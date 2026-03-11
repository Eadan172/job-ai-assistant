import httpx
import json
import os
import re
from typing import Optional, Dict, Any

class LLMAdapter:
    """
    统一的大语言模型适配器
    支持 DeepSeek、通义千问、智谱 GLM 云端 API
    """
    
    def __init__(self, model_type: str = "deepseek", api_key: str = ""):
        self.model_type = model_type
        self.api_key = api_key
        self.timeout = 60.0
        
        # API 配置
        self.api_configs = {
            "deepseek": {
                "url": "https://api.deepseek.com/v1/chat/completions",
                "model": "deepseek-chat",
                "headers": lambda key: {
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                }
            },
            "qwen": {
                "url": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                "model": "qwen-turbo",
                "headers": lambda key: {
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                }
            },
            "glm": {
                "url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                "model": "glm-4",
                "headers": lambda key: {
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                }
            }
        }
        
        print(f"[LLM Adapter] 初始化 - 模型: {model_type}, API Key: {'已设置' if api_key else '未设置'}")
    
    async def chat(self, message: str, context: Dict[str, Any] = None) -> str:
        """
        发送聊天消息
        """
        print(f"[LLM Adapter] chat 调用 - 模型: {self.model_type}")
        return await self._api_chat(message, context)
    
    async def _api_chat(self, message: str, context: Dict[str, Any] = None) -> str:
        """
        使用云端 API 进行聊天
        """
        if not self.api_key:
            raise Exception(f"模型 {self.model_type} 需要提供 API Key")
        
        config = self.api_configs.get(self.model_type)
        if not config:
            raise Exception(f"不支持的模型类型: {self.model_type}")
        
        print(f"[LLM Adapter] 使用 {self.model_type} 云端 API")
        
        # 构建消息
        system_prompt = self._build_system_prompt(context)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
        
        # 构建请求体
        if self.model_type == "qwen":
            payload = {
                "model": config["model"],
                "input": {
                    "messages": messages
                }
            }
        else:
            payload = {
                "model": config["model"],
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000
            }
        
        print(f"[LLM Adapter] API 请求 payload (不含密钥): {json.dumps({k: v for k, v in payload.items() if k != 'api_key'}, ensure_ascii=False)[:200]}...")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    config["url"],
                    headers=config["headers"](self.api_key),
                    json=payload
                )
                
                print(f"[LLM Adapter] API 响应状态: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    if self.model_type == "qwen":
                        result = data.get("output", {}).get("text", "")
                    else:
                        result = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    print(f"[LLM Adapter] API 返回内容长度: {len(result)}")
                    print(f"[LLM Adapter] API 返回前100字符: {result[:100]}...")
                    return result
                elif response.status_code == 401:
                    raise Exception("API Key 无效或已过期")
                elif response.status_code == 403:
                    raise Exception("API 访问被拒绝，请检查 API Key 权限")
                else:
                    error_text = response.text
                    print(f"[LLM Adapter] API 请求失败: {response.status_code} - {error_text}")
                    raise Exception(f"API 请求失败: {response.status_code}")
                    
        except httpx.ConnectError as e:
            print(f"[LLM Adapter] API 连接失败: {str(e)}")
            raise Exception(f"无法连接到 {self.model_type} API 服务")
        except Exception as e:
            print(f"[LLM Adapter] API 调用异常: {str(e)}")
            raise
    
    def _build_system_prompt(self, context: Dict[str, Any] = None) -> str:
        """
        构建系统提示词
        """
        base_prompt = """你是一个专业的招聘AI助手，帮助求职者进行求职相关的工作。

你的职责包括：
1. 分析岗位要求，帮助求职者理解职位需求
2. 优化简历内容，提供专业的修改建议
3. 模拟面试问答，帮助求职者准备面试
4. 提供薪资建议，基于市场行情给出参考
5. 生成求职建议，帮助求职者提高成功率
6. 分析网页中的岗位信息，生成结构化的岗位分析报告

请用专业、友好、鼓励的语气回复，回复要简洁明了，重点突出。"""
        
        if context:
            if context.get("jobs"):
                jobs_info = "\n".join([
                    f"- {job.get('title')} at {job.get('company')} ({job.get('salary')})"
                    for job in context["jobs"][:5]
                ])
                base_prompt += f"\n\n当前已爬取的岗位信息：\n{jobs_info}"
            
            if context.get("resume"):
                base_prompt += f"\n\n用户简历摘要：\n{context['resume'][:500]}..."
            
            if context.get("analysis"):
                base_prompt += f"\n\n简历分析结果：匹配度 {context['analysis'].get('matchScore', 0)}%"
        
        return base_prompt
    
    async def analyze_resume(self, resume_text: str) -> Dict[str, Any]:
        """
        分析简历 - 完全由 LLM 生成分析结果
        重点：岗位投递方向、优劣势分析
        """
        print(f"[LLM Adapter] 分析简历，模型: {self.model_type}")
        
        prompt = f"""你是一位资深职业规划师和简历专家。请深入分析以下简历，给出专业的职业规划建议。

简历内容：
{resume_text}

请严格按照以下 JSON 格式返回分析结果：
{{
    "name": "姓名",
    "experience": "工作年限",
    "education": "最高学历",
    "skills": ["核心技能1", "核心技能2", "核心技能3"],
    
    "job_directions": [
        {{
            "direction": "投递方向名称",
            "match_level": "高/中/低",
            "reason": "匹配原因"
        }}
    ],
    
    "strengths": [
        {{
            "point": "优势点",
            "evidence": "简历中的证据",
            "how_to_use": "如何在求职中发挥"
        }}
    ],
    
    "weaknesses": [
        {{
            "point": "不足之处",
            "impact": "对求职的影响",
            "improvement": "改进建议"
        }}
    ],
    
    "career_suggestions": [
        "职业发展建议1",
        "职业发展建议2",
        "职业发展建议3"
    ],
    
    "resume_improvements": [
        "简历优化建议1",
        "简历优化建议2"
    ],
    
    "detailed_analysis": "详细分析报告（包含：1.个人背景总结 2.核心竞争力分析 3.适合的岗位方向及原因 4.优劣势详细分析 5.求职策略建议）"
}}"""
        
        response = await self.chat(prompt)
        print(f"[LLM Adapter] 简历分析原始响应: {response[:500]}...")
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
                result["raw_analysis"] = response
                return result
        except json.JSONDecodeError as e:
            print(f"[LLM Adapter] JSON 解析失败: {e}")
        
        return {
            "name": "请查看详细分析",
            "experience": "请查看详细分析",
            "education": "请查看详细分析",
            "skills": [],
            "job_directions": [],
            "strengths": [],
            "weaknesses": [],
            "career_suggestions": [],
            "resume_improvements": [],
            "raw_analysis": response
        }
    
    async def optimize_resume(self, resume_text: str) -> Dict[str, Any]:
        """
        优化简历 - 完全由 LLM 生成优化建议
        """
        print(f"[LLM Adapter] 优化简历，模型: {self.model_type}")
        
        prompt = f"""请为以下简历提供详细的优化建议：

简历内容：
{resume_text}

请从以下方面提供具体的优化建议：
1. 结构优化：如何更好地组织简历结构
2. 内容优化：如何突出重点、量化成果
3. 语言优化：如何使用更专业的表达
4. 格式优化：如何让简历更易读

请给出具体的修改建议和示例。"""
        
        response = await self.chat(prompt)
        print(f"[LLM Adapter] 简历优化原始响应: {response[:500]}...")
        
        return {
            "raw_suggestions": response
        }
    
    async def analyze_jobs(self, jobs: list) -> str:
        """
        分析岗位列表，生成汇总报告
        """
        print(f"[LLM Adapter] 分析岗位列表，数量: {len(jobs)}")
        
        jobs_text = "\n\n".join([
            f"岗位 {i+1}:\n标题: {job.get('title', '未知')}\n公司: {job.get('company', '未知')}\n薪资: {job.get('salary', '面议')}\n地点: {job.get('location', '未知')}\n经验: {job.get('experience', '不限')}\n学历: {job.get('education', '不限')}\n描述: {job.get('description', '无')[:200]}"
            for i, job in enumerate(jobs)
        ])
        
        prompt = f"""请分析以下岗位列表，生成一份完整的岗位分析报告：

{jobs_text}

请按以下格式生成报告：

## 岗位概览
- 岗位总数：X 个
- 主要岗位类型：XXX
- 平均薪资范围：XXX

## 岗位类型分析
（分析岗位类型分布）

## 技能要求趋势
（分析技能要求趋势）

## 薪资分析
（分析薪资分布）

## 经验与学历要求
（分析经验和学历要求）

## 求职建议
（给出求职建议）"""
        
        return await self.chat(prompt)


def get_llm_adapter(model_type: str = "deepseek", api_key: str = "") -> LLMAdapter:
    """
    获取 LLM 适配器实例（每次创建新实例）
    """
    print(f"[LLM Adapter] 创建新实例 - 模型: {model_type}, API Key: {'已设置' if api_key else '未设置'}")
    return LLMAdapter(model_type, api_key)
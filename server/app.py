from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import tempfile
from typing import Optional, List
from models.llm_adapter import get_llm_adapter
from utils.resume_parser import parse_resume, extract_resume_info

app = FastAPI(title="招聘AI助手本地服务 V1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic 模型用于接收JSON请求
class AnalyzeRequest(BaseModel):
    resume_text: str = ""
    model_type: str = "deepseek"
    api_key: str = ""

class OptimizeRequest(BaseModel):
    resume_text: str = ""
    model_type: str = "deepseek"
    api_key: str = ""

class ChatRequest(BaseModel):
    message: str
    context: dict = {}
    model_type: str = "deepseek"
    api_key: str = ""

class TestConnectionRequest(BaseModel):
    model_type: str = "deepseek"
    api_key: str = ""

@app.get("/")
async def root():
    return {
        "message": "欢迎使用招聘AI助手本地服务",
        "version": "1.0",
        "docs": "/docs",
        "status": "/status",
        "health": "/health"
    }

@app.get("/status")
async def get_status():
    return {"status": "running", "message": "招聘AI助手本地服务运行正常", "version": "1.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/parse-resume")
async def parse_resume_file(file: UploadFile = File(...)):
    """
    解析上传的简历文件，返回文本内容
    """
    print(f"\n{'='*60}")
    print(f"[API] parse-resume 请求")
    print(f"[API] 文件名: {file.filename}")
    print(f"[API] 文件类型: {file.content_type}")
    print(f"{'='*60}")
    
    try:
        # 保存临时文件
        ext = os.path.splitext(file.filename)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        
        try:
            # 解析文件
            content = parse_resume(tmp_path)
            print(f"[API] 解析成功，内容长度: {len(content)}")
            print(f"[API] 内容预览: {content[:200]}...")
            
            return {
                "success": True,
                "content": content,
                "filename": file.filename
            }
        finally:
            os.unlink(tmp_path)
            
    except Exception as e:
        print(f"[API] 解析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"解析文件失败: {str(e)}")

@app.post("/analyze-resume")
async def analyze_resume(request: AnalyzeRequest):
    """
    分析简历 - 接收JSON请求
    """
    print(f"\n{'='*60}")
    print(f"[API] analyze-resume 请求")
    print(f"[API] 模型类型: {request.model_type}")
    print(f"[API] API Key 长度: {len(request.api_key) if request.api_key else 0}")
    print(f"[API] 简历内容长度: {len(request.resume_text) if request.resume_text else 0}")
    print(f"{'='*60}")
    
    try:
        if not request.api_key:
            raise HTTPException(status_code=400, detail=f"模型 {request.model_type} 需要提供 API Key")
        
        content = request.resume_text or "这是一份简历内容"
        
        llm = get_llm_adapter(request.model_type, request.api_key)
        analysis = await llm.analyze_resume(content)
        
        result = {
            "raw_analysis": analysis.get("raw_analysis", ""),
            "name": analysis.get("name", "未识别"),
            "experience": analysis.get("experience", "未识别"),
            "education": analysis.get("education", "未识别"),
            "skills": analysis.get("skills", []),
            "job_directions": analysis.get("job_directions", []),
            "strengths": analysis.get("strengths", []),
            "weaknesses": analysis.get("weaknesses", []),
            "career_suggestions": analysis.get("career_suggestions", []),
            "resume_improvements": analysis.get("resume_improvements", []),
            "model_used": request.model_type
        }
        
        print(f"[API] 分析完成，返回结果长度: {len(result['raw_analysis'])}")
        
        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析简历失败: {str(e)}")

@app.post("/optimize-resume")
async def optimize_resume(request: OptimizeRequest):
    """
    优化简历 - 接收JSON请求
    """
    print(f"\n{'='*60}")
    print(f"[API] optimize-resume 请求")
    print(f"[API] 模型类型: {request.model_type}")
    print(f"[API] API Key 长度: {len(request.api_key) if request.api_key else 0}")
    print(f"[API] 简历内容长度: {len(request.resume_text) if request.resume_text else 0}")
    print(f"{'='*60}")
    
    try:
        if not request.api_key:
            raise HTTPException(status_code=400, detail=f"模型 {request.model_type} 需要提供 API Key")
        
        content = request.resume_text or "这是一份简历内容"
        
        llm = get_llm_adapter(request.model_type, request.api_key)
        optimization = await llm.optimize_resume(content)
        
        result = {
            "raw_suggestions": optimization.get("raw_suggestions", ""),
            "suggestions": optimization.get("suggestions", []),
            "model_used": request.model_type
        }
        
        print(f"[API] 优化完成，返回结果长度: {len(result['raw_suggestions'])}")
        
        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 优化失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"优化简历失败: {str(e)}")

@app.post("/analyze-jobs")
async def analyze_jobs(data: dict):
    """
    分析岗位列表，生成汇总报告
    """
    print(f"\n{'='*60}")
    print(f"[API] analyze-jobs 请求")
    print(f"{'='*60}")
    
    try:
        jobs = data.get("jobs", [])
        model_type = data.get("model_type", "deepseek")
        api_key = data.get("api_key", "")
        
        print(f"[API] 模型类型: {model_type}")
        print(f"[API] 岗位数量: {len(jobs)}")
        
        if not jobs:
            return {
                "success": False,
                "message": "没有岗位数据可供分析"
            }
        
        llm = get_llm_adapter(model_type, api_key)
        analysis = await llm.analyze_jobs(jobs)
        
        print(f"[API] 岗位分析完成，报告长度: {len(analysis)}")
        
        return {
            "success": True,
            "data": {
                "analysis": analysis,
                "jobs_count": len(jobs),
                "model_used": model_type
            }
        }
    except Exception as e:
        print(f"[API] 分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析岗位失败: {str(e)}")

@app.post("/analyze-job")
async def analyze_job(job_data: dict):
    """
    分析单个岗位
    """
    print(f"\n{'='*60}")
    print(f"[API] analyze-job 请求")
    print(f"{'='*60}")
    
    try:
        job_title = job_data.get("title", "")
        company = job_data.get("company", "")
        description = job_data.get("description", "")
        model_type = job_data.get("model_type", "deepseek")
        api_key = job_data.get("api_key", "")
        
        print(f"[API] 模型类型: {model_type}")
        print(f"[API] 岗位: {job_title} @ {company}")
        
        llm = get_llm_adapter(model_type, api_key)
        
        prompt = f"""请分析以下岗位：

职位：{job_title}
公司：{company}
描述：{description}

请提供：
1. 岗位要求分析
2. 技能要求
3. 薪资建议
4. 面试准备建议"""
        
        analysis = await llm.chat(prompt)
        
        result = {
            "jobTitle": job_title,
            "company": company,
            "analysis": analysis,
            "model_used": model_type
        }
        
        print(f"[API] 岗位分析完成")
        
        return {"success": True, "data": result}
    except Exception as e:
        print(f"[API] 分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析岗位失败: {str(e)}")

@app.post("/chat")
async def chat(data: dict):
    """
    AI 对话
    """
    print(f"\n{'='*60}")
    print(f"[API] chat 请求")
    print(f"[API] 模型类型: {data.get('model_type', 'deepseek')}")
    print(f"[API] API Key 长度: {len(data.get('api_key', '')) if data.get('api_key') else 0}")
    print(f"[API] 消息: {data.get('message', '')[:100]}...")
    print(f"{'='*60}")
    
    try:
        message = data.get("message", "")
        context = data.get("context", {})
        model_type = data.get("model_type", "deepseek")
        api_key = data.get("api_key", "")
        
        llm = get_llm_adapter(model_type, api_key)
        response = await llm.chat(message, context)
        
        print(f"[API] 聊天响应长度: {len(response)}")
        print(f"[API] 响应前100字符: {response[:100]}...")
        
        return {
            "success": True, 
            "data": {
                "response": response,
                "model_used": model_type
            }
        }
    except Exception as e:
        print(f"[API] 对话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"对话失败: {str(e)}")

@app.post("/generate-reply")
async def generate_reply(message_data: dict):
    """
    生成自动回复
    """
    print(f"\n{'='*60}")
    print(f"[API] generate-reply 请求")
    print(f"{'='*60}")
    
    try:
        message = message_data.get("message", "")
        context = message_data.get("context", "")
        model_type = message_data.get("model_type", "deepseek")
        api_key = message_data.get("api_key", "")
        
        print(f"[API] 模型类型: {model_type}")
        
        llm = get_llm_adapter(model_type, api_key)
        
        prompt = f"""请根据以下招聘方消息，生成一个专业、礼貌的回复：

招聘方消息：{message}
上下文：{context}

要求：
1. 语气专业、友好
2. 表达求职意愿
3. 询问面试安排
4. 不超过100字"""
        
        reply = await llm.chat(prompt)
        
        print(f"[API] 回复生成完成")
        
        return {
            "success": True, 
            "data": {
                "reply": reply,
                "model_used": model_type
            }
        }
    except Exception as e:
        print(f"[API] 生成回复失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成回复失败: {str(e)}")

@app.post("/test-connection")
async def test_connection(data: dict):
    """
    测试模型连接
    """
    print(f"\n{'='*60}")
    print(f"[API] test-connection 请求")
    print(f"{'='*60}")
    
    model_type = data.get("model_type", "deepseek")
    api_key = data.get("api_key", "")
    
    print(f"[API] 模型类型: {model_type}")
    print(f"[API] API Key 长度: {len(api_key) if api_key else 0}")
    
    # 严格校验 API Key
    if not api_key or len(api_key.strip()) == 0:
        error_msg = f"模型 {model_type} 需要提供 API Key"
        print(f"[API] 校验失败: {error_msg}")
        return {
            "success": False, 
            "message": error_msg,
            "error_type": "missing_api_key"
        }
    
    try:
        llm = get_llm_adapter(model_type, api_key)
        
        test_message = "你好，请简短回复'连接成功'"
        print(f"[API] 发送测试消息...")
        
        response = await llm.chat(test_message)
        
        print(f"[API] 模型响应: {response[:100] if response else '空'}...")
        
        if response and len(response) > 0:
            print(f"[API] 连接测试成功")
            return {
                "success": True, 
                "message": f"连接成功 - 模型: {model_type}",
                "response": response[:100],
                "model_used": model_type
            }
        else:
            print(f"[API] 响应为空")
            return {
                "success": False, 
                "message": "模型响应为空",
                "error_type": "empty_response"
            }
            
    except Exception as e:
        error_msg = str(e)
        print(f"[API] 连接测试异常: {error_msg}")
        return {
            "success": False, 
            "message": f"连接测试失败: {error_msg}",
            "error_type": "exception"
        }

@app.post("/match-resume-job")
async def match_resume_job(data: dict):
    """
    匹配简历与岗位
    """
    print(f"\n{'='*60}")
    print(f"[API] match-resume-job 请求")
    print(f"{'='*60}")
    
    try:
        resume_text = data.get("resume_text", "")
        job_data = data.get("job_data", {})
        model_type = data.get("model_type", "deepseek")
        api_key = data.get("api_key", "")
        
        print(f"[API] 模型类型: {model_type}")
        
        llm = get_llm_adapter(model_type, api_key)
        
        prompt = f"""请分析简历与岗位的匹配度：

简历摘要：
{resume_text[:500]}

岗位信息：
职位：{job_data.get('title')}
公司：{job_data.get('company')}
要求：{job_data.get('description')}

请提供：
1. 匹配度评分（0-100）
2. 匹配的优势
3. 不匹配的地方
4. 改进建议"""
        
        analysis = await llm.chat(prompt)
        
        print(f"[API] 匹配分析完成")
        
        return {
            "success": True,
            "data": {
                "analysis": analysis,
                "model_used": model_type
            }
        }
    except Exception as e:
        print(f"[API] 匹配分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"匹配分析失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
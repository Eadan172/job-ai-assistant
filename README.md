# 🤖 招聘AI助手 (Job AI Assistant)

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Edge%20%7C%20Chrome-brightgreen.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-yellow.svg)

**一款智能招聘助手浏览器插件，帮助求职者高效找工作**

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [使用教程](#-使用教程) • [常见问题](#-常见问题)

</div>

---

## 📖 项目简介

招聘AI助手是一款专为求职者设计的浏览器插件，集成了岗位爬取、AI分析、简历优化等功能。通过接入主流大语言模型（DeepSeek、通义千问、智谱GLM），为求职者提供智能化的求职辅助服务。

### ✨ 核心亮点

- 🚀 **一键爬取**：支持Boss直聘、拉勾网、前程无忧、智联招聘等主流招聘网站
- 🤖 **AI分析**：智能分析岗位要求，生成匹配度报告
- 📄 **简历优化**：AI分析简历内容，提供专业优化建议
- 💬 **智能对话**：模拟面试、薪资建议、求职咨询
- 📥 **一键导出**：生成Markdown格式的分析报告

---

## 🎯 功能特性

### 1. 岗位爬取
- 自动识别当前招聘网站
- 支持快速爬取和深度爬取两种模式
- 智能解析岗位信息（职位、公司、薪资、地点等）
- 支持iframe内容抓取和SPA页面解析

### 2. AI岗位分析
- 批量分析爬取的岗位数据
- 生成岗位趋势报告
- 技能要求分析
- 薪资范围统计

### 3. 简历分析
- 支持PDF、DOCX、TXT格式简历上传
- AI智能解析简历内容
- 生成岗位匹配建议
- 提供简历优化方向

### 4. AI对话助手
- 匹配度分析
- 模拟面试问答
- 薪资谈判建议
- 求职策略咨询

---

## 🖥️ 系统要求

### 必需环境
- **操作系统**：Windows 10/11、macOS 10.15+、Linux
- **浏览器**：Microsoft Edge (Chromium内核) 或 Google Chrome
- **Python**：3.8 或更高版本
- **网络**：需要访问大模型API服务

### 支持的AI模型
| 模型 | API提供商 | 特点 |
|------|----------|------|
| DeepSeek | DeepSeek | 性价比高，响应快 |
| 通义千问 | 阿里云 | 中文理解强 |
| 智谱GLM | 智谱AI | 国产大模型 |

---

## 🚀 快速开始

### 第一步：克隆项目

```bash
git clone https://github.com/your-username/job-ai-assistant.git
cd job-ai-assistant
```

### 第二步：安装Python依赖

```bash
cd server
pip install -r requirements.txt
```

### 第三步：启动本地服务

```bash
python app.py
```

看到以下输出表示服务启动成功：
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### 第四步：安装浏览器插件

#### Edge浏览器安装步骤：

1. 打开Edge浏览器，在地址栏输入 `edge://extensions/`
2. 开启左下角的 **"开发人员模式"**
3. 点击 **"加载解压缩的扩展"** 按钮
4. 选择项目中的 `extension` 文件夹
5. 插件安装成功后，浏览器工具栏会出现插件图标

#### Chrome浏览器安装步骤：

1. 打开Chrome浏览器，在地址栏输入 `chrome://extensions/`
2. 开启右上角的 **"开发者模式"**
3. 点击 **"加载已解压的扩展程序"** 按钮
4. 选择项目中的 `extension` 文件夹
5. 插件安装成功后，浏览器工具栏会出现插件图标

### 第五步：配置API Key

1. 点击浏览器工具栏的插件图标打开插件
2. 切换到 **"设置"** 标签页
3. 选择AI模型类型（推荐DeepSeek）
4. 输入对应的API Key
5. 点击 **"测试连接"** 确认配置正确
6. 点击 **"保存设置"**

#### 如何获取API Key：

| 模型 | 获取地址 |
|------|----------|
| DeepSeek | https://platform.deepseek.com/ |
| 通义千问 | https://dashscope.console.aliyun.com/ |
| 智谱GLM | https://open.bigmodel.cn/ |

---

## 📚 使用教程

### 一、爬取岗位信息

1. **访问招聘网站**
   - 打开Boss直聘、拉勾网、前程无忧或智联招聘
   - 登录您的账号（部分网站需要登录才能查看完整信息）

2. **搜索或浏览岗位**
   - 输入关键词搜索目标岗位
   - 或浏览首页推荐的岗位列表

3. **点击爬取按钮**
   - 点击插件图标打开面板
   - 点击 **"🔍 爬取当前页面岗位"** 按钮
   - 等待爬取完成，页面会显示爬取到的岗位数量

4. **查看爬取结果**
   - 岗位列表会显示在插件面板中
   - 可以看到职位名称、公司、薪资等信息

### 二、AI分析岗位

1. **确保已爬取岗位**
   - 插件中至少有一条岗位数据

2. **执行AI分析**
   - 点击 **"🤖 AI 分析岗位"** 按钮
   - 等待AI生成分析报告
   - 报告会显示在岗位列表上方

3. **导出报告**
   - 点击 **"📥 导出 Markdown"** 按钮
   - 报告会以Markdown格式下载到本地

### 三、上传与分析简历

1. **上传简历**
   - 切换到 **"简历"** 标签页
   - 点击上传区域或拖拽简历文件
   - 支持 PDF、DOCX、TXT 格式

2. **AI分析简历**
   - 点击 **"🤖 AI 分析简历"** 按钮
   - AI会分析您的简历并生成报告
   - 报告包含：推荐投递方向、核心优势、待提升方面等

3. **优化简历**
   - 点击 **"✨ AI 优化简历"** 按钮
   - AI会提供具体的优化建议

4. **下载分析报告**
   - 点击 **"📥 下载分析报告"** 按钮
   - 报告会以Markdown格式保存

### 四、AI对话助手

1. **切换到对话标签**
   - 点击 **"💬 对话"** 标签页

2. **开始对话**
   - 在输入框输入您的问题
   - 点击发送或按回车键
   - AI会给出专业的回答

3. **使用快捷功能**
   - **匹配度分析**：分析简历与岗位的匹配程度
   - **模拟面试**：模拟真实面试场景
   - **薪资建议**：获取薪资谈判建议

---

## ⚙️ 配置说明

### 服务器配置

服务器默认运行在 `http://localhost:8000`，如需修改：

编辑 `server/app.py` 文件最后一行：
```python
uvicorn.run(app, host="0.0.0.0", port=8000)  # 修改端口号
```

### 插件配置

编辑 `extension/popup/popup.js` 文件开头的配置：
```javascript
const CONFIG = {
    serverUrl: 'http://localhost:8000',  // 服务器地址
    maxJobs: 100  // 最大爬取岗位数
};
```

### 支持的招聘网站

| 网站 | 网址 | 支持程度 |
|------|------|----------|
| Boss直聘 | zhipin.com | ✅ 完全支持 |
| 拉勾网 | lagou.com | ✅ 完全支持 |
| 前程无忧 | 51job.com | ✅ 完全支持 |
| 智联招聘 | zhaopin.com | ✅ 完全支持 |

---

## 📁 项目结构

```
job-ai-assistant/
├── extension/                 # 浏览器插件
│   ├── background/           # 后台脚本
│   │   └── background.js
│   ├── content-script/       # 内容脚本
│   │   └── content.js
│   ├── icons/               # 插件图标
│   │   ├── icon.svg
│   │   ├── icon16.png
│   │   ├── icon32.png
│   │   ├── icon48.png
│   │   └── icon128.png
│   ├── popup/               # 弹窗界面
│   │   ├── index.html
│   │   └── popup.js
│   └── manifest.json        # 插件配置
│
├── server/                   # 本地服务器
│   ├── models/              # AI模型适配器
│   │   └── llm_adapter.py
│   ├── utils/               # 工具函数
│   │   └── resume_parser.py
│   ├── app.py               # 主程序
│   └── requirements.txt     # Python依赖
│
├── docs/                     # 文档
│   └── images/              # 图片资源
│
├── README.md                 # 项目说明
├── LICENSE                   # 开源协议
└── .gitignore               # Git忽略配置
```

---

## ❓ 常见问题

### Q1: 插件显示"服务未启动"怎么办？

**A:** 请确保本地服务器正在运行：
```bash
cd server
python app.py
```
如果端口8000被占用，可以修改端口号。

### Q2: 爬取岗位时提示"爬取失败"？

**A:** 可能的原因：
1. 当前页面不是招聘网站
2. 页面尚未加载完成
3. 网站结构发生变化

解决方法：
- 确保在支持的招聘网站页面
- 等待页面完全加载后再点击爬取
- 尝试刷新页面后重新爬取

### Q3: AI分析提示"需要提供API Key"？

**A:** 请在设置中配置正确的API Key：
1. 打开插件设置页面
2. 选择模型类型
3. 输入有效的API Key
4. 点击"测试连接"验证
5. 保存设置

### Q4: 简历上传后解析失败？

**A:** 可能的原因：
1. 文件格式不支持（仅支持PDF、DOCX、TXT）
2. 文件损坏或加密
3. 服务器未启动

解决方法：
- 确保文件格式正确
- 尝试重新保存文件
- 检查服务器是否运行

### Q5: 如何获取免费的API Key？

**A:** 各平台都提供免费额度：
- **DeepSeek**：新用户赠送免费额度
- **通义千问**：新用户赠送免费额度
- **智谱GLM**：新用户赠送免费额度

### Q6: 支持哪些浏览器？

**A:** 目前支持：
- Microsoft Edge（Chromium内核版本）
- Google Chrome
- 其他Chromium内核浏览器（如Brave、Vivaldi等）

### Q7: 数据安全吗？

**A:** 
- 所有数据存储在本地
- 简历内容仅发送给配置的AI服务
- 不会上传到任何第三方服务器
- API Key保存在浏览器本地存储中

---

## 🔧 技术架构

### 前端（浏览器插件）
- **Manifest V3**：使用最新的扩展程序标准
- **Content Script**：页面内容抓取
- **Background Service Worker**：后台任务处理
- **Popup**：用户交互界面

### 后端（本地服务）
- **FastAPI**：高性能异步Web框架
- **LLM Adapter**：统一的大模型接口适配
- **Resume Parser**：简历文件解析

### AI模型
- **DeepSeek API**：高性价比大模型
- **通义千问 API**：阿里云大模型服务
- **智谱GLM API**：国产大模型

---

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 📄 开源协议

本项目采用 MIT 协议开源，详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的Web框架
- [DeepSeek](https://www.deepseek.com/) - 高性价比AI服务
- [通义千问](https://tongyi.aliyun.com/) - 阿里云大模型
- [智谱AI](https://www.zhipuai.cn/) - GLM大模型

---

<div align="center">

**如果这个项目对您有帮助，请给一个 ⭐ Star 支持一下！**

Made with ❤️ by Job Seekers, for Job Seekers

</div>

# 快速安装指南

## 📦 安装步骤（5分钟完成）

### 步骤一：下载项目

**方式1：使用Git克隆（推荐）**
```bash
git clone https://github.com/your-username/job-ai-assistant.git
cd job-ai-assistant
```

**方式2：下载ZIP压缩包**
1. 点击项目页面右上角的 "Code" 按钮
2. 选择 "Download ZIP"
3. 解压到任意目录

---

### 步骤二：安装Python依赖

**Windows用户：**
```bash
cd server
pip install -r requirements.txt
```

**Mac/Linux用户：**
```bash
cd server
pip3 install -r requirements.txt
```

> 如果pip安装速度慢，可以使用国内镜像：
> ```bash
> pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
> ```

---

### 步骤三：启动本地服务

**Windows用户：**
- 双击运行 `start-server.bat`

**Mac/Linux用户：**
```bash
chmod +x start-server.sh
./start-server.sh
```

**或手动启动：**
```bash
cd server
python app.py
```

看到以下输出表示成功：
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

### 步骤四：安装浏览器插件

#### Edge浏览器
1. 打开 `edge://extensions/`
2. 开启左下角 **"开发人员模式"**
3. 点击 **"加载解压缩的扩展"**
4. 选择项目中的 `extension` 文件夹

#### Chrome浏览器
1. 打开 `chrome://extensions/`
2. 开启右上角 **"开发者模式"**
3. 点击 **"加载已解压的扩展程序"**
4. 选择项目中的 `extension` 文件夹

---

### 步骤五：配置API Key

1. 点击浏览器工具栏的插件图标
2. 切换到 **"设置"** 标签
3. 选择AI模型（推荐DeepSeek）
4. 输入API Key
5. 点击 **"测试连接"** 验证
6. 点击 **"保存设置"**

#### 获取API Key

| 模型 | 注册地址 | 免费额度 |
|------|----------|----------|
| DeepSeek | https://platform.deepseek.com/ | 新用户赠送 |
| 通义千问 | https://dashscope.console.aliyun.com/ | 新用户赠送 |
| 智谱GLM | https://open.bigmodel.cn/ | 新用户赠送 |

---

## ✅ 验证安装

1. 打开任意招聘网站（如Boss直聘）
2. 点击插件图标
3. 界面显示"服务运行中"表示安装成功
4. 点击"爬取当前页面岗位"测试功能

---

## ❓ 遇到问题？

### 服务启动失败
- 检查Python版本：`python --version`（需要3.8+）
- 检查端口占用：确保8000端口未被占用
- 重新安装依赖：`pip install -r requirements.txt --force-reinstall`

### 插件加载失败
- 确保选择的是 `extension` 文件夹
- 检查文件夹中是否包含 `manifest.json`
- 尝试刷新浏览器扩展页面

### API连接失败
- 检查网络连接
- 确认API Key正确无误
- 检查API Key是否有余额

---

## 📞 获取帮助

- 查看完整文档：[README.md](README.md)
- 提交问题：[GitHub Issues](https://github.com/your-username/job-ai-assistant/issues)

---

**祝您求职顺利！🎉**

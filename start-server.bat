@echo off
chcp 65001 >nul
echo ========================================
echo    招聘AI助手 - 启动本地服务
echo ========================================
echo.

cd /d "%~dp0server"

echo [1/2] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [2/2] 启动服务...
echo.
echo 服务地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo.
echo 请保持此窗口打开，关闭将停止服务
echo ========================================
echo.

python app.py

pause

#!/bin/bash

echo "========================================"
echo "   招聘AI助手 - 启动本地服务"
echo "========================================"
echo ""

cd "$(dirname "$0")/server"

echo "[1/2] 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到Python，请先安装Python 3.8+"
    exit 1
fi

echo "[2/2] 启动服务..."
echo ""
echo "服务地址: http://localhost:8000"
echo "API文档: http://localhost:8000/docs"
echo ""
echo "请保持此终端打开，关闭将停止服务"
echo "========================================"
echo ""

python3 app.py

#!/bin/bash

# AI报告批阅系统启动脚本 (基于uv)

echo "========================================="
echo "   AI报告批阅系统 - 启动脚本 (uv)"
echo "========================================="

# 检查uv是否安装
if ! command -v uv &> /dev/null; then
    echo "错误: 未找到uv，请先安装uv"
    echo "安装命令: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✓ uv已安装: $(uv --version)"

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python3"
    exit 1
fi

echo "✓ Python3已安装: $(python3 --version)"

# 检查项目配置文件
if [ ! -f "pyproject.toml" ]; then
    echo "错误: 未找到pyproject.toml配置文件"
    exit 1
fi

echo "✓ 找到项目配置文件: pyproject.toml"

# 检查是否需要安装依赖
if [ ! -f ".venv/.installed" ]; then
    echo "正在安装依赖..."
    uv sync
    if [ $? -ne 0 ]; then
        echo "错误: 安装依赖失败"
        exit 1
    fi
    touch .venv/.installed
    echo "✓ 依赖安装成功"
else
    echo "✓ 依赖已安装"
fi

# 检查必要的目录是否存在
mkdir -p reports
mkdir -p output
mkdir -p graded_reports
echo "✓ 目录结构检查完成"

# 检查是否有配置文件
if [ ! -f "config.py" ]; then
    echo "警告: 未找到config.py配置文件"
    echo "请确保已正确配置API密钥和其他设置"
fi

# 检查端口8000是否被占用
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "警告: 端口8000已被占用"
    echo "正在尝试终止占用端口的进程..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    sleep 2
fi

# 启动API服务器（后台运行）
echo ""
echo "========================================="
echo "   正在启动API服务器（后台运行）..."
echo "========================================="
echo "访问地址: http://localhost:8000"
echo "日志文件: logs/server.log"
echo "停止服务: ./stop.sh"
echo "========================================="
echo ""

# 创建日志目录
mkdir -p logs

# 使用uv run启动FastAPI应用（后台运行）
nohup uv run uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload > logs/server.log 2>&1 &
SERVER_PID=$!

# 保存PID到文件
echo $SERVER_PID > logs/server.pid

echo "✓ 服务器已在后台启动"
echo "✓ 进程ID: $SERVER_PID"
echo "✓ 查看日志: tail -f logs/server.log"
echo ""

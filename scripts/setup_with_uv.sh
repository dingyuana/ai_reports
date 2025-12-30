#!/bin/bash

# 使用 uv 设置 AI 报告批阅系统
# 此脚本将使用 uv 创建虚拟环境并安装所有依赖

set -e  # 遇到错误时退出

echo "AI 实验报告自动批阅系统 - uv 设置脚本"
echo "====================================="

# 检查 uv 是否已安装
if ! command -v uv &> /dev/null; then
    echo "错误: uv 未安装。请先安装 uv："
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✓ uv 已安装"

# 检查 Python 版本
PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
echo "检测到 Python 版本: $PYTHON_VERSION"

# 检查是否为 3.10 或更高版本
if [[ $(printf '%s\n' "3.10" "$PYTHON_VERSION" | sort -V | head -n1) == "3.10" ]]; then
    echo "✓ Python 版本满足要求"
else
    echo "错误: Python 版本过低，需要 3.10 或更高版本"
    exit 1
fi

# 检查是否存在 pyproject.toml
if [ ! -f "pyproject.toml" ]; then
    echo "警告: pyproject.toml 不存在，将使用 requirements.txt"
    
    # 检查是否存在 requirements.txt
    if [ ! -f "requirements.txt" ]; then
        echo "错误: 未找到 requirements.txt 文件"
        exit 1
    fi
    
    echo "正在创建虚拟环境..."
    uv venv
    
    echo "正在激活虚拟环境..."
    source .venv/bin/activate
    
    echo "正在安装依赖..."
    uv pip install -r requirements.txt
    
else
    echo "检测到 pyproject.toml，使用 uv sync 安装依赖..."
    
    # 检查 uv.lock 是否存在，如果不存在则生成
    if [ ! -f "uv.lock" ]; then
        echo "生成 uv.lock 文件..."
    fi
    
    # 创建虚拟环境并同步依赖
    uv venv
    source .venv/bin/activate
    uv sync --dev
fi

echo "✓ 依赖安装完成"

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "正在创建 .env 文件..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✓ 已从 .env.example 创建 .env 文件"
        echo "请编辑 .env 文件并配置 AI_API_KEY 和 ARK_API_KEY"
    else
        echo "警告: 未找到 .env.example 文件"
    fi
else
    echo "✓ .env 文件已存在"
fi

echo ""
echo "设置完成！"
echo ""
echo "要启动服务器，请执行以下命令："
echo "  source .venv/bin/activate"
echo "  uv run uvicorn main:report --host 0.0.0.0 --port 8000"
echo ""
echo "或者使用以下命令启动（在虚拟环境中）："
echo "  uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload"
echo ""

# 显示虚拟环境路径
echo "虚拟环境位置: $(pwd)/.venv"
echo "要激活虚拟环境，请运行: source .venv/bin/activate"
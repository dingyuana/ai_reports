#!/bin/bash

# AI报告批阅系统停止脚本

echo "========================================="
echo "   AI报告批阅系统 - 停止脚本"
echo "========================================="

# 首先清理所有批阅相关进程
echo "正在停止所有批阅任务..."
pkill -9 -f "python.*api_server" 2>/dev/null
pkill -9 -f "uvicorn.*api_server" 2>/dev/null
pkill -9 -f "python.*grade" 2>/dev/null
sleep 2

# 检查PID文件是否存在
if [ ! -f "logs/server.pid" ]; then
    echo "警告: 未找到logs/server.pid文件"
    echo "尝试查找并终止占用8000端口的进程..."
    
    # 查找并终止占用8000端口的进程
    PID=$(lsof -ti:8000 -sTCP:LISTEN)
    if [ -n "$PID" ]; then
        echo "找到进程ID: $PID"
        kill $PID
        sleep 2
        if ps -p $PID > /dev/null; then
            echo "强制终止进程..."
            kill -9 $PID
        fi
        echo "✓ 服务器已停止"
    else
        echo "未找到运行中的服务器"
    fi
    exit 0
fi

# 读取PID
PID=$(cat logs/server.pid)

# 检查进程是否存在
if ! ps -p $PID > /dev/null; then
    echo "进程 $PID 不存在"
    rm -f logs/server.pid
    echo "✓ PID文件已清理"
    exit 0
fi

# 终止进程
echo "正在停止服务器（PID: $PID）..."
kill $PID

# 等待进程结束
for i in {1..10}; do
    if ! ps -p $PID > /dev/null; then
        echo "✓ 服务器已停止"
        rm -f logs/server.pid
        exit 0
    fi
    sleep 1
done

# 如果进程仍在运行，强制终止
echo "强制终止进程..."
kill -9 $PID 2>/dev/null
sleep 1

# 清理PID文件
rm -f logs/server.pid

# 最终清理
echo "正在最终清理..."
pkill -9 -f "python.*api_server" 2>/dev/null
pkill -9 -f "uvicorn.*api_server" 2>/dev/null
pkill -9 -f "python.*grade" 2>/dev/null

echo "✓ 服务器已强制停止"
echo "✓ 所有批阅任务已中止"

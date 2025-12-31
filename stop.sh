#!/bin/bash

# AI 智能教学助手停止脚本

echo "🛑 停止 AI 智能教学助手..."

if [ ! -f server.pid ]; then
    echo "⚠️  未找到 server.pid 文件"
    echo "尝试查找 uvicorn 进程..."
    PID=$(ps aux | grep "uvicorn app:app" | grep -v grep | awk '{print $2}' | head -1)
    if [ -n "$PID" ]; then
        echo "找到进程 PID: $PID"
        kill $PID
        echo "✅ 服务已停止"
    else
        echo "❌ 未找到运行中的服务"
    fi
    exit 0
fi

PID=$(cat server.pid)

if ps -p $PID > /dev/null 2>&1; then
    echo "停止进程 PID: $PID..."
    kill $PID
    sleep 2
    
    # 强制停止
    if ps -p $PID > /dev/null 2>&1; then
        echo "强制停止..."
        kill -9 $PID
    fi
    
    echo "✅ 服务已停止"
    rm -f server.pid
else
    echo "⚠️  进程不存在 (PID: $PID)"
    rm -f server.pid
fi

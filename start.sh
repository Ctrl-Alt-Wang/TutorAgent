#!/bin/bash

# AI 智能教学助手启动脚本

echo "🚀 启动 AI 智能教学助手..."
echo ""

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "⚠️  警告: .env 文件不存在"
    echo "请复制 .env.example 并配置你的 API Key："
    echo "  cp .env.example .env"
    echo "  然后编辑 .env 文件"
    exit 1
fi

# 检查依赖
echo "📦 检查 Python 依赖..."
pip list | grep -q fastapi
if [ $? -ne 0 ]; then
    echo "正在安装依赖..."
    pip install -q -r requirements.txt
fi

# 创建数据库目录
mkdir -p database

# 停止旧进程
if [ -f server.pid ]; then
    OLD_PID=$(cat server.pid)
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "🛑 停止旧服务 (PID: $OLD_PID)..."
        kill $OLD_PID 2>/dev/null
        sleep 2
    fi
fi

# 启动服务
echo "✨ 启动服务..."
nohup uvicorn app:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
NEW_PID=$!
echo $NEW_PID > server.pid

sleep 3

# 检查启动状态
if ps -p $NEW_PID > /dev/null; then
    echo ""
    echo "✅ 服务启动成功！"
    echo ""
    echo "📍 访问地址："
    echo "   本地: http://localhost:8000"
    echo "   网络: http://$(hostname -I | awk '{print $1}'):8000"
    echo ""
    echo "📝 查看日志: tail -f server.log"
    echo "🛑 停止服务: ./stop.sh"
    echo ""
else
    echo "❌ 服务启动失败"
    echo "查看日志: cat server.log"
    exit 1
fi

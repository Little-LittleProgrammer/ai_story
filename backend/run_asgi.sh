#!/bin/bash
# ASGI服务器启动脚本 - 支持真正的SSE流式输出
# 使用Daphne而非runserver以支持异步流式响应

cd "$(dirname "$0")"

echo "🚀 启动ASGI服务器(Daphne)..."
echo "📡 支持SSE流式输出"
echo "🌐 地址: http://localhost:8000"
echo ""

# 使用Daphne运行ASGI应用
daphne -b 0.0.0.0 -p 8000 config.asgi:application

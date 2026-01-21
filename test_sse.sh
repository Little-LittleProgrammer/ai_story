#!/bin/bash
# 测试SSE流式接口

PROJECT_ID="d4fad65b-d862-4540-ad32-1061ccaa91a9"
API_URL="http://localhost:8000/api/v1/projects/projects/${PROJECT_ID}/stream/"

echo "🧪 测试SSE流式接口..."
echo "📡 URL: ${API_URL}"
echo "⏰ 实时输出(每秒一个emoji):"
echo ""

curl -N \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzYwOTUyMzcxLCJpYXQiOjE3NjA5MjM1NzEsImp0aSI6ImY4Yzk2YjNiNjZjNTQxNjdiMTY4ODZlY2RjMDFlMmJjIiwidXNlcl9pZCI6MX0.fmuxOMV_WDN1Ha54ewGnWiFZ14FxwAiQ6FwyVDrW81A" \
  -X POST \
  "${API_URL}"

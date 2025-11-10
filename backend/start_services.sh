#!/bin/bash
# AI Story 服务启动脚本
# 用于快速启动所有必需的服务

set -e

echo "🚀 启动 AI Story 服务..."
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查Redis是否运行
check_redis() {
    echo -n "检查 Redis 服务... "
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 运行中${NC}"
        return 0
    else
        echo -e "${RED}✗ 未运行${NC}"
        return 1
    fi
}

# 启动Redis
start_redis() {
    echo "启动 Redis..."
    if command -v brew &> /dev/null; then
        # macOS with Homebrew
        brew services start redis
        echo -e "${GREEN}✓ Redis 已启动 (Homebrew)${NC}"
    elif command -v systemctl &> /dev/null; then
        # Linux with systemd
        sudo systemctl start redis
        echo -e "${GREEN}✓ Redis 已启动 (systemd)${NC}"
    else
        echo -e "${YELLOW}⚠ 请手动启动 Redis${NC}"
        echo "  macOS: brew services start redis"
        echo "  Linux: sudo systemctl start redis"
        echo "  Docker: docker run -d -p 6379:6379 redis:latest"
    fi
}

# 检查并启动Redis
if ! check_redis; then
    echo ""
    read -p "是否启动 Redis? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        start_redis
        sleep 2
        check_redis
    else
        echo -e "${RED}错误: Redis 未运行，无法继续${NC}"
        exit 1
    fi
fi

echo ""
echo "选择启动模式:"
echo "1) 完整模式 (Django + Celery Worker)"
echo "2) 仅 Django 服务器"
echo "3) 仅 Celery Worker"
echo "4) 测试模式 (运行测试脚本)"
echo ""
read -p "请选择 (1-4): " -n 1 -r
echo ""

case $REPLY in
    1)
        echo -e "${GREEN}启动完整模式...${NC}"
        echo ""

        # 启动Celery Worker (后台)
        echo "启动 Celery Worker..."
        uv run celery -A config worker -Q llm,image,video -l info --detach
        echo -e "${GREEN}✓ Celery Worker 已启动 (后台运行)${NC}"
        echo ""

        # 启动Django服务器 (前台)
        echo "启动 Django ASGI 服务器..."
        echo -e "${YELLOW}提示: 按 Ctrl+C 停止服务${NC}"
        echo ""
        sleep 2
        ./run_asgi.sh
        ;;

    2)
        echo -e "${GREEN}启动 Django 服务器...${NC}"
        echo ""
        echo -e "${YELLOW}提示: 按 Ctrl+C 停止服务${NC}"
        echo ""
        sleep 1
        ./run_asgi.sh
        ;;

    3)
        echo -e "${GREEN}启动 Celery Worker...${NC}"
        echo ""
        echo -e "${YELLOW}提示: 按 Ctrl+C 停止服务${NC}"
        echo ""
        sleep 1
        uv run celery -A config worker -Q llm,image,video -l info
        ;;

    4)
        echo -e "${GREEN}运行测试脚本...${NC}"
        echo ""
        python test_celery_redis.py
        ;;

    *)
        echo -e "${RED}无效选择${NC}"
        exit 1
        ;;
esac

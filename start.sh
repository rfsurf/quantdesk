#!/bin/bash
# QuantDesk 一键启动脚本
# 启动 PostgreSQL + Redis (Docker) + 后端 + 前端

set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "╔══════════════════════════════════════╗"
echo "║       QuantDesk v2.0                 ║"
echo "║   零代码量化策略工具                   ║"
echo "╚══════════════════════════════════════╝"
echo ""

# 1. 启动数据库
echo "► 启动 PostgreSQL + Redis..."
docker compose -f "$DIR/docker-compose.yml" up -d postgres redis 2>/dev/null
sleep 2

# 2. 等待 PostgreSQL 就绪
echo "► 等待 PostgreSQL 就绪..."
for i in $(seq 1 15); do
  if docker compose -f "$DIR/docker-compose.yml" exec -T postgres pg_isready -U quantdesk 2>/dev/null; then
    echo "  PostgreSQL 已就绪 ✓"
    break
  fi
  sleep 1
done

# 3. 创建表
echo "► 初始化数据库表..."
cd "$DIR"
.venv/bin/python3 -c "
import sys; sys.path.insert(0, '.')
import asyncio
from backend.database import init_db
asyncio.run(init_db())
print('  数据库表已创建 ✓')
"

# 4. 启动后端
echo "► 启动后端 (port 8000)..."
.venv/bin/uvicorn backend.app:app --host 0.0.0.0 --port 8000 &
echo "  后端 PID: $!"

# 5. 启动前端
echo "► 启动前端 (port 3000)..."
cd "$DIR/frontend"
npx next dev -p 3000 &
echo "  前端 PID: $!"

echo ""
echo "═══════════════════════════════════════"
echo "  QuantDesk 启动完成！"
echo ""
echo "  前端:   http://localhost:3000"
echo "  后端:   http://localhost:8000"
echo "  API文档: http://localhost:8000/docs"
echo ""
echo "  停止:   kill %1 %2 && docker compose stop"
echo "═══════════════════════════════════════"

wait

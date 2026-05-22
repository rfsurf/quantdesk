# QuantDesk — 零代码量化策略工具

面向国内散户的个人量化工作台，不用写代码也能搭建、回测、导出策略。

## 核心功能

- **拖拽搭策略** — 25+因子可视化拖拽，ReactFlow画布连接条件树
- **秒级回测** — A股真实数据，净值曲线 + 8项绩效指标 + AI诊断
- **策略体检卡** — 12维度×100分制健康评分
- **WFA前向分析** — Standard/Anchored双模式，防止过拟合
- **参数网格优化** — 自动搜索最优参数组合
- **QMT一键导出** — 生成可拷贝的Python脚本
- **MCP Agent Gateway** — 让Cursor/Claude Code直接操控平台
- **AI三层商业模式** — Free/Pro/BYOK

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + pandas + PostgreSQL/TimescaleDB |
| 前端 | Next.js 14 + ReactFlow + ECharts + Tailwind CSS |
| 数据 | AKShare (东方财富行情) |
| AI | DeepSeek / Ollama / 用户自带API Key |

## 快速启动

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/quantdesk.git
cd quantdesk

# 2. 启动服务（一键脚本）
./start.sh

# 或手动启动：
docker compose up -d postgres
cd backend && python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn backend.app:app --host 0.0.0.0 --port 8000
cd frontend && npm install && npm run dev
```

## 访问地址

| 服务 | 地址 |
|------|------|
| 前端页面 | http://localhost:3000 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |

## 账号

- 管理员：`admin@quantdesk.dev`
- 普通用户：任意邮箱注册
- 开发模式验证码：`000000`

## 项目结构

```
quantdesk/
├── backend/           # FastAPI 后端
│   ├── routers/       # 9个路由模块
│   ├── services/      # 3个服务层
│   ├── backtest_engine.py
│   ├── wfa_engine.py
│   ├── scorecard.py
│   ├── ai_client.py
│   └── ...
├── frontend/          # Next.js 前端
│   ├── src/
│   │   ├── app/       # 11个页面路由
│   │   ├── components/
│   │   └── lib/
│   └── ...
├── docker-compose.yml
├── start.sh
└── README.md
```

## 借鉴的开源项目

- [buffett-oracle-analyzer](https://github.com/BruceLanLan/buffett-oracle-analyzer) — 策略体检评分卡
- [lo2cin4bt](https://github.com/lo2cin4/lo2cin4bt) — WFA前向验证
- [QuantDinger](https://github.com/brokermr810/QuantDinger) — AI生成 + MCP Gateway
- [OpenAlice](https://github.com/TraderAlice/OpenAlice) — 策略版本Git化

## License

MIT
# 校园论坛

一个面向校园的全栈社区论坛：发帖讨论、二手交易、实时私信，举报内容由 AI 自动审核。

在线地址：https://zcfe.online

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI · SQLAlchemy(async) · Alembic · MySQL · Redis |
| 前端 | Vue 3 · Vite |
| 认证 | JWT 双 Token（Access + Refresh，JTI 黑名单） |
| 实时通讯 | WebSocket（私信） |
| AI 审核 | 通义千问 qwen 审查举报内容 |
| 部署 | 腾讯云轻量服务器 · Nginx · HTTPS · systemd |

## 核心功能

- **用户系统**：注册/登录、JWT 双 Token、等级体系、管理员角色
- **内容社区**：板块分类、帖子发布/浏览、评论与楼中楼回复、点赞、收藏
- **二手交易**：商品发布、分类筛选、在售/已售状态管理、商品图片
- **实时私信**：WebSocket 双向实时通讯，消息即时到达
- **通知系统**：点赞/评论/私信等事件实时通知，未读计数
- **AI 审核**：举报内容自动 AI 判定，违规帖子自动处理，降低人工管理成本

## 项目优势

- **全异步架构**：SQLAlchemy async + FastAPI，IO 密集型场景下吞吐更高
- **JTI 黑名单机制**：登出/改密后 token 立即失效，而非依赖过期时间，更安全
- **Alembic 数据库版本管理**：表结构变更可迁移、可回溯，上线不发愁
- **AI 审核代替人工**：举报处理全自动，适合校园场景的低成本运营
- **前后端分离**：Vue3 + FastAPI，构建产物可直接静态托管，部署简单

## 目录结构

```
├── routers/      # API 路由（用户/帖子/评论/私信/二手/AI 等 13 个模块）
├── models/       # 数据库模型（17 张表）
├── crud/         # 数据操作层
├── schemas/      # Pydantic 校验模型
├── ai_agent/     # AI 审核模块
├── migrations/   # Alembic 迁移脚本
├── tools/        # 工具类
└── frontend/     # Vue3 前端（Vite 构建）
```

## 快速开始

```bash
# 后端
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --host 0.0.0.0 --port 8000

# 前端
cd frontend
npm install
npm run dev
```

## 免责说明

本项目为校园学习实践项目，仅作技术交流使用。

# 校园论坛 · 二手交易平台

基于 FastAPI 的全栈校园社区:发帖讨论、二手交易、实时私信,举报内容由 AI 自动审核。

**在线地址**:[https://zcfe.online](https://zcfe.online)

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI · SQLAlchemy 2.0 (async) · Alembic · MySQL · Redis |
| 前端 | Vue 3 · Vite |
| 认证 | JWT 双 Token:Access 1h / Refresh 2d 轮换,SHA-256 哈希落库,JTI 黑名单 |
| 实时通讯 | WebSocket(私信) |
| AI 审核 | 通义千问 qwen |

## 功能

- **用户**:注册 / 登录、refresh token 轮换、等级经验体系、管理员角色
- **社区**:板块分类、帖子、评论楼中楼、点赞、收藏、通知(未读计数)
- **二手交易**:商品发布、分类筛选、在售 / 已售状态、商品图片上传
- **实时私信**:WebSocket 双向通讯,历史消息分页
- **内容安全**:举报 → AI 判定 → 违规自动删帖并通知双方,AI 不可用时降级人工

## 快速开始

### 后端

```bash
git clone https://github.com/Mangran-mang/Campus-Forum-FastAPI.git
cd Campus-Forum-FastAPI

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.lock

cp .env.example .env             # 填入自己的密钥与数据库
cp alembic.ini.example alembic.ini
alembic upgrade head

uvicorn main:app --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## 环境变量(.env)

| 变量 | 说明 |
|---|---|
| `JWT_SECRET` | JWT 签名密钥,必填 |
| `JWT_ALGORITHM` | 签名算法,必填(HS256) |
| `DATABASE_URL` | MySQL 连接串:`mysql+aiomysql://user:pass@127.0.0.1:3306/dbname?charset=utf8mb4`,必填 |
| `API_KEY` | 通义千问 API Key,举报审核用,必填 |
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_PASSWORD` | Redis 连接(JTI 黑名单、举报去重),默认 `localhost:6379` |
| `CORS_ORIGINS` | 允许的前端源,逗号分隔,如 `http://localhost:5173` |

## 测试

```bash
python -m pytest tests/ -q
```

单元测试覆盖安全原语(密码哈希 / JWT 签发解码)、查询构造(LIKE 转义 / 条件拼装)与异常处理,不依赖数据库。

## 目录结构

```
├── routers/      # API 路由(用户 / 帖子 / 评论 / 私信 / 商品 等 13 个模块)
├── crud/         # 数据访问层
├── models/       # SQLAlchemy 模型(17 张表)
├── schemas/      # Pydantic 请求 / 响应模型
├── ai_agent/     # AI 内容审核(通义千问)
├── tools/        # 认证依赖、统一异常、日志、WebSocket 连接管理
├── config/       # pydantic-settings 配置、数据库 / Redis 连接
├── migrations/   # Alembic 迁移
├── tests/        # pytest 单元测试
└── frontend/     # Vue 3 前端
```

## 更新日志

见 [更新日志.md](更新日志.md)。

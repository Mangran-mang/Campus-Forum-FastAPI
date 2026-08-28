from sqlalchemy.ext.asyncio import (
    create_async_engine, async_sessionmaker, AsyncSession,
)
from config.config import Config

DATABASE_URL = Config.DATABASE_URL

# 数据库引擎
async_engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,# 超过这个时间就关闭
    pool_pre_ping=True,
)
"""
echo=True是否打印执行的 SQL 语句与参数
echo_pool打印连接池的创建、获取、回收日志
"""
# 会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, class_=AsyncSession,  # 指定会话类型是异步，AsyncSession是ORM会话
    expire_on_commit=False,  # 提交事务后依然可以访问那个orm对象
)


async def get_database():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

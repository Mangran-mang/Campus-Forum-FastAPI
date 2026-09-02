from redis.asyncio import Redis
from config.config import Config
import logging

logger = logging.getLogger(__name__)

JTI_EXPIRY = 3600# JTI就是JWT的ID

# 创建一个Redis客户端连接实例
redis_kwargs = dict(
    host=Config.REDIS_HOST,
    port=Config.REDIS_PORT,
    db=0,
    decode_responses=True,  # 将返回值转换为字符串
)
if Config.REDIS_PASSWORD:
    redis_kwargs["password"] = Config.REDIS_PASSWORD

token_blocklist = Redis(**redis_kwargs)

async def add_jti_to_blocklist(jti: str,expiry:int=JTI_EXPIRY):
    """
    将JTI添加到黑名单中
    默认过期时间为1小时
    """
    try:
        await token_blocklist.set(name=jti, value="", ex=expiry)
    except Exception as e:
        logger.warning(f"JTI添加到黑名单失败{e}")

async def is_jti_in_blocklist(jti: str) -> bool:
    """
    检查JTI是否在黑名单中
    并返回True或False
    Redis 不可用时降级放行，风险：已拉黑 token 在故障窗口内可用
    """
    try:
        jti = await token_blocklist.get(name=jti)
        return jti is not None
    except Exception as e:
        logger.warning(f"检查黑名单缓存失败{e}")
        return False

async def try_report_deduplicate(post_id: int, user_uid: str, ttl: int = 86400) -> bool:
    """
    举报去重：同一用户对同一帖子在 ttl 秒内只能举报一次
    使用 SET NX EX 原子操作，只有 key 不存在时才设置成功
    返回 True 表示首次举报（放行），False 表示重复举报
    Redis 异常时放行（保证举报功能可用，只是失去去重保护）
    """
    key = f"report:{post_id}:{user_uid}"
    try:
        # nx=True：仅当 key 不存在时写入成功，返回 True
        result = await token_blocklist.set(name=key, value="1", nx=True, ex=ttl)
        return bool(result)
    except Exception as e:
        logger.warning(f"检查举报去重缓存失败{e}")
        return True

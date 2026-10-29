
from redis.asyncio import Redis
from config.config import Config
from datetime import date
import logging


logger = logging.getLogger(__name__)

JTI_EXPIRY = 3600# 到期时间默认常量

DAILY_ACTIVE_TTL = 172800 # 48*60*60 两天的秒数


# 连接参数字典
redis_kwargs = dict(
    host=Config.REDIS_HOST,
    port=Config.REDIS_PORT,
    db=0,
    decode_responses=True,  # 将返回值转换为字符串
)
if Config.REDIS_PASSWORD:
    redis_kwargs["password"] = Config.REDIS_PASSWORD
# 创建一个Redis客户端连接实例，这里创建的是存黑名单的实例
token_blocklist = Redis(**redis_kwargs)
# redis客户端别名，实际上和黑名单客户端是同一个，但为了方便区分作用，所以改名了
redis_client = token_blocklist


async def add_jti_to_blocklist(jti: str,expiry:int=JTI_EXPIRY):
    """
    将JTI添加到黑名单中
    默认过期时间为1小时
    """
    try:
        await token_blocklist.set(name=jti, value="", ex=expiry)# 这里的ex就是所谓的TTL,代表了过期时间,设了redis才会自动清理
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

async def mark_daily_active(user_uid:str)->None:
    """
    标记用户每日活跃
    """
    key = f"active:{date.today().isoformat()}"  # 以今天日志为键
    try:
        added = await token_blocklist.sadd(key, user_uid)# sadd往集合中新增元素
        if added:
            await token_blocklist.expire(key, DAILY_ACTIVE_TTL)# expire防止内存泄漏
    except Exception as e:
        logger.warning("记录日活失败: %s", e)

async def get_daily_active_count(day: date) -> int:
    """取某天的活跃用户数；Redis 不可用或当天无数据都返回 0"""
    try:
        return await token_blocklist.scard(f"active:{day.isoformat()}")# scard返回集合元素个数
    except Exception as e:
        logger.warning("读取日活失败: %s", e)
        return 0


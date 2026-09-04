import logging
import hashlib

logger = logging.getLogger(__name__)
from passlib.context import CryptContext# 密码哈希库
from datetime import timedelta, datetime, timezone
import jwt

from config.config import Config
import uuid

ACCESS_TOKEN_EXPIRE= 3600

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# 加密函数
def get_password_hash(password):
    return pwd_context.hash(password)
# 验证密码函数
def verify_password(plain_password, hashed_password):
    # verify函数会把传入的密码哈希后去和数据库的哈希值进行对比
    return pwd_context.verify(plain_password, hashed_password)

# 该函数用来创建访问令牌和刷新令牌，通过refresh变量区分
def create_access_token(user_data: dict,expiry:timedelta = None,refresh:bool = False):
    """
    创建两种令牌
    载荷包括用户数据，到期时间，随机的uid，是否为刷新令牌
    user_data具体传了什么，由调用它的函数决定，本系统默认传了email和uid
    所以载荷中的user对应的也是一个字典{email和uid}
    """
    # 有效载荷是想要在令牌中编码为json对象的数据
    payload = {}

    payload['user'] = user_data
    payload['exp'] = datetime.now(timezone.utc) + (expiry if expiry else timedelta(seconds=ACCESS_TOKEN_EXPIRE))
    payload['jti'] = str(uuid.uuid4())
    payload['refresh'] =  refresh

    token = jwt.encode(
        payload=payload,
        key= Config.JWT_SECRET,
        algorithm = Config.JWT_ALGORITHM
    )
    # print(f"这里！！！！！{Config.JWT_ALGORITHM}")
    return token

# 解码令牌
def decode_token(token:str):
    """
    尝试解码，失败则返回None
    这个函数相当于一个验证函数，对token进行拆分验证，以此来确定是不是我们生产的token
    注意:pyjwt 库的 decode 方法里，algorithms 参数要求传入列表（list），比如 ["HS256"]
    """
    # print("解码令牌为"+token)
    try:
        token_data = jwt.decode(
            jwt=token,
            key=Config.JWT_SECRET,
            algorithms=[Config.JWT_ALGORITHM]
        )
        return token_data
    except jwt.PyJWTError as e:
        logger.exception(e)
        return None

def hash_token(token: str) -> str:
    """
    对 refresh token 做单向 sha256 哈希，只用于「落库 + 比对」，绝不回传给前端

    ## 为什么不用 bcrypt
    bcrypt 的慢哈希是给低熵密码（人想出来的）防暴力破解的；
    JWT 是 256 位高熵随机串，暴力破解不现实，快哈希即可（GitHub 存个人访问令牌同理）。

    ## 为什么不需要盐
    盐防的是「相同低熵密码跨用户撞库」，而每个 token 的 jti 都唯一，天然高熵。

    ## 为什么验证不需要"解密"
    单向函数同输入必同输出：客户端带原始 token 来，服务端再算一次哈希去比对库里那份即可。
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
## 两种模型

#### Pydantic模型

Pydantic 是一个 **Python 数据验证、解析和序列化库**，能够轻松实现

数据验证、

序列化（model.model_dump 生成字典，model.model_dump_json一键生成 JSON）

与反序列化（model_validate解析成模型实例,需配合配置使用）

安全提示

```
class PostsCreateModel(BaseModel):
    """
    需要标题、内容、作者uid
    """
    title: str
    content: str
    summary: Optional[str] = None
    is_public: bool = True
    author_uid: str

    model_config = {"from_attributes": True}
```

如图中所示，通常需要继承自BaseModel，继承后，该类就能拥有上述效果

from_attributes=True的作用是可以使模型从ORM对象中创建

字段类型中的Optional，代表着该字段可选填

大多时候，它们用在路由函数中的参数类型限制中，这样就能精准检查用户的输入内容，且可以通过**Field**作用于 Pydantic 模型内部的字段约束(除此之外还有相同作用的Query/Path/Body，它们分别用于url查询、路由路径、json请求体)

总的来说，就是它能在字段类型错误、为空、字段名错误时报错，能够极其方便的将模型与json或字典来回转化，如果要使用orm模型直接填充pydantic模型，就需要在配置中更改"from_attributes":True

#### ORM模型

通常我们写的orm模型都要继承自DeclarativeBase，于是它们具备了映射数据库表的能力，类名、类变量会自动对应数据库的表名、列名

```
class Base(DeclarativeBase):
    created_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        comment="创建时间"
    )
```

```
class User(Base):
    __tablename__ = "user"

    uid: Mapped[str] = mapped_column(String(36),primary_key=True,nullable= False,default=uuid.uuid4,comment="用户id")
    email: Mapped[str] = mapped_column(String(255),unique= True,nullable= False,comment="用户账号")
    password: Mapped[str] = mapped_column(String(255),nullable= False,comment="用户密码")
    username: Mapped[Optional[str]] = mapped_column(String(50),nullable= True,comment="用户名")
    nickname: Mapped[Optional[str]] = mapped_column(String(50),nullable= True,default="无",comment="昵称")
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255),nullable= True,default="",comment="头像")
    gender: Mapped[str] = mapped_column(Enum('男','女','未知'),nullable= False,comment="性别",default='未知')
    is_active: Mapped[bool] = mapped_column(default=True,comment="是否激活")
    is_superuser: Mapped[bool] = mapped_column(default=False,comment="是否是管理员")

    updated_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间"
    )
    posts: Mapped["Posts"] = relationship("Posts",back_populates="author")
    token: Mapped["Token"] = relationship("Token",back_populates="user",uselist= False)
```

它们需要有__tablename__来对应表名，以及字段来对应列名

我们通常先写一个基类，这个基类通常有其他类应有的公共字段，如更新时间、插入时间等

比较常用的Mapped，它告诉orm，这是数据库表中的列，而不是普通的什么类型

而Mapped中的内容，是python自带的类型，后面mapped_column中参数的类型才是从sqlalchemy.orm导入的类型，比如DateTime对应的才是MySQL数据库中的DATETIME类型

于是乎，读写数据就能从datetime和DateTime间相互转换了(该转换是 SQLAlchemy 自动完成的)

mapped_column的作用和Field它们类似，但它用于数据库表中的限制，所以参数内容不太一样



## 数据库的配置与配置文件

```
from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
    """
    配置类
    BaseSettings(承自 Pydantic 的 BaseModel) 是配置管理的核心基类
    SettingsConfigDict 是用来给 BaseSettings 配置行为的 “规则字典”
    BaseSeetings在实例化后为字段赋值
    """
    model_config = SettingsConfigDict(env_file=".env",extra="ignore")

    JWT_SECRET: str
    JWT_ALGORITHM: str
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    API_KEY: str
    DATABASE_URL: str

Config = Settings()
"""
为什么要实例化Settings
因为实例化它之后,env才会被读
那些字段才会加载
"""
```

SettingsConfigDict的用法就是指定文件和规则，.env就是约定俗成的隐藏文件，里面会写着一些不方便公开的信息，诸如ai的API或者数据库的url，jwt的加密方法以及密钥，redis的地址和端口这些

然后在配置模块中写好完全同名的变量，以便读取文件后为它们赋值，此后它们将通过这个类的实例来调用；当然也可以将api等信息加载到环境变量中然后读取

为了方便区分，配置信息的加载与配置内容本身是分开的

比如redis的配置和数据库依赖的配置

```
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from config.config import Config


DATABASE_URL = Config.DATABASE_URL

# 数据库引擎
async_engine = create_async_engine(DATABASE_URL,pool_size=10,max_overflow=20)
"""
echo=True是否打印执行的 SQL 语句与参数
echo_pool打印连接池的创建、获取、回收日志
"""
# 会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_= AsyncSession,# 指定会话类型是异步，AsyncSession是ORM会话
    expire_on_commit=False# 提交事务后依然可以访问那个orm对象
)

async def get_database():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
```

数据库依赖的使用：

先写数据库url

创建数据库引擎（可以是异步也可以是同步），其中配置要写平常连接池可提供的连接和最大连接数

创建会话工厂，来自sqlalchemy.ext.asyncio的async_sessionmaker函数，它的返回值是一个**异步会话工厂**，这个工厂是一个可调用对象，而我们每次调用这个工厂，它都会创建一个新的会话实例，所以它非常贴合“工厂”这个称呼，且每个会话在用完时都会自己关闭，会话间彼此隔离

而案例中的get_datebase就是方便我们调用这个会话工厂以创建会话对象，需要注意的是，每次调用这个函数都会调用一次AsyncSessionLocal()以别名session拿出去调用，

就像下面两行代码

with open("test.txt", "r", encoding="utf-8") as f:    

​		content = f.read()

然后赋值给某变量(此步骤叫依赖注入，而依赖注入说白了就是把返回的对象给某个变量而已)

注：AsyncSessionLocal是具体对象，AsyncSession才是类



总结：

`AsyncSessionLocal` = 造会话的**工厂**（提前配置好数据库地址、规则）；

`AsyncSessionLocal()` = 启动工厂，造出一个**会话工具**；

`async with ... as session` = 借用这个工具，同时自动帮你 “开门 / 关门”（拿连接、还连接）；

`yield session` = 把工具递给接口去干活；

接口干完活 → 自动归还连接，一切复位。

## CRUD业务函数

```
class UserService:
    async def crud_get_all_users(self, db: AsyncSession):
        """
        返回所有用户
        """
        users = select(User)
        result = await db.execute(users)
        return result.scalars().all()

    async def crud_add_new_user(self, db: AsyncSession, user: UserCreateModel):
        """
        创建后返回orm模型User对象
        """
        orm_user = User(**user.model_dump())
        orm_user.password = security.get_password_hash(user.password)
        db.add(orm_user)
        await db.commit()
        await db.refresh(orm_user)
        return orm_user
```

crud函数，通常专注于数据库表中内容的增删改查，而crud正是增删改查的英文缩写

在小的项目中，crud会和业务逻辑写一块，好吧这不重要

是否写到类中调用由个人喜好决定，我认为这样会更加清晰方便，当然也可以直接写crud函数，然后在需要的地方直接导入调用

而crud的使用通常需要数据库的参与，所以需要导入from sqlalchemy.ext.asyncio import AsyncSession，该类用来指定会话工具的类

至于crud实际的使用操作，就像使用数据库时写sql语句那样 ，不过变成了在python中通过一个中介工具来写sql语句，比如sqlalchemy

注：可以配合一些加密函数、自定义抛出异常来使用

## 路由函数

通常需要先写router = APIRouter(prefix="/api/user",tags=["用户管理"])

创建了一个「用户模块专属的路由容器」，前者路径后者标签

为什么是这样而不是app = FastAPI()，因为这样可以更加清晰的分开业务，以防接口过多导致混乱和难以维护

```
@router.get("/current_user")
async def get_current_user(
        user=Depends(get_user_by_token),
        user_check: bool = Depends(user_checker)
    ):
    """
    获取当前用户
    """
    return {"code":200,"message":"获取成功","data":user}
```

而@router.get是路由注册装饰器，就像@app.get一样，把函数注册成接口，不过是注册到分支的router中而不是主app中

而get（或post、delete什么都好啦）中的参数不只可以是固定路径，也可以像这样

```
@router.get("/get/{email}")
async def get_user_by_email(email:str,db:AsyncSession=Depends(get_database)):
    """
    通过邮箱获取用户
    """
    user = await user_service.crud_get_user_by_email(db,email)
    if user:
        return {"code":200,"message":"获取成功","data":user}
    else:
        return {"code":404,"message":"用户不存在"}
```

它们的区别belike

| 参数类型                         | 位置                                     | 典型场景                                  | 定义方式                            |
| :------------------------------- | :--------------------------------------- | :---------------------------------------- | :---------------------------------- |
| **路径参数（Path Parameters）**  | URL 路径中，`/api/user/{user_id}`        | 资源唯一标识（用户 ID、订单 ID）          | 路径里写 `{param}`，函数里声明类型  |
| **查询参数（Query Parameters）** | URL 问号后，`/api/user?page=1`           | 分页、过滤、排序、可选条件                | 函数里直接写参数（带 / 不带默认值） |
| **请求体（Request Body）**       | HTTP 请求体（JSON/Form）                 | 新增 / 修改复杂数据（用户注册、提交表单） | 用 Pydantic 模型声明                |
| **表单参数（Form Data）**        | `application/x-www-form-urlencoded` 表单 | 传统登录、表单提交                        | 用 `Form(...)` 声明                 |

1.在路径参数中，路径中{user_id}占位符是必填的，且会自动替换掉函数中的参数user_id:int，同时一个路径中也可以有多个路径参数

2.查询参数，我个人感觉和路径参数有差别但不大，查询参数的内容可以更简单的写详细一些，且也是在url中![image-20260530213941455](C:\Users\xbox\AppData\Roaming\Typora\typora-user-images\image-20260530213941455.png)

3.请求体参数，就是post请求

一般get请求的路由函数中，参数只有一些依赖注入的内容，post请求相当于把url路径中的参数，写到了请求体中，这样更加的自定义化，而且更加美观易读

```
@router.post("/add")
async def add_new_user(user_data:UserCreateModel,db:AsyncSession=Depends(get_database)):
    """
    添加用户
    """
    if await user_service.crud_user_exists(db,user_data.email):
        raise HTTPException(status_code=400,detail="用户已存在")

    user = await user_service.crud_add_new_user(db,user_data)

    return {"code":200,"message":"添加成功","data":user}
```

如图所示，该路由函数不仅用到了一个会话工具，以及一个Pydantic模型（你应该记得它通常用来做校验）

然后该路由函数中会包含具体的crud函数或其他什么业务逻辑

把模型、crud、业务、路由，四层分开，是为了更专注自己的工作

而路由层，则支付测接收参数、统一响应、做简单校验和调用业务逻辑

4.表单参数

@app.post("/login/")
async **def** login(
  username: str = Form(),
  password: str = Form(), 
):
  **return** {"username": username}

就像上面声明的那样，也是post请求，但不需要请求体，而是以一个表单取代

## 自定义异常与注册

##### 使用自定义异常的三个步骤

###### 1.声明自定义异常类

必须继承 Python 内置的 `Exception` 类，否则无法被 FastAPI 的异常机制捕获。

这个类里可以什么都不写，也可以定义额外的属性belike

```
class UserException(Exception):
    """用户方面出现问题"""
    pass


class PostException(Exception):
    """帖子方面出现问题"""
    def __init__(self, error_type: str, message: str):
        self.error_type = error_type
        self.message = message
```

###### 2.写异常处理函数

处理函数既可以写死，又可以传递动态信息，分别对应上一步

```
async def post_not_found_error(request: Request, exc: PostException):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={
            "异常类型": exc.error_type,
            "异常信息": exc.message,
        }, )


async def user_not_found_error(request: Request, exc: UserException):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={
            "异常类型": "用户异常",
            "异常信息": "未查找到对应的用户信息",
        }, )
```

就像图中这样，如果只想写一个处理用户不存在的异常，那就写死

否则写成获取动态信息会更加通用，在抛出异常时写对应的内容即可

而异常处理函数中必须按序写这两个参数request: Request和exc: PostException

第一个参数是当前触发异常的请求对象，第二个参数代表被捕获到的异常实例

至于它们是怎么被使用的，我觉得不需要关心

###### 3.挂载到FastAPI应用

用fastapi实例名.add_exception_handler(异常类型,处理函数)来挂载

然后在你抛出某异常时，就会自动调用你写好的异常处理函数了

## 中间件

目前我对中间件的理解比较浅，也许未来会不断加深

我认为，中间件就是把客户端发出的请求，进行二次加工，也就是在把请求传递给服务器之前先拦下来，做一些标记、处理然后再给服务器

比如登录验证，使用中间件注册到fastapi后，所有路由函数，都要经过它

##  JWT的使用演示

需用到pyjwt库

```
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
    payload['exp'] = datetime.now() + (expiry if expiry else timedelta(seconds=ACCESS_TOKEN_EXPIRE))
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
        logging.exception(e)
        return None
```

#### 创建令牌

首先我们用jwt.encode()来生成令牌

encode需要三个参数

1.payload：一个字典，它包含了你想放在里面的信息，比如用户具体数据、token到期时间、随机uid、令牌的种类等什么都可以，甚至你喜欢什么口味的披萨，案例中的ACCESS_TOKEN_EXPIRE是一个期望的到期时间（这里是3600秒）

2.key：签名密钥

3.algorithm：签名算法

我们因为有这个载荷，每个用户数据都不同，且每次都会生成随机的uuid，所以token大概率不会重复

而这个token就是我们验证用户信息的关键

但需要注意的是datetime.now()在实际的工作中，这样写大概率不合适，而应该换成时区的时间

#### 解码令牌

注释中写的比较详细了，主要作用就是验证token和拿到token中用户的信息

#### 令牌的使用

###### 1.取token

首先写一个类，继承自HTTPBearer，可以重写__init__，然后改写auto_error为True以返回错误信息

重写call函数，说是重写，但实际上也是为了在调用时自动触发，让它像函数一样方便，request就是客户端发送的请求，就像中间件拦截request那样，

这里作为依赖注入时也能发挥和中间件相同的作用，不过这里是只拿过来检察一下Authorization请求头，

而做法就是调用父类的call方法，用creds接收一下返回值，creds中的credentials则是我们需要的token部分

###### 2.验证token

我们已经拿到token了，于是可以做一些操作了，比如检查token中的时间是否到期、检查它是哪种类型的令牌（推荐写子类来重写检查函数）、配合redis检查它是否在黑名单之类的

那么为什么能够做这些操作呢

关键在于request的获取，当该类实例化并注入时，就会拿到request，然后进行这一系列操作

## 依赖注入

依赖注入，本质就是把封装好的函数中返回的对象，赋值给某个变量

比如最常用的会话工具的依赖注入

```
async def get_database():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
```

其中yield出去的session，就是赋值给了某变量，然后它就能建立一个新连接来使用数据库了。

然后也可以有稍微复杂一些的使用，比如用户权限验证、token验证等

## 加密演示

```
from passlib.context import CryptContext# 密码哈希库

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# 加密函数
def get_password_hash(password):
    return pwd_context.hash(password)
# 验证密码函数
def verify_password(plain_password, hashed_password):
    # verify函数会把传入的密码哈希后去和数据库的哈希值进行对比
    return pwd_context.verify(plain_password, hashed_password)
```

CryptContext是哈希库passlib的核心工具类，用来处理密码哈希与验证

由于哈希算法的不可逆和安全性，所以通常一些密码加密都会使用它

schemes=["bcrypt"]指定要使用的哈希算法列表，按优先级排序

deprecated="auto"，用于平滑升级，比如列表中有两种算法，但旧算法密码是第二个算法来验证的，验证成功后，就会换成新的算法，而不用改密码，意思就是从就算发变成了新算法来加密

本例子中的pwd_context就是一个可以使用加密和验证的实例（我喜欢叫成工具）

然后就可以pwd_context.hash进行加密，加密后再把加密后的内容存到数据库中

## Redis的使用

redis也许安装好后配置，包括客户端和服务端，服务端的地址和端口需要记一下

配置好后我们在脚本中创建Redis实例

说白了就是写个函数用redis实例的set和get函数去读写，这样就能享受到它的缓存功能了

至少我现在的理解是这样的

## alembic数据迁移

Alembic 是 **SQLAlchemy 官方配套的数据迁移工具**

pip install alembic sqlalchemy

初始化alembic，alembic init 自定义文件夹名称

然后到alembic.ini文件中修改sqlalchemy.url为你的数据库连接地址

需要注意的是模型的导入，要让alembic能检测到你的模型

告诉alembic数据库已是最新状态alembic stamp head

生成迁移文件alembic revision --autogenerate -m "你要写的内容"

开始迁移alembic upgrade head

回滚版本alembic downgrade -1

## git版本控制

记录代码修改（写注释、加功能、改 bug）；代码写崩了，**一键回滚到上一个正常版本**；多人协作写项目，不会互相覆盖代码；把代码备份到 GitHub/Gitee 云端，永不丢失

第一次使用需安装git和配置用户信息

打开 `Git Bash`，执行下面两条命令，替换成你自己的信息：

```
# 设置用户名（自定义，比如昵称/英文名）
git config --global user.name "你的名字"

# 设置邮箱（GitHub/Gitee 注册邮箱）
git config --global user.email "你的邮箱@xxx.com"
```

查看是否配置成功：

```
git config --global --list
```

第一次使用git上传代码到仓库

1. **进入项目根目录**

   找到你的项目文件夹 → 右键 → `Git Bash Here`，终端会直接定位到项目目录。

2. **初始化本地 Git 仓库【首次独有步骤】**

   ```
   git init
   ```

   作用：在项目里生成隐藏的 `.git` 版本控制文件夹，开启 Git 管理。

3. **把所有文件加入暂存区**

   ```
   git add .
   ```

   - `.` 代表**当前目录所有文件 / 文件夹**
   - 只想上传单个文件：`git add 文件名`

4. **提交到本地版本库**

   ```
   git commit -m "第一次提交：上传完整项目源码"
   ```

   - `-m` 后面双引号里是**提交备注**，必填，简单描述本次操作。

5. **关联本地仓库 和 线上远程仓库【首次独有步骤】**

   把上一步复制的远程仓库地址粘贴进来：

   ```
   git remote add origin 你的远程仓库HTTPS地址
   ```

   ```
   git remote add origin https://gitee.com/xxx/my-demo.git
   ```

   - `origin` 是远程仓库的固定别名，不用修改。
   - 报错 `remote origin already exists`：说明之前关联过，先执行 `git remote remove origin` 再重试。

6. **推送到线上远程仓库【首次带额外参数】**

   ```
   git push -u origin main
   ```

   - 补充：部分老仓库默认分支是 `master`，就改成 `git push -u origin master`
   - `-u`：绑定本地分支和远程分支（**关键**，绑定后下次更新不用再写一长串）
   - 首次推送会弹窗要求输入代码平台的**账号密码**，输入后等待上传完成即可。

> 至此：你的完整项目就第一次成功传到云端仓库了。

1. **进入项目根目录**

   项目文件夹右键 → `Git Bash Here`

2. （可选）查看文件改动状态（推荐新手每次执行）

   ```
   git status
   ```

   红色 = 未暂存的修改，绿色 = 已暂存，用来确认哪些文件变了。

3. **暂存修改的文件**

   ```
   git add .
   ```

   改动少就指定文件：`git add 1.py index.html`

4. **提交到本地版本库**

   ```
   git commit -m "更新说明：修复XXbug / 新增XX功能"
   ```

5. **拉取线上最新代码【强烈建议必做】**

   ```
   git pull origin main
   ```

   作用：如果多人协作、或换过电脑提交过代码，先拉取云端最新内容，避免代码冲突。单人使用也建议养成习惯。

6. **推送到线上仓库**

   ```
   git push
   ```

   因为**第一次已经用 `-u` 绑定了分支**，这里直接简写 `git push` 即可，不用加其他参数。

> 至此：本次代码更新就同步到远程仓库了。

**第一次上传**：多了 `git init`（初始化）、`git remote add`（关联远程）、`git push -u`（绑定分支）三个**一次性步骤**；

**后续所有更新**：只循环 `git add → git commit → git pull → git push` 四步即可。

## 路由挂载及生命周期

为了模块和业务的分工清晰，我们通常把路由分开写

最后再统一到主脚本挂载

需要app.include_router函数，里面的参数就是指定的router实例



```
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --------------------------
    # 1. 【启动阶段】yield 之前的代码：应用启动时执行（只执行1次）
    # --------------------------
    print("如果需要改ORM模型，则到main函数中重新启用init_db函数")
    # await init_db()  # 被你注释掉的建表逻辑
    
    yield  # 关键分界点！yield 之后，FastAPI才会开始接收请求
    
    # --------------------------
    # 2. 【关闭阶段】yield 之后的代码：应用关闭时执行（只执行1次）
    # --------------------------

# 把 lifespan 注册给 FastAPI 实例
app = FastAPI(lifespan=lifespan)
```
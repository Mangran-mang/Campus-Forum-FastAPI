## 一、数据库的配置与配置文件

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

##### 配置文件的作用是什么

SettingsConfigDict的用法就是指定文件和规则，.env就是约定俗成的隐藏文件，里面会写着一些不方便公开的信息，诸如ai的API或者数据库的url，jwt的加密方法以及密钥，redis的地址和端口这些

##### 为什么要写model_config来接收类

Pydantic V2 约定：

类内部必须定义一个名为 `model_config` 的类属性，框架才会读取这个属性里的配置规则。

正确语法是**赋值**：`model_config = SettingsConfigDict(...)`，而不是裸写一行构造调用。

##### 配置文件怎么用

在配置模块中写好完全同名的变量，以便读取文件后为它们赋值，此后它们将通过这个类的实例来调用；当然也可以将api等信息加载到环境变量中然后读取

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

注意：在get_database函数的yield中可以接一个seesion.commit，这样事务就会自动提交

但不推荐这样做，因为会出奇怪的错误

##### 数据库依赖的使用：

先写数据库url：驱动协议://账号:密码@主机:端口/数据库名?额外参数(比如charset=utf8mb4)

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



## 二、两种模型

#### Pydantic模型

Pydantic 是一个 **Python 数据验证、解析和序列化库**，能够轻松实现

1. 数据验证、

2. 序列化（model.model_dump 生成字典，model.model_dump_json一键生成 JSON）

3. 与反序列化（model_validate解析成模型实例,需配合配置使用）

4. 安全提示;


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

如代码中所示，通常需要继承自BaseModel，继承后，该类就能拥有上述效果

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

##### 进阶内容

###### 其他参数：

```
class Bookmark(Base):
    __tablename__ = "bookmarks"
    __table_args__ = (
        UniqueConstraint("post_id", "user_uid", name="uq_user_post_bookmark"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="收藏id")
    post_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, comment="帖子id"
    )
    user_uid: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.uid", ondelete="CASCADE"), nullable=False, comment="收藏用户uid"
    )
```

这里用到了__table_args__，里面的参数UniqueConstraint限制了一个post_id对应一个user_uid

###### 关系映射:

​	这是sqlalchemy提供的便利用法

​	属性名：Mapped["类名"] = relationship(argument="类名",foreign_keys=[外键],back_populates="目标类的属性名"，remote_side="目标类的属性")，其中remote_side只在自连接时使用，foreign_keys在**两张表之间存在多条外键路径**时才必须写

## 三、CRUD业务函数

例子展示：

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

在小的项目中，crud会和业务逻辑写一块(好吧这不重要)

select中的参数可以是列、类（也就是表）、聚合函数

《《《注意这里select(表名)，我们平时sql语句里select后跟的是列名，这里语句对应的也不是sql语句中的*，而是枚举了所有列》》》

是否写到类中调用由个人喜好决定，我认为这样会更加清晰方便，当然也可以直接写crud函数，然后在需要的地方直接导入调用

而crud的使用通常需要数据库的参与，所以需要导入from sqlalchemy.ext.asyncio import AsyncSession，该类用来指定会话工具的类

至于crud实际的使用操作，就像使用数据库时写sql语句那样 ，不过变成了在python中通过一个中介工具来写sql语句，比如sqlalchemy

而这里我们用到的语法和数据库中不太一样，可以查看官方文档学习和使用

注：可以配合一些加密函数、自定义抛出异常来使用

##### 进阶内容：

###### selectinload:

​	它的主要作用就是减少sql语句的使用，提升性能，比如在查询帖子时会附带作者，那20个帖子，在一轮查询后就需要1个sql查帖子列表20个sql查作者，但如果在查帖子时就拿到作者uid，然后把它们放到一个列表里统一查询，这样2个sql语句就能完成任务，省去了19次的非查询消耗时间

## 四、路由函数

在完成以上三步后，就可以真正的发挥接口的作用了

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

## 五、依赖注入

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

为什么它可以注入，它注入的究竟是什么，能拿到什么

## 六、自定义异常与注册

自定义异常的**底层本质完全一致**，最终都会把「异常 / 状态码 → 处理函数」的映射注册到 FastAPI 应用的同一张异常处理器表中，只是语法形式和适用场景不同。

##### 使用自定义异常的三个步骤

###### 1.声明自定义异常类

通常继承 Python 内置的 `Exception` 类，因为不继承BaseException的子类，raise语句抛不出来

因为add_exception_handler什么类型都能注册，问题在于能不能抛出

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

就像这样，如果只想写一个处理用户不存在的异常，那就写死

否则写成获取动态信息会更加通用，在抛出异常时写对应的内容即可

而异常处理函数中必须按序写这两个参数request: Request和exc: PostException

第一个参数是当前触发异常的请求对象，第二个参数代表被捕获到的异常实例

至于它们是怎么被使用的，我觉得不需要关心

###### 3.挂载到FastAPI应用

用fastapi实例名.add_exception_handler(异常类型,处理函数)来挂载

然后在你抛出某异常时，就会自动调用你写好的异常处理函数了

##### 其他两种写自定义异常的方式

###### 1.异常函数工厂，写一个嵌套函数（注意这个函数不叫“装饰器”）

```
def create_exception_handler(status_code: int,initial_message: Any) -> Callable[[Request, Exception],JSONResponse]:
    async def exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status_code,
            content={
                "异常类型": "请重写改内容",
                "异常信息": str(exc),
                "初始信息": initial_message
            }, )
    return exception_handler
```

这里返回的是一个“函数”，但已经提前“标注”好了返回的类型是一个可调用对象

Callable[[Request, Exception], JSONResponse]中[Request, Exception]是这个可调用对象的参数

后面的JSONResponse是返回值类型

异常处理函数中，Request和Exception是必须要写的，即使你在返回的信息中不使用它们

Request参数：当前的请求对象 Request，包含请求路径、客户端 IP、请求头等信息

Exception参数：捕获到的异常实例本身，包含异常的具体信息

###### 2.装饰器式注册异常处理

```
@app.exception_handler(500)
async def internal_server_error(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "异常类型": "服务器内部错误",
            "异常信息": str(exc),
        },
    )
```

注意这里的500也可以换成其他状态码，也可以是指定的异常类型，为了解耦与模块清晰化，依然要写到挂载异常的模块中

这个函数的作用如其他自定义异常一样，把所有状态码为500的请求，做函数内的处理逻辑

## 七、中间件

例子：

在中间件中无法追踪异常，因为它不会返回，只会抛出

```
def register_middleware(app: FastAPI):
    """
    注册中间件
    """
    @app.middleware("http")
    async def custom_loggin(request: Request, call_next):
        # 进来时先执行call_next以上的代码
        # ---------- 关键步骤：把请求传给下一个环节 ----------
        # call_next 是 FastAPI 提供的函数，调用它会把请求传给：
        # 下一个中间件 → 最后到你的接口路由
        # 执行完会拿到接口返回的 response
        response = await call_next(request)
        message = f"{request.client.host} {request.method} {request.url.path} {response.status_code}"
        # print(message)
        return  response

    app.add_middleware(  # 设置app可被跨域访问
        CORSMiddleware,  # 中间件类 跨域中间件
        allow_origins=["*"],  # *代表所有，允许所有源访问
        allow_credentials=True,  # 允许携带cookie
        allow_methods=["*"],  # 允许所有请求方法
        allow_headers=["*"],  # 允许所有请求头
    )
```

##### 封装+集中管理

这里写成register_middleware是为了方便内部的函数能访问app这个FastAPI实例，所以如果你不想单独放到一个模块中的话，可以直接在主模块中写@你的实例名.middleware()，但代价是耦合了，主模块中内容可能会有点混乱，而我们封装好的函数直接拿去用的话就一个register_middleware(app)就行了，非常清晰

这种方法我们称之为：注册函数模式

##### 中间件的参数

我们在本次示例中用到的中间件参数是'http'，但其实还有另一个参数

| 参数                  | 处理什么       | 场景                   |
| :-------------------- | :------------- | :--------------------- |
| `"http"`              | HTTP 请求      | 普通的页面、API 接口   |
| `"websocket"`（没用） | WebSocket 连接 | 实时通信（聊天、推送） |
| 其他，但没用          |                |                        |

首先就是不带括号的情况@app.middleware=啥也没注册，但也不报错

有参数的情况，不管你传了什么参数都只处理http请求，这听起来很弱智很让人不解，但这是一个历史遗留的兼容问题

如果想要一个能处理所有请求的中间件，就要手写ASGI中间件喽

##### call_next的作用

在call_next的前后可以分为请求和响应，这也代表了我们可以处理用户发出的信息和服务端返回的响应，也就是说，密码等私密信息在后端人员面前是裸奔的，我觉着吧，还可以在这里写一个简单的违规信息检测，比如骂人的字词可以直接在中间件里改掉

##### 中间件的解剖

我们都知道装饰器是add_middleware的语法糖而已，

但实际middleware内部长这样

```
# FastAPI 的 middleware 装饰器源码
def middleware(self, middleware_type: str):
    def decorator(func):
        self.add_middleware(BaseHTTPMiddleware, dispatch=func)  # ← 内部就是调用它！
        return func
    return decorator
```

add_middleware内部

```
def add_middleware(self, middleware_class: _MiddlewareFactory[P], *args: P.args, **kwargs: P.kwargs) -> None:
    if self.middleware_stack is not None:  # pragma: no cover
        raise RuntimeError("Cannot add middleware after an application has started")
    self.user_middleware.insert(0, Middleware(middleware_class, *args, **kwargs))
```

也就是说，装饰器实际上是把参数传给了内部的middleware_class(这里对应BaseHTTPMiddleware类)的_ _init_ _，也就是把函数(其他中间件应该是配置参数而不是函数)给了这个类

但这也延申出了另一个问题：middleware装饰器是不是只能用在http请求中

我们看这里

```
app.add_middleware(  # 设置app可被跨域访问
        CORSMiddleware...........
```

CORSMiddleware要的是配置，而不是函数

那我们自然也没办法用修饰函数的装饰器来让CORSMiddleware这样的类保存配置，因为装饰器中的dispatch期望接收的是一个func

哦对了，在我们导包的时候可能会有疑问，导入的CORSMiddleware究竟来自于starlette还是fastapi呢：实际上它们两个是一个东西，因为fastapi就是从starlette拿的CORSMiddleware

嗯，大抵就是这样了

##  八、JWT的使用演示

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

## 九、加密演示

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

## 十、Redis缓存

#### Redis介绍

Redis采用的是C/S(服务端、客户端)架构，目的是让数据存储和数据读取解耦

所以Redis不是一定要把服务端和客户端部署到一个设备上，在实际的生产环境中，我们也会分开部署，以防性能不足

但需要注意的是，在本机部署里我们可以写localhost或127.0.0.1，直接在内网访问，在实际生产环境中却有可能需要写另一台服务器的具体IP，当然如果你想在本机上访问自己的公网IP也可以，但可能需要考虑服务器不放行的情况，需要额外配置

配置好后我们在脚本中创建Redis实例

说白了就是写个函数用redis实例的set和get函数去读写，这样就能享受到它的缓存功能了

至少我现在的理解是这样的

案例：

```
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
        print(f"举报去重失败{e}")
        return True
```

通常我们处理一个事务时会先检查它在不在缓存中，不在则存入

但在这个例子中token_blocklist.set(name=key, value="1", nx=True, ex=ttl)用到了nx参数，即检查+写入

第一次举报时检查redis内部，不存在则写入，重复举报时再检查，存在就拒绝写入

那么为什么要这样写，而不是传统的写法（比如项目里的黑名单业务逻辑）？

因为同时发送两个请求时会产生这样的竞态现象

```
请求A：GET  report:5:u1  → 不存在
请求B：GET  report:5:u1  → 不存在   ← B 还没看到 A 写入
请求A：SET  report:5:u1  → 成功，放行
请求B：SET  report:5:u1  → 也成功，也放行   ← 重复举报漏掉了！
```

这样就破坏了原子性

## alembic数据迁移

Alembic 是 **SQLAlchemy 官方配套的数据迁移工具**

##### 初始化

alembic，alembic init 自定义文件夹名称

然后到alembic.ini文件中修改sqlalchemy.url为你的数据库连接地址

Alembic迁移是同步操作，所以alembic.ini文件中你的url地址中的驱动要换成同步驱动

此外alembic可以建表但需要我们手动建库

##### 模型的导入

需要注意的是模型的导入，要让alembic能检测到你的模型

导入的位置是初始化后的文件夹中的env文件

##### 指令

安装pip install alembic

告诉alembic数据库已是最新状态alembic stamp head

生成迁移文件alembic revision --autogenerate -m "你要写的内容"

开始迁移alembic upgrade head

回滚版本alembic downgrade -1

#### alembic实战踩坑案例

原因：用 SCP 把本地整个项目覆盖到了服务器。这个操作本身没问题，但它引发了一连串连锁反应

```
SCP 覆盖前——服务器独有：
  migrations/versions/9efb9ee4c18a_merge_branches.py   ← 服务器上生成的 merge 节点
  alembic_version 表里记录：9efb9ee4c18a

SCP 覆盖后——文件被本地版本替换：
  9efb9ee4c18a 文件没了（本地没有）
  alembic_version 表里还写着 9efb9ee4c18a
  → alembic 找不到这个文件 → 报错
```

##### 为什么删了 merge 节点还不行

##### 你把 `9efb9ee4c18a` 文件删掉后，磁盘上暴露了本地两条并行分支：

```
本地分支 A（旧）：3e9a1887c65d ← 孤立的"初始迁移"
本地分支 B（新）：5e892e7a9720 → b1c2d3e4f5a6 → 0af95caa2ddc → abcfdeda1df4
                              ↑
                    alembic_version 表被手动改回这里
```

`3e9a1887c65d` 是早期操作（手动 stamp / 改 down_revision）遗留的孤儿，和真实链路没有父子关系。但它存在于磁盘上，alembic 就认为有两条链、两个 head，不知道该走哪条。

##### 核心教训

| 踩的坑                      | 为什么不该做                    |
| :-------------------------- | :------------------------------ |
| SCP 整包覆盖 `migrations/`  | 覆盖了别人/服务器生成的迁移文件 |
| 手动 `alembic stamp` 跳版本 | 数据库版本号和磁盘文件脱节      |
| 手动改 `down_revision`      | 父子链断裂，产生孤儿分支        |

------

##### 解决过程

三步走：

**1. 把数据库版本号拉回分叉点**

```sql
UPDATE alembic_version SET version_num = '5e892e7a9720';
```

告诉 alembic："你现在在这里，往后走新链。"

**2. 指定目标版本，绕过孤儿分支**

```bash
alembic upgrade abcfdeda1df4
```

不跑 `head`（会看到两个头不知所措），直接指定要走 `abcfdeda1df4`，alembic 会自动沿 `5e892e7a9720 → b1c2d3e4f5a6 → 0af95caa2ddc → abcfdeda1df4` 逐级执行。

**3. 3 个迁移依次建了 4 张表**

- `b1c2d3e4f5a6`：`goods_classify` + `goods`（商品+分类）
- `0af95caa2ddc`：`goods_comment`（商品评论）
- `abcfdeda1df4`：`images`（图片）

------

以后的正确姿势

```
改模型 → 本地 alembic revision --autogenerate → 传单个迁移文件到服务器 → 服务器 alembic upgrade head
                                                                           ↑
                                                                      永远不要 SCP 覆盖整个 migrations/
                                                                      永远不要手动 stamp / 改 down_revision
```

## git版本控制

为什么要用存代码到云端（当然你也可以自己把整个项目压缩一下放到某个小角落）

1. 记录代码修改（写注释、加功能、改 bug）；
2. 代码写崩了，**一键回滚到上一个正常版本**；
3. 多人协作写项目，不会互相覆盖代码；把代码备份到 GitHub/Gitee 云端，永不丢失

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
   - 你也可以git status看一下将会提交的代码对不对

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

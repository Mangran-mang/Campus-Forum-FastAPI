# AI 选择模块 · 自己动手前的注意事项

> 生成 **2026-10-18** · **修订 v2（同日）**：存储方案由"MySQL 单行表"改为 **JSON 配置文件**（同学拍板，理由见一），
> 加密层随之取消（威胁模型推理见四）。其余设计不变。
>
> **定位**：后台管理页的增量功能 —— 管理员在后台切换审核用的 AI 模型
> （预设下拉 + 手填 key/模型名 + 连通性测试）。与《后台管理开发注意事项.md》同系列：
> 已拍定的决策 + 实测/核实过的事实 + 坑点，**不含实现代码**。
>
> 预设数据是 2026-10-18 从各家**官方文档**核实的，来源在表格里 —— 模型名会过时，
> 这正是"预设可编辑 + 自定义选项"成为需求一部分的原因。

---

## 一、已拍定的决策，别再纠结

| 决策项 | 结论 | 理由 |
|---|---|---|
| **配置存哪** | **JSON 文件**（项目根 `ai_config.json`，路径用 `pathlib` 相对 `__file__` 拼，别用相对 cwd） | 存储需求就一条配置，建表+迁移+crud 是全套流程税；文件直读直写，改动收敛在一个工具函数里。代价与纪律见三 |
| **文件不存在/解析失败时** | fallback 到 `.env` 的 `API_KEY`（= 现在的行为） | 零破坏性上线：不进后台设置过，审核照常走 .env 的千问 key；文件被写坏也只回退默认模型，不全挂 |
| **key 怎么存** | **明文**（v1 方案的 Fernet 加密取消） | 威胁模型推理见四 —— 文件方案下加密防御增量≈0。**脱敏回显**和**PUT 空不改**两条保留，见 4.2/4.3 |
| **GET 怎么回 key** | 只回脱敏串 `sk-ab****wx9f`，**永不回完整 key** | 后台页面被截图/录屏/开 devtools 也不泄露 |
| **PUT 传空 key** | **空 = 保持现有 key 不变** | ⭐ 本功能最容易翻车的一条，见 4.3 |
| **热更新** | 每次审核读文件 + 签名比对缓存，**弃模块级单例** | ⭐ 多 worker 下模块级缓存必炸，见五。隐含**单机部署前提**，升级触发条件见 5.2 |
| **预设放哪** | 后端常量 + `GET /api/admin/ai/presets` 下发 | 改预设不用重新 build 前端 |
| **测试连接** | 必须做 `POST /api/admin/ai/test` | ⭐ 审核失败降级是"按未违规放行"，key 坏了 = 所有举报帖静默放行且无任何报错 —— 管理员必须有个保存前验一验的入口。文件方案下它更重要了（多一个"文件写坏"的静默故障模式） |

**为什么"换模型"只是换三个字符串**：现在审核走 `init_chat_model(model_provider="openai")`
的 OpenAI 兼容模式，而下面四家全提供 OpenAI 兼容端点 → 切换 = 换 base_url / model / api_key，
不需要任何供应商适配代码。这是整个方案能做小的根本原因。

---

## 二、预设数据（2026-10-18 核实自官方文档）

| provider | 显示名 | base_url | 预设模型名 | 备注 |
|---|---|---|---|---|
| `qwen` | 通义千问（阿里云百炼） | `https://dashscope.aliyuncs.com/compatible-mode/v1` | qwen3.8-flash、qwen3.7-flash、qwen3.6-flash、**qwen3.5-flash**、qwen-flash | 现网在用 qwen3.5-flash；qwen3 系列默认开思考模式，见下 |
| `deepseek` | DeepSeek | `https://api.deepseek.com` | **deepseek-v4-flash**、deepseek-v4-pro | ⭐ `deepseek-chat`/`deepseek-reasoner` 已于 **2026-07-24 官方弃用**，网上旧教程还在教旧名 |
| `kimi` | Kimi（月之暗面） | `https://api.moonshot.cn/v1` | kimi-k3、kimi-k2.6 | 国际站是 api.moonshot.ai，别混 |
| `zhipu` | 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` | glm-5.3、glm-5.2 | 注意是 `/api/paas/v4`，不是根路径 |
| `custom` | 自定义 | 手填 | 手填 | 任意 OpenAI 兼容服务（中转站、本地 vLLM 等） |

来源：help.aliyun.com（百炼 OpenAI 兼容文档）/ api-docs.deepseek.com / platform.moonshot.cn/docs / docs.bigmodel.cn。

**思考模式的坑（写 test 接口时就会撞上）**：qwen3.5+ 系列、GLM-5 系列默认开启思考模式，
审核场景要的是快和便宜，思考模式又慢又贵。langchain 侧的关闭方式是给模型传
`model_kwargs={"extra_body": {"enable_thinking": False}}` 这类参数（各家参数名不同，
调不通/变慢时先查这个）。建议：**审核用的模型对象统一显式关思考**，别依赖各家默认值。

---

## 三、文件存储设计（v2：替代原"数据表设计"）

### 3.1 文件格式

```json
{
  "provider": "qwen",
  "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "model_name": "qwen3.5-flash",
  "api_key": "",
  "updated_time": "2026-10-18T20:30:00"
}
```

- **用 JSON，不用 txt**：四个字段手工拼/拆字符串必错；`json.dumps/loads` 一行，
  格式坏了 `loads` 直接抛异常（看得见），txt 拼坏了解析逻辑还"能跑"（看不见）
- `api_key: ""` = 未在后台设置过 → 运行时用 `.env` 的 `API_KEY` 兜底（语义与 v1 种子行空串完全一致）
- `updated_time` 每次保存写入，审计找回一半；`updated_by` 不做（单管理员，没有意义）

### 3.2 ⭐ 原子写（"直接写"的唯一安全写法）

先建立一个认知：`--workers N` 是 uvicorn fork 出 **N 个独立 Python 进程**，每个都完整加载
一遍 main.py、有自己独立的事件循环和内存，互相**不知道对方存在**；Nginx 把每个请求分给
其中任意一个。"只有一个接口"是逻辑层面 —— 物理上这个接口有 N 份运行中的副本，而且
读这个文件的有三个调用方（GET config / 每次审核 / test）。多进程的动机：CPython 的 GIL
让**单进程内**同一时刻只有一个线程在执行 Python 字节码，想吃满多核只能开多进程
（每个进程有独立 GIL）—— 代价就是内存隔离：你踩过的 WS 注册表盲区和"MySQL 连接翻倍"
根源都是它，每个 worker 各持一份连接池与注册表。"同时"从哪来：

| 场景 | 谁撞谁 | 触发条件 |
|---|---|---|
| 写 vs 写 | 两个 PUT 被分到不同 worker | 管理员双击保存 / 前端超时重试，两个请求毫秒级先后到达 |
| **写 vs 读** | PUT 保存 vs 某个用户举报帖触发审核读文件 | **不需要管理员手速**：两个无关用户、两个无关接口，同一毫秒撞上是随机的 |

`open('w')` 的标准语义是**先 truncate（清空）再逐步写入** —— 这个窗口期内文件是空的或
半截的，读方撞上就是解析失败。所以两个 worker 同时处理保存（或写与读交错）时，
"直接 open('w') 写" 会产生**交错/截断的半截文件** —— 不报错，配置坏了，
之后所有审核静默降级。写法必须是：

```
写临时文件（同目录，如 ai_config.json.tmp）
→ os.replace(tmp, ai_config.json)
```

`os.replace` 底层是 rename，**在同一文件系统上是原子系统调用**：任何时刻读方要么看到
完整的旧文件、要么看到完整的新文件，永远看不到半截。这就是"单行表 UPDATE 天然并发安全"
在文件世界里的等价物 —— 没有"天然"，只有自己把这一步做对。

**为什么不用"等/加锁"解决？** 跨进程锁（Linux 的 flock）能互斥，但要付三样东西：
所有读写方都得守纪律加锁（漏一个全失效，和"每个路由都要挂 user_checker"同一种脆弱）、
读也被串行化（保存期间审核全卡住）、持锁进程崩溃还要处理锁残留。而 rename 是零配合
成本的并发安全 —— 思想不是"**阻止**写与读同时发生"，而是"让它们同时发生时，读方看到的
**永远是完整版本**"：写新版本 + 一步原子切换。这与 MySQL 的 MVCC 是同一个思想
（写时生成新版本、提交后原子可见）；我们只有单对象、低频写、且容忍旧值
（这次审核恰好用旧模型，语义上完全合理），所以不需要隔离级别，只需原子可见性。
进行中的读更不用担心：replace 只改目录项指向，**已打开文件的进程持有旧 inode 的引用，
能完整读完旧内容** —— 正在进行的读自动持有旧版本的完整视图。

读侧配一条防御：`json.loads` 抛异常 → `logger.warning` + 返回 None → 上层 fallback `.env`
（原子写之后理论上不会再出现坏文件，但兜底逻辑让最坏情况 = 回退默认模型，而不是全挂）。

### 3.3 ⚠️ 此文件不进仓库、不参与 scp（部署纪律）

- `.gitignore` 加 `ai_config.json` —— 它是**运行时数据**不是代码
- ⭐ 你的部署方式是 scp 手工上传：**本地测试保存过配置后，整个目录一上传就会把线上
  已保存的配置覆盖掉** —— 这是"漏传文件 = 静默故障"的镜像：多传/覆盖一个文件也是静默故障
- 约定：**`ai_config.json` 永远不出现在 scp 清单里**；本地想清配置直接删文件（会自动回退 .env）
- 权限：你 systemd 用 root 跑，不用管；哪天改成专用用户，记得给项目目录写权限

### 3.4 隐含前提：单机部署

文件方案的"共享真值"依赖**所有 worker 在同一台机器、看同一个文件**。哪天要上多机部署，
文件就不共享了，那时候配置才真的需要入库（Redis/MySQL）。现在单机，成立 —— 把这条
边界写在这里，是为了以后你翻到这份文档时知道"文件方案失效的触发条件是什么"。

---

## 四、key 的处理

### 4.1 为什么加密层取消了（v2 变更，威胁模型推理）

Fernet 加密防的场景是：**数据库/备份被拖走，但服务器本身没沦陷** —— 拖库的人拿到的
是密文，解密密钥在 .env 里没跟着泄露。v1 方案（入库+加密）下这个防御是成立的。

文件方案下：`ai_config.json` 和 `.env` 在**同一台机器、同一个目录层级** —— 能读到
json 的人必然能读到 .env，加密防御增量 ≈ 0，纯属把同一个秘密写两遍。所以明文存。

**什么时候必须升级回"加密入库"**：多管理员（后台权限扩散）、商业化运营、等保/合规要求、
多机部署（3.4）。到那天按 v1 思路补：Fernet（依赖 `cryptography==48.0.1` 已在
requirements.lock:17，零新增）+ `AI_SECRET_KEY` 放 .env 必填 + GET 脱敏。
现在砍掉，是把"安全等级与部署形态匹配"的取舍记下来，不是降低标准。

### 4.2 保留的两条纪律（与存储介质无关）

1. **GET 脱敏**：前 4 位 + `****` + 后 4 位；长度不足 10 的全打码。
   来源字段（见六）区分 `"file"` / `"env"` —— 前端显示"当前用 .env 兜底 key"
2. **PUT 空值语义**，见下

### 4.3 ⭐ PUT 的空值语义（本功能第一大坑，v2 依然成立）

场景：GET 返回 `sk-ab****wx9f` → 前端表单里是这串 → 管理员只改了模型名 → 前端把表单
**原样 PUT 回来** → 如果后端不设防，文件里的 key 就被替换成了 `sk-ab****wx9f` 这个
脱敏串本身 → **不报错、不 500，只是从某个时刻起审核全部走降级放行** —— 你排查时日志里
只有"AI 审核返回内容为空/解析失败"，谁能想到是 key 被脱敏串覆盖了。

约定（后端三行 if 就能挡住）：

```
api_key 非空        → 写入新 key
api_key 空/缺省     → 保留文件里的旧 key 不动；文件里也没有(空串)则继续用 .env 的
```

前端配套：key 区域显示为只读脱敏文本 + 「更换」按钮，点开才出现输入框 —— 从交互上
降低"把脱敏串填回去"的概率。**但安全边界必须在后端**，前端只是体验优化。

---

## 五、热更新设计（本功能最核心的一段）

### 5.1 现状与问题

```python
# ai_agent/review.py 现状：import 时创建一次，进程存活期内不变
review_model = init_chat_model(model="qwen3.5-flash", api_key=Config.API_KEY, ...)
```

你服务器 systemd 是 `--workers` 多进程。如果做"改配置 + 重启"没问题，
但做**运行中热切换**时，任何"进程内存里存配置"的方案都会撞上你踩过的那个盲区
（WS 注册表/连接池同源问题）：worker-1 已经读到新配置、worker-2 还在用旧的，
**没有报错、没有 500，就是一部分举报帖用旧模型审** —— 比全坏更难发现。

### 5.2 正解：每次读文件 + 签名比对缓存

```
_get_review_model():
    cfg = 读 ai_config.json（解析失败→None）           # 真值永远在磁盘文件里
    key  = cfg.api_key 非空 ? cfg.api_key : Config.API_KEY
    sig  = sha256(base_url + model_name + key)
    if sig == 模块级缓存的 sig: return 缓存的模型        # 没变 → 零成本复用
    模块级缓存 = (sig, init_chat_model(...))           # 变了 → 重建
```

为什么这个方案对多 worker 天然免疫：**每个 worker 各有各的模块级缓存，但真值每次
都从磁盘上的共享文件读** —— 哪个 worker 下一次审核都会发现签名变了、自己重建，
不需要任何进程间通信。对比 WS 注册表：那是"写进进程内存的数据别的进程看不见"，
这里是"缓存只是加速，真值始终在磁盘"。缓存失效策略从"通知所有人"变成"每个人都
下一次自己发现"，这是分布式系统里最便宜的一致性。

两个实现细节：

- **重建成本**：`init_chat_model` 只是构造一个 HTTP 客户端对象，不发网络请求，
  微秒~毫秒级，审核本身 2-5 秒，完全无感
- **并发重建无害**：两个协程同时发现签名变了、各自重建一次，幂等，不需要锁
- ⚠️ 前提：单机（见 3.4）。多机部署时此方案失效，配置须入库

### 5.3 对外契约不变

`review_post_content(title, content)` 的签名和返回值**一个字都不要动** ——
`routers/posts.py:179` 的调用方（`asyncio.to_thread(review_post_content, ...)`）零改动，
整个改造收敛在 `ai_agent/` 内部。posts.py 里那行 to_thread 的理由（同步调用阻塞事件循环）
在 test 接口里同样适用：**test 路由里的 invoke 也必须 to_thread**。

---

## 六、接口设计（全部挂在 routers/admin.py，全部 `Depends(user_checker)`）

| 方法 | 路径 | 入参 | 出参 data | 要点 |
|---|---|---|---|---|
| GET | `/api/admin/ai/presets` | — | `{presets: [{name, label, base_url, models[]}]}` | 常量直接返回，不读文件 |
| GET | `/api/admin/ai/config` | — | `{provider, base_url, model_name, api_key_masked, api_key_source, updated_time}` | `api_key_source`: `"file"` / `"env"` —— 前端据此显示"当前用 .env 兜底 key"；文件不存在时 provider/base_url/model_name 运行时默认值回显 |
| PUT | `/api/admin/ai/config` | `{provider, base_url, model_name, api_key?}` | 更新后的配置（同 GET 出参） | api_key 空 = 不改（见 4.3）；base_url 必须 http(s) 开头；写文件走原子写（3.2） |
| POST | `/api/admin/ai/test` | `{provider, base_url, model_name, api_key?}` | `{ok, latency_ms, reply / error}` | **用表单当前值（含未保存的修改），不落盘、不动缓存**；api_key 空时按"文件里的 key（没有则 .env）"解析 —— 管理员只换模型不换 key 也要能测 |

test 接口三个硬要求：

1. **必须设超时**（10 秒级）—— 管理员填了个不通的 base_url，没超时的请求会挂到天荒地老，前端像卡死
2. **max_tokens 给小值**（8 足够）+ prompt 一句"回复OK"，控制测试成本
3. **invoke 用 `asyncio.to_thread` 包**（理由见 5.3）

普通 HTTPException 走框架信封（main.py 已注册）→ 前端 `pickErrorMessage` 能直接吃。
业务校验失败（如"尚未设置过 key"）用项目已有的业务异常基类，别手写 JSONResponse。

**schemas 放哪**：新增 `schemas/ai_config.py`（项目 schemas 按域分文件），输出模型
**显式声明所有字段**（漏声明 = 静默丢失，不报错），`response_model` 用 `Envelope[T]` 校验整个信封。

---

## 七、前端要点（贴合你现有代码）

| 改什么 | 在哪 | 怎么做 |
|---|---|---|
| API 封装 | `frontend/src/api/index.js` | `adminApi` 对象里加 4 个方法，全部走现成的 `adminRequest()`（自动带 admin_token、401 自动跳后台登录页） |
| 导航 | `frontend/src/views/admin/AdminLayout.vue:7-9` | nav 里加一行 `<router-link to="/admin/ai" class="admin-nav-item">AI 设置</router-link>` |
| 路由 | `frontend/src/router/index.js` | 照 AdminGoodsView 的样子：顶部动态 import + `/admin` children 里加 `{ path: 'ai', ... }`（在 AdminLayout 的 children 里，天然有守卫） |
| 页面 | 新增 `frontend/src/views/admin/AdminAIView.vue` | 表单页，见下 |

AdminAIView 的交互细节：

- **预设下拉** → 选中即自动填 base_url + 模型名（模型名给 datalist/下拉，预设 models 里的都可选，也允许手输）→ **所有字段仍可编辑**；选"自定义"则三项全手填
- **key 区域**：只读显示 `api_key_masked` + 来源徽标（`file`/`env`）；「更换」按钮展开密码框，留空 = 不改 —— 和后端 4.3 的约定严丝合缝
- **测试连接**按钮：用**当前表单值**调 test（保存前就能测），结果区显示 ok/失败原因/延迟
- **保存**：PUT → 成功后重新 GET 刷新表单；先确认 `res.code === 200` 再改本地状态（项目铁律）
- 错误提示统一 `pickErrorMessage(res, fallback)`，无 `catch {}` 空块，无 HTML minlength

---

## 八、建议动手顺序（每步都能单独验证）

| 步骤 | 做什么 | 验证 |
|---|---|---|
| 1 | JSON 读写工具（读：文件→解析失败/不存在→None；写：tmp + os.replace） | `python -c` 里写→读往返；删文件再读应得 None；**两个进程同时写**（手开两个终端各跑一次写）之后文件仍是合法 JSON |
| 2 | schemas + GET/PUT 两个接口 | 起 uvicorn 手打：PUT 不带 api_key → 文件里旧 key 原样（`type ai_config.json` 看前后）；GET 回的是脱敏串；**PUT 之后立刻 GET 验证回显** |
| 3 | review.py 改造（读文件+签名缓存） | 举报一帖看日志走通；改 json 里的 model_name 再举报，日志里应出现新模型（或临时打一行 log）；**重启两次分别举报，验证两个 worker 都用新配置** |
| 4 | test 接口 | 填正确 key → ok+延迟；故意填错 key → 明确失败；填不通的 base_url → 10 秒内返回错误而不是挂死 |
| 5 | 前端三件套 | 整链路：选预设→测→存→重进页面回显正确；只改模型名保存 → key 没被脱敏串覆盖（回后台看 masked 串没变就说明没坏） |

部署清单（对应你的 scp 流程）：**后端改动 = `ai_agent/review.py` + `routers/admin.py` +
`schemas/ai_config.py`（新增）+ `.gitignore`；无需迁移、无需重启数据库，`systemctl restart school-forum` 即可**；
`ai_config.json` 不上传（3.3）。前端 build 后传 dist 产物（老规矩：按本次 build 输出清旧 chunk）。

---

## 九、自查清单（提交前逐条过）

- [ ] 四个路由全部挂了 `Depends(user_checker)`，扫一眼能看出权限边界
- [ ] 没有手写字典 / JSONResponse，全走 `success_response` + `Envelope[T]`
- [ ] 输出模型显式声明了全部字段；`response_model` 校验整个信封
- [ ] 写文件走了 tmp + os.replace（不是直接 open('w')）
- [ ] 读文件有兜底：不存在/解析失败 → warning + fallback .env，不 500
- [ ] PUT 空 api_key 不覆盖旧值（打开 ai_config.json 对比前后）
- [ ] GET 永不返回完整 key（自己 curl 看一遍响应体）
- [ ] review.py 对外签名没变，posts.py 一行没动
- [ ] test 的 invoke 包了 to_thread、设了 timeout、max_tokens 很小
- [ ] `.gitignore` 加了 ai_config.json；本地测试配置没被 scp 上线
- [ ] 前端：pickErrorMessage / code===200 再改状态 / 无空 catch / 无 minlength
- [ ] 表单里 key 输入框是 password 型 + 留空不改语义，与后端约定一致

---

## 十、一句话总纲

> 这个模块的骨架是「**单文件配置 + 原子写 + 签名比对热更新 + 脱敏回写约定**」。
> 文件方案砍掉了三层样板代码，代价是并发安全和部署纪律要自己守住 ——
> 四个坑（脱敏串回存、多 worker 热更新、审核失败静默放行、scp 覆盖运行时文件）
> 每一个都是真实事故的形状。面试里讲"为什么从文件升级到入库的条件是什么"，
> 比背八股有说服力。

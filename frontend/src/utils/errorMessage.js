// 后端错误响应 → 用户可读文案
//
// ## 为什么需要这个模块
// 后端响应统一为 {code, message, data}（见 tools/exceptions.py）：
//   - 业务异常（400/401/404/409…）：message 本来就是给用户看的中文（"密码错误"）
//   - 422 参数校验失败：message 是笼统的固定文案"请求参数校验失败"，
//     真正有用的**字段级明细在 data 里**：[{field: "password", message: "String should have at least 8 characters"}]
// 之前各页面写的是 `res.detail || res.message || 'xx失败'`：
//   ① res.detail 在新信封下**根本不存在**（后端早就把 detail 改名成 message 了），
//      这个兜底是死代码，留着会让人误以为还有一层老格式兼容；
//   ② 即便读到了 data 明细，直接展示会是英文原文（Pydantic 的 msg 是英文），
//      用户看到 "String should have at least 8 characters" 毫无帮助。
// 所以这里做两件事：**优先取字段明细**，并把**英文校验消息翻成中文**。

// ---------- 字段名 → 中文标签 ----------
// 用于把 `password: String should have...` 变成 `密码：至少 8 位`
const FIELD_LABELS = {
  email: '邮箱',
  password: '密码',
  old_password: '当前密码',
  new_password: '新密码',
  username: '用户名',
  nickname: '昵称',
  gender: '性别',
  title: '标题',
  content: '内容',
  summary: '摘要',
  category_id: '板块',
  name: '名称',
  classify: '分类',
  status: '状态',
  price: '价格',
  post_id: '帖子',
  comment_id: '评论',
  content_type: '内容类型',
}

// ---------- Pydantic(v2) 英文校验消息 → 中文 ----------
// 匹配不到的返回空串，交给调用方用「字段标签 + 原消息」兜底，绝不静默吞掉信息。
//
// ⚠️ 维护提示：这些文案来自 pydantic 的英文默认消息（不是我们的代码），
// 大版本升级时可能变。所以**匹配一律用宽松的 includes/正则**，不要用全等，
// 且失败路径必须保留原文——宁可显示英文，也不要显示"未知错误"。
function translatePydanticMessage(raw) {
  const msg = String(raw || '').trim()
  if (!msg) return ''

  // String should have at least 8 characters
  let m = msg.match(/should have at least (\d+) character/i)
  if (m) return `至少 ${m[1]} 位`

  // String should have at most 30 characters
  m = msg.match(/should have at most (\d+) character/i)
  if (m) return `最多 ${m[1]} 个字符`

  // Field required
  if (/field required/i.test(msg)) return '不能为空'

  // value is not a valid email address: <原因>
  // 冒号后面那截才是真正有用的信息（是少了 @ 还是域名不对），
  // 能识别就说得更准，用户改一次就能过。
  if (/valid email address/i.test(msg)) {
    if (/must have an @-sign/i.test(msg)) return '邮箱缺少 @ 符号'
    if (/top-level domain|should have a period|after the @-sign is not valid/i.test(msg)) {
      return '邮箱域名格式不正确（@ 后面要是完整的域名，如 qq.com）'
    }
    return '邮箱格式不正确'
  }

  // Input should be a valid number / unable to parse string as a number
  if (/valid number|parse string as a number/i.test(msg)) return '必须是数字'

  // Input should be a valid integer
  if (/valid integer/i.test(msg)) return '必须是整数'

  // Input should be a valid string —— str 类型的字段收到了数字/null
  // （例如 UserUpdateModel.nickname 注解是 str，前端传了 null）
  if (/valid string/i.test(msg)) return '必须是文本，不能为空'

  // Input should be greater than or equal to 0
  m = msg.match(/greater than or equal to (-?[\d.]+)/i)
  if (m) return `不能小于 ${m[1]}`

  // Input should be less than or equal to 100
  m = msg.match(/less than or equal to (-?[\d.]+)/i)
  if (m) return `不能大于 ${m[1]}`

  // String should match pattern '...'（比如用户名只允许字母数字）
  if (/should match pattern/i.test(msg)) return '格式不正确'

  // 兜底：把 pydantic 消息里 <class 'xxx'> 这类实现细节去掉，只留人话
  return msg.replace(/<[^>]+>/g, '').trim()
}

/**
 * 从统一信封响应里提取最能说明问题的错误文案。
 *
 * @param {object} res       后端返回的 {code, message, data}
 * @param {string} fallback  彻底取不到时用的兜底文案（各页面自定，如"注册失败"）
 * @returns {string}
 *
 * ## 优先级说明
 * 字段明细（data）> message > fallback。
 * 因为 422 的 message 是笼统的固定文案，而 data 里那条才真正告诉用户
 * "哪个字段、错在哪"——这正是"提示要详细"的关键。
 * 多条明细用「；」连起来一次说清，避免用户改一个字段提交一次、再被打回一次。
 */
export function pickErrorMessage(res, fallback = '操作失败') {
  if (!res) return fallback

  // 1) 优先字段级明细：[{field, message}]
  if (Array.isArray(res.data) && res.data.length > 0) {
    const parts = res.data
      .map((item) => {
        if (!item) return ''
        const label = FIELD_LABELS[item.field] || item.field || ''
        const text = translatePydanticMessage(item.message)
        if (!label) return text
        if (!text) return `${label}填写有误`
        // 翻译结果本身已经带了这个词就别再拼一遍（"邮箱格式不正确"
        // 不能变成"邮箱：邮箱格式不正确"）；是"至少/最多/不能/必须是"这类
        // 补语则直接连写（"密码" + "至少 8 位" → "密码至少 8 位"）。
        if (text.startsWith(label)) return text
        return /^(至少|最多|不能|必须是)/.test(text) ? `${label}${text}` : `${label}：${text}`
      })
      .filter(Boolean)
    if (parts.length) return parts.join('；')
  }

  // 2) 兜底 message（业务异常走这条，本来就是中文）
  //    res.detail 保留成最末一档，只为兼容可能存在的旧格式响应
  return res.message || res.detail || fallback
}

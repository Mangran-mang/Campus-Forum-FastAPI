// 后端 API 封装 - 所有接口集中管理
const BASE = '/api'

// 获取存储的 token
function getToken() {
  return localStorage.getItem('access_token')
}

function getRefreshToken() {
  return localStorage.getItem('refresh_token')
}

// 存储 token
function saveTokens(access, refresh) {
  localStorage.setItem('access_token', access)
  if (refresh) localStorage.setItem('refresh_token', refresh)
}

// 清除登录状态
export function clearAuth() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user_info')
}

// 核心请求方法（自动带 token、自动刷新）
async function request(path, options = {}) {
  const token = getToken()
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  if (token) headers['Authorization'] = `Bearer ${token}`

  let res = await fetch(`${BASE}${path}`, { ...options, headers })

  // 如果 403 且可能是 token 过期，尝试刷新
  if (res.status === 403 && getRefreshToken()) {
    const refreshOk = await tryRefresh()
    if (refreshOk) {
      headers['Authorization'] = `Bearer ${getToken()}`
      res = await fetch(`${BASE}${path}`, { ...options, headers })
    } else {
      clearAuth()
      window.location.hash = '#/login'
      throw new Error('登录已过期，请重新登录')
    }
  }

  return res.json()
}

// 尝试刷新 token（单飞模式：同一时刻只允许一个刷新请求在飞）
// ## 为什么单飞：access 过期瞬间页面常有多个并发请求同时 403，
// 若各自发起刷新，会拿同一把旧 refresh 互踩——轮换后第一个成功、
// 其余全部 401 被登出。共享同一个 promise，让所有请求等同一个刷新结果。
let refreshPromise = null
async function tryRefresh() {
  if (refreshPromise) return refreshPromise
  refreshPromise = doRefresh().finally(() => {
    refreshPromise = null
  })
  return refreshPromise
}

async function doRefresh() {
  try {
    const refreshToken = getRefreshToken()
    const res = await fetch(`${BASE}/user/refresh_token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${refreshToken}`,
      },
    })
    const data = await res.json()
    // 后端响应已统一信封，token 在 data 里；刷新失败时是 {code:400,...}，走 false
    if (data.code === 200 && data.data?.access_token) {
      // 后端已做 refresh 轮换：必须把新 refresh 也存回去替换旧的，
      // 否则下次刷新仍拿已被轮换作废的旧 token，会 401 死循环
      saveTokens(data.data.access_token, data.data.refresh_token)
      return true
    }
    return false
  } catch {
    return false
  }
}

// ============== 用户相关 ==============
export const userApi = {
  register: (data) => request('/user/add', { method: 'POST', body: JSON.stringify(data) }),
  login: async (data) => {
    const res = await fetch(`${BASE}/user/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    const result = await res.json()
    // 统一信封后 token/user 都在 data 里（原来平铺在顶层）
    if (result.code === 200 && result.data) {
      saveTokens(result.data.access_token, result.data.refresh_token)
      localStorage.setItem('user_info', JSON.stringify(result.data.user))
    }
    return result
  },
  getCurrentUser: () => request('/user/current_user'),
  updateUser: (data) => request('/user/update', { method: 'POST', body: JSON.stringify(data) }),
  // 改密码走独立接口（后端会校验原密码，并在成功后作废该用户所有会话）
  changePassword: (data) => request('/user/change_password', { method: 'POST', body: JSON.stringify(data) }),
  deleteUser: (email) => request(`/user/delete/${email}`, { method: 'DELETE' }),
  logout: () => request('/user/logout', { method: 'POST' }),
}

// ============== 帖子相关 ==============
export const postApi = {
  getList: (params = {}) => {
    const qs = new URLSearchParams()
    if (params.page) qs.set('page', params.page)
    if (params.page_size) qs.set('page_size', params.page_size)
    if (params.author_uid) qs.set('author_uid', params.author_uid)
    if (params.category_id) qs.set('category_id', params.category_id)
    // keyword 交给 URLSearchParams 编码，中文/%、& 等都会被正确处理，
    // 不需要（也不应该）在前端预先转义 —— LIKE 元字符的转义是后端的事
    if (params.keyword) qs.set('keyword', params.keyword)
    return request(`/posts/get_posts?${qs}`)
  },
  getDetail: (id) => request(`/posts/get_post/${id}`),
  create: (data) => request('/posts/add_post', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/posts/update_post?post_id=${id}`, { method: 'POST', body: JSON.stringify(data) }),
  delete: (id) => request(`/posts/delete_post/${id}`, { method: 'DELETE' }),
  report: (id) => request(`/posts/report/${id}`, { method: 'POST' }),
}

// ============== 评论相关 ==============
export const commentApi = {
  getList: (postId, params = {}) => {
    const qs = new URLSearchParams({ post_id: postId, ...params })
    return request(`/comments/getcomments?${qs}`)
  },
  add: (postId, data) =>
    request(`/comments/addcomment?post_id=${postId}`, { method: 'POST', body: JSON.stringify(data) }),
  delete: (commentId) => request(`/comments/deletecomment?comment_id=${commentId}`, { method: 'DELETE' }),
}

// ============== 板块相关 ==============
export const categoryApi = {
  getAll: () => request('/categories/'),
  getById: (id) => request(`/categories/${id}`),
  create: (data) => request('/categories/add', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/categories/update/${id}`, { method: 'POST', body: JSON.stringify(data) }),
  delete: (id) => request(`/categories/delete/${id}`, { method: 'DELETE' }),
}

// ============== 点赞相关 ==============
export const likeApi = {
  toggle: (postId) => request('/likes/toggle', { method: 'POST', body: JSON.stringify({ post_id: postId }) }),
  count: (postId) => request(`/likes/count/${postId}`),
  check: (postId) => request(`/likes/check/${postId}`),
}

// ============== 收藏相关 ==============
export const bookmarkApi = {
  toggle: (postId) => request('/bookmarks/toggle', { method: 'POST', body: JSON.stringify({ post_id: postId }) }),
  getMy: () => request('/bookmarks/my'),
}

// ============== 商品相关 ==============
export const goodsApi = {
  getList: () => request('/goods/get_goods'),
  getDetail: (gid) => request(`/goods/get_goods/${gid}`),
  create: (data) => request('/goods/add_goods', { method: 'POST', body: JSON.stringify(data) }),
  update: (gid, data) => request(`/goods/${gid}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (gid) => request(`/goods/${gid}`, { method: 'DELETE' }),
}

// ============== 商品分类相关 ==============
export const classifyApi = {
  getAll: () => request('/classify/get_classify'),
  getById: (id) => request(`/classify/get_classify/${id}`),
}

// ============== 商品评论相关 ==============
export const goodsCommentApi = {
  getList: (goodsGid, params = {}) => request(`/goods/${goodsGid}/comments?page=${params.page || 1}&page_size=${params.page_size || 10}`),
  add: (goodsGid, data) => request(`/goods/${goodsGid}/comments`, { method: 'POST', body: JSON.stringify(data) }),
  delete: (commentId) => request(`/goods/comments/${commentId}`, { method: 'DELETE' }),
}

// ============== 图片相关 ==============
async function uploadFile(path, file) {
  const token = getToken()
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData,
  })
  if (res.status === 403 && getRefreshToken()) {
    const refreshOk = await tryRefresh()
    if (refreshOk) {
      const res2 = await fetch(`${BASE}${path}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` },
        body: formData,
      })
      return res2.json()
    } else {
      clearAuth()
      window.location.hash = '#/login'
      throw new Error('登录已过期')
    }
  }
  return res.json()
}

export const imageApi = {
  upload: (targetType, targetId, file) => uploadFile(`/upload/${targetType}/${targetId}`, file),
  getList: (targetType, targetId) => request(`/images/${targetType}/${targetId}`),
  delete: (imageId) => request(`/images/${imageId}`, { method: 'DELETE' }),
}

// ============== 后台管理相关 ==============
export const adminApi = {
  // ## 后台独立登录入口，但与前台共用同一套 token 存储
  // 后端签发与前台同构的双 token（同一账号体系），所以登录成功后
  // 直接写同一组 localStorage 键 —— 代价：后台登录会顶掉该管理员
  // 前台的 refresh 会话（前台下次刷新 401 需重登），这是单行模型的既有行为。
  // 失败语义：非管理员/密码错/邮箱不存在一律 401「邮箱或密码错误」，前端无需也无法区分
  login: async (data) => {
    const res = await fetch(`${BASE}/admin/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    const result = await res.json()
    if (result.code === 200 && result.data) {
      saveTokens(result.data.access_token, result.data.refresh_token)
      localStorage.setItem('user_info', JSON.stringify(result.data.user))
    }
    return result
  },
  // 三个列表接口的 data 形状统一为 {xxx: [...], total, page, page_size}，
  // page_size 是后端 clamp 后的生效值（不是请求原值），分页器必须用它算页数
  getUsers: (params = {}) => {
    const qs = new URLSearchParams({ page: params.page || 1, page_size: params.page_size || 10 })
    return request(`/admin/users?${qs}`)
  },
  getPosts: (params = {}) => {
    const qs = new URLSearchParams({ page: params.page || 1, page_size: params.page_size || 10 })
    return request(`/admin/posts?${qs}`)
  },
  getGoods: (params = {}) => {
    const qs = new URLSearchParams({ page: params.page || 1, page_size: params.page_size || 10 })
    return request(`/admin/goods?${qs}`)
  },
  updateUser: (data) => request('/admin/update_user', { method: 'POST', body: JSON.stringify(data) }),
  // 删除走 query 传邮箱（后台手动输入场景，不用路径参数）
  // ⚠️ 后端 delete_user 目前没有「不能删自己」的拦截 —— 前端先挡一层（见 AdminUsersView）
  deleteUser: (email) => request(`/admin/delete?email=${encodeURIComponent(email)}`, { method: 'DELETE' }),
}

// ============== 通知相关 ==============
export const notificationApi = {
  getList: (params = {}) => {
    const qs = new URLSearchParams(params)
    return request(`/notifications/?${qs}`)
  },
  getUnreadCount: () => request('/notifications/unread_count'),
  markRead: (id) => request(`/notifications/read/${id}`, { method: 'POST' }),
  markAllRead: () => request('/notifications/read_all', { method: 'POST' }),
}

// ============== 私信相关 ==============
export const messageApi = {
  // 获取或创建与某用户的会话
  getOrCreateConversation: (otherUid) =>
    request(`/messages/conversation?other_uid=${otherUid}`, { method: 'POST' }),
  // 我的会话列表
  getConversations: (params = {}) => {
    const qs = new URLSearchParams(params)
    return request(`/messages/conversations?${qs}`)
  },
  // 会话历史消息
  getMessages: (convId, params = {}) => {
    const qs = new URLSearchParams({ page: params.page || 1, page_size: params.page_size || 50 })
    return request(`/messages/conversations/${convId}/messages?${qs}`)
  },
  // 发送消息
  sendMessage: (convId, content) =>
    request(`/messages/conversations/${convId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    }),
  // 搜索用户
  searchUsers: (keyword) => request(`/messages/users/search?keyword=${encodeURIComponent(keyword)}`),
}

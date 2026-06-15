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

// 尝试刷新 token
async function tryRefresh() {
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
    if (data.access_token) {
      saveTokens(data.access_token)
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
    if (result.access_token) {
      saveTokens(result.access_token, result.refresh_token)
      localStorage.setItem('user_info', JSON.stringify(result.user))
    }
    return result
  },
  getCurrentUser: () => request('/user/current_user'),
  updateUser: (data) => request('/user/update', { method: 'POST', body: JSON.stringify(data) }),
  deleteUser: (email) => request(`/user/delete/${email}`, { method: 'DELETE' }),
  logout: () => request('/user/logout'),
}

// ============== 帖子相关 ==============
export const postApi = {
  getList: (params = {}) => {
    const qs = new URLSearchParams()
    if (params.page) qs.set('page', params.page)
    if (params.page_size) qs.set('page_size', params.page_size)
    if (params.author_uid) qs.set('author_uid', params.author_uid)
    if (params.category_id) qs.set('category_id', params.category_id)
    return request(`/posts/get_posts?${qs}`)
  },
  getDetail: (id) => request(`/posts/get_post/${id}`),
  create: (data) => request('/posts/add_post', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/posts/update_post?post_id=${id}`, { method: 'POST', body: JSON.stringify(data) }),
  delete: (id) => request(`/posts/delete_post/${id}`, { method: 'DELETE' }),
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

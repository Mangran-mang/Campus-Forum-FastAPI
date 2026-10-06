import { createRouter, createWebHashHistory } from 'vue-router'

import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import PostListView from '../views/PostListView.vue'
import PostDetailView from '../views/PostDetailView.vue'
import CreatePostView from '../views/CreatePostView.vue'
import ProfileView from '../views/ProfileView.vue'
import NotificationsView from '../views/NotificationsView.vue'
import AnnouncementView from '../views/AnnouncementView.vue'
import GoodsListView from '../views/GoodsListView.vue'
import GoodsDetailView from '../views/GoodsDetailView.vue'
import CreateGoodsView from '../views/CreateGoodsView.vue'
import EditGoodsView from '../views/EditGoodsView.vue'
import MessagesView from '../views/MessagesView.vue'
import ChatView from '../views/ChatView.vue'

// ---------- 后台管理 ----------
import AdminLoginView from '../views/admin/AdminLoginView.vue'
import AdminLayout from '../views/admin/AdminLayout.vue'
import AdminUsersView from '../views/admin/AdminUsersView.vue'
import AdminPostsView from '../views/admin/AdminPostsView.vue'
import AdminGoodsView from '../views/admin/AdminGoodsView.vue'

const routes = [
  { path: '/', redirect: '/posts' },
  { path: '/login', name: 'Login', component: LoginView },
  { path: '/register', name: 'Register', component: RegisterView },
  { path: '/posts', name: 'PostList', component: PostListView },
  { path: '/posts/create', name: 'CreatePost', component: CreatePostView },
  { path: '/posts/:id', name: 'PostDetail', component: PostDetailView },
  { path: '/profile', name: 'Profile', component: ProfileView },
  { path: '/notifications', name: 'Notifications', component: NotificationsView },
  { path: '/announcements', name: 'Announcements', component: AnnouncementView },
  { path: '/goods', name: 'GoodsList', component: GoodsListView },
  { path: '/goods/create', name: 'CreateGoods', component: CreateGoodsView },
  { path: '/goods/:gid', name: 'GoodsDetail', component: GoodsDetailView },
  { path: '/goods/:gid/edit', name: 'EditGoods', component: EditGoodsView },
  { path: '/messages', name: 'Messages', component: MessagesView },
  { path: '/messages/:id', name: 'Chat', component: ChatView },

  // ---------- 后台管理 ----------
  // meta.admin 让 App.vue 跳过前台的星空/导航/页脚（后台有自己的布局）
  { path: '/admin/login', name: 'AdminLogin', component: AdminLoginView, meta: { admin: true } },
  {
    path: '/admin',
    component: AdminLayout,
    meta: { admin: true },
    children: [
      { path: '', redirect: '/admin/users' },
      { path: 'users', name: 'AdminUsers', component: AdminUsersView },
      { path: 'posts', name: 'AdminPosts', component: AdminPostsView },
      { path: 'goods', name: 'AdminGoods', component: AdminGoodsView },
    ],
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

// ## 前端路由守卫只是「体验层」，不是安全边界
// 它读的是 localStorage —— 任何人 F12 就能伪造 user_info，所以真正的权限
// 边界在后端每个 /api/admin/* 接口上的 UserChecker(True)（实时查库）。
// 这里拦截的目的只有一个：让非管理员别在后台页面里白点一圈然后处处 403，
// 而是在门口就被引导到后台登录页。
router.beforeEach((to) => {
  if (!to.path.startsWith('/admin')) return true
  if (to.name === 'AdminLogin') return true

  let info = null
  try {
    info = JSON.parse(localStorage.getItem('user_info') || 'null')
  } catch {
    info = null
  }
  const token = localStorage.getItem('access_token')
  if (!token || !info || info.is_superuser !== true) {
    return { name: 'AdminLogin' }
  }
  return true
})

export default router

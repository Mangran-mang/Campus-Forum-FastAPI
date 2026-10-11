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

// ---------- 后台管理（懒加载）----------
// ## 为什么这里用动态 import 而不是顶部静态 import
// 后台是低频入口，且数据看板依赖 echarts（按需引入后仍有 ~190KB gzip）。
// 静态 import 会把它打进主包 —— 前台访客根本不看后台，却要为此多下载 3 倍体积。
// 动态 import 让 Vite 把 /admin 相关代码单独拆 chunk，只在真正访问时才加载。
const AdminLoginView = () => import('../views/admin/AdminLoginView.vue')
const AdminLayout = () => import('../views/admin/AdminLayout.vue')
const AdminUsersView = () => import('../views/admin/AdminUsersView.vue')
const AdminPostsView = () => import('../views/admin/AdminPostsView.vue')
const AdminGoodsView = () => import('../views/admin/AdminGoodsView.vue')

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
// 它读的是 localStorage —— 任何人 F12 就能伪造，所以真正的权限
// 边界在后端每个 /api/admin/* 接口上的 UserChecker(True)（实时查库）。
// 这里拦截的目的只有一个：让没登录后台的人别在后台页面里白点一圈然后处处 401/403，
// 而是在门口就被引导到后台登录页。
// ## 后台是独立短会话（admin_token），与前台登录态无关：
// 前台登录着也必须单独登录后台（step-up），后台登录也不影响前台。
router.beforeEach((to) => {
  if (!to.path.startsWith('/admin')) return true
  if (to.name === 'AdminLogin') return true

  let info = null
  try {
    info = JSON.parse(localStorage.getItem('admin_user_info') || 'null')
  } catch {
    info = null
  }
  const token = localStorage.getItem('admin_token')
  if (!token || !info || info.is_superuser !== true) {
    return { name: 'AdminLogin' }
  }
  return true
})

export default router

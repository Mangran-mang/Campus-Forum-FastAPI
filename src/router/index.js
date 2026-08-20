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
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router

import { createRouter, createWebHashHistory } from 'vue-router'

import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import PostListView from '../views/PostListView.vue'
import PostDetailView from '../views/PostDetailView.vue'
import CreatePostView from '../views/CreatePostView.vue'
import ProfileView from '../views/ProfileView.vue'
import NotificationsView from '../views/NotificationsView.vue'

const routes = [
  { path: '/', redirect: '/posts' },
  { path: '/login', name: 'Login', component: LoginView },
  { path: '/register', name: 'Register', component: RegisterView },
  { path: '/posts', name: 'PostList', component: PostListView },
  { path: '/posts/create', name: 'CreatePost', component: CreatePostView },
  { path: '/posts/:id', name: 'PostDetail', component: PostDetailView },
  { path: '/profile', name: 'Profile', component: ProfileView },
  { path: '/notifications', name: 'Notifications', component: NotificationsView },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router

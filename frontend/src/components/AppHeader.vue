<template>
  <header class="header">
    <div class="container flex-between">
      <router-link to="/posts" class="logo">郑财论坛</router-link>
      <nav class="nav" v-if="isLoggedIn">
        <router-link to="/posts" class="nav-link">首页</router-link>
        <router-link to="/posts/create" class="nav-link">发帖</router-link>
        <router-link to="/notifications" class="nav-link">
          通知
          <span v-if="unreadCount > 0" class="badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
        </router-link>
        <router-link to="/profile" class="nav-link">我的</router-link>
        <button class="btn-outline btn-sm" @click="handleLogout">退出</button>
      </nav>
      <nav class="nav" v-else>
        <router-link to="/login" class="nav-link">登录</router-link>
        <router-link to="/register" class="btn-primary btn-sm">注册</router-link>
      </nav>
    </div>
  </header>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { userApi, notificationApi, clearAuth } from '../api/index.js'

const router = useRouter()
const isLoggedIn = ref(!!localStorage.getItem('access_token'))
const unreadCount = ref(0)
let timer = null

async function fetchUnread() {
  if (!isLoggedIn.value) return
  try {
    const res = await notificationApi.getUnreadCount()
    if (res.code === 200) unreadCount.value = res.data.unread_count
  } catch {}
}

function checkLogin() {
  isLoggedIn.value = !!localStorage.getItem('access_token')
}

async function handleLogout() {
  try { await userApi.logout() } catch {}
  clearAuth()
  isLoggedIn.value = false
  unreadCount.value = 0
  router.push('/login')
}

onMounted(() => {
  checkLogin()
  if (isLoggedIn.value) {
    fetchUnread()
    timer = setInterval(fetchUnread, 30000)
  }
  window.addEventListener('auth-change', checkLogin)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  window.removeEventListener('auth-change', checkLogin)
})
</script>

<style scoped>
.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 56px;
  background: #fff;
  border-bottom: 1px solid var(--border);
  z-index: 100;
  display: flex;
  align-items: center;
}
.logo {
  font-size: 18px;
  font-weight: 600;
  color: var(--primary);
  text-decoration: none;
}
.nav {
  display: flex;
  align-items: center;
  gap: 16px;
}
.nav-link {
  color: var(--text-secondary);
  font-size: 14px;
  text-decoration: none;
  position: relative;
}
.nav-link:hover {
  color: var(--primary);
  text-decoration: none;
}
.badge {
  background: var(--danger);
  color: #fff;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 10px;
  margin-left: 4px;
  vertical-align: top;
}
</style>

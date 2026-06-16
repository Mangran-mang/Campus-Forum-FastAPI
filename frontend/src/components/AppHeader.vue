<template>
  <header class="header">
    <div class="container header-inner">
      <router-link to="/posts" class="logo" @click="menuOpen = false">郑财论坛</router-link>

      <!-- 桌面端导航 -->
      <nav class="nav nav-desktop" v-if="isLoggedIn">
        <router-link to="/posts" class="nav-link">首页</router-link>
        <router-link to="/posts/create" class="nav-link">发帖</router-link>
        <router-link to="/notifications" class="nav-link">
          通知
          <span v-if="unreadCount > 0" class="badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
        </router-link>
        <router-link to="/profile" class="nav-link">我的</router-link>
        <button class="btn-outline btn-sm" @click="handleLogout">退出</button>
      </nav>
      <nav class="nav nav-desktop" v-else>
        <router-link to="/login" class="nav-link">登录</router-link>
        <router-link to="/register" class="btn-primary btn-sm">注册</router-link>
      </nav>

      <!-- 移动端汉堡按钮 -->
      <button class="hamburger" @click="menuOpen = !menuOpen" aria-label="菜单">
        <span :class="{ open: menuOpen }"></span>
        <span :class="{ open: menuOpen }"></span>
        <span :class="{ open: menuOpen }"></span>
      </button>
    </div>

    <!-- 移动端下拉菜单 -->
    <Transition name="slide">
      <div class="mobile-menu" v-if="menuOpen">
        <template v-if="isLoggedIn">
          <router-link to="/posts" class="mobile-link" @click="menuOpen = false">首页</router-link>
          <router-link to="/posts/create" class="mobile-link" @click="menuOpen = false">发帖</router-link>
          <router-link to="/notifications" class="mobile-link" @click="menuOpen = false">
            通知
            <span v-if="unreadCount > 0" class="badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
          </router-link>
          <router-link to="/profile" class="mobile-link" @click="menuOpen = false">我的</router-link>
          <button class="mobile-link logout-btn" @click="handleLogout(); menuOpen = false">退出登录</button>
        </template>
        <template v-else>
          <router-link to="/login" class="mobile-link" @click="menuOpen = false">登录</router-link>
          <router-link to="/register" class="mobile-link" @click="menuOpen = false">注册</router-link>
        </template>
      </div>
    </Transition>
  </header>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { userApi, notificationApi, clearAuth } from '../api/index.js'

const router = useRouter()
const isLoggedIn = ref(!!localStorage.getItem('access_token'))
const unreadCount = ref(0)
const menuOpen = ref(false)
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
.header-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}
.logo {
  font-size: 18px;
  font-weight: 600;
  color: var(--primary);
  text-decoration: none;
  flex-shrink: 0;
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

/* 汉堡按钮 - 默认隐藏 */
.hamburger {
  display: none;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  width: 36px;
  height: 36px;
  padding: 6px;
  background: none;
  border: none;
  cursor: pointer;
}
.hamburger span {
  display: block;
  width: 100%;
  height: 2px;
  background: var(--text);
  border-radius: 2px;
  transition: all 0.3s;
}
.hamburger span.open:nth-child(1) {
  transform: translateY(7px) rotate(45deg);
}
.hamburger span.open:nth-child(2) {
  opacity: 0;
}
.hamburger span.open:nth-child(3) {
  transform: translateY(-7px) rotate(-45deg);
}

/* 移动端下拉菜单 */
.mobile-menu {
  display: none;
  position: fixed;
  top: 56px;
  left: 0;
  right: 0;
  background: #fff;
  border-bottom: 1px solid var(--border);
  box-shadow: var(--shadow-md);
  padding: 8px 0;
  z-index: 99;
}
.mobile-link {
  display: block;
  padding: 12px 20px;
  font-size: 15px;
  color: var(--text);
  text-decoration: none;
  border-bottom: 1px solid var(--border);
}
.mobile-link:last-child {
  border-bottom: none;
}
.mobile-link:hover {
  background: var(--bg);
  text-decoration: none;
}
.logout-btn {
  color: var(--danger);
  background: none;
  border: none;
  width: 100%;
  text-align: left;
  cursor: pointer;
  font-size: 15px;
}

/* 过渡动画 */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.25s ease;
}
.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* 移动端适配 */
@media (max-width: 768px) {
  .nav-desktop {
    display: none !important;
  }
  .hamburger {
    display: flex;
  }
  .mobile-menu {
    display: block;
  }
}
</style>

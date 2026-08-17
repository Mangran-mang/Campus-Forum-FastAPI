<template>
  <header class="header">
    <div class="container header-inner">
      <router-link to="/posts" class="logo" @click="menuOpen = false">校园论坛</router-link>

      <!-- 桌面端导航 -->
      <nav class="nav nav-desktop" v-if="isLoggedIn">
        <router-link to="/posts" class="nav-link">首页</router-link>
        <router-link to="/goods" class="nav-link">二手交易</router-link>
        <router-link to="/announcements" class="nav-link">公告</router-link>
        <router-link to="/posts/create" class="nav-link">发帖</router-link>
        <router-link to="/messages" class="nav-link">私信</router-link>
        <router-link to="/notifications" class="nav-link">
          通知
          <span v-if="unreadCount > 0" class="badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
        </router-link>
        <router-link to="/profile" class="nav-link">我的</router-link>
        <button class="btn-outline btn-sm" @click="handleLogout">退出</button>
      </nav>
      <nav class="nav nav-desktop" v-else>
        <router-link to="/posts" class="nav-link">首页</router-link>
        <router-link to="/goods" class="nav-link">二手</router-link>
        <router-link to="/announcements" class="nav-link">公告</router-link>
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
          <router-link to="/goods" class="mobile-link" @click="menuOpen = false">二手交易</router-link>
          <router-link to="/announcements" class="mobile-link" @click="menuOpen = false">公告</router-link>
          <router-link to="/posts/create" class="mobile-link" @click="menuOpen = false">发帖</router-link>
          <router-link to="/messages" class="mobile-link" @click="menuOpen = false">私信</router-link>
          <router-link to="/notifications" class="mobile-link" @click="menuOpen = false">
            通知
            <span v-if="unreadCount > 0" class="badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
          </router-link>
          <router-link to="/profile" class="mobile-link" @click="menuOpen = false">我的</router-link>
          <button class="mobile-link logout-btn" @click="handleLogout(); menuOpen = false">退出登录</button>
        </template>
        <template v-else>
          <router-link to="/posts" class="mobile-link" @click="menuOpen = false">首页</router-link>
          <router-link to="/goods" class="mobile-link" @click="menuOpen = false">二手交易</router-link>
          <router-link to="/announcements" class="mobile-link" @click="menuOpen = false">公告</router-link>
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
  background: #fffdf5;
  /* 手绘波浪底边 */
  border-bottom: 2px solid #2d2a26;
  z-index: 100;
  display: flex;
  align-items: center;
  /* 胶带贴纸感 */
  box-shadow: 0 3px 0 rgba(61, 55, 41, 0.08);
}
.header::before {
  content: '';
  position: absolute;
  top: -8px;
  left: 24px;
  width: 64px;
  height: 18px;
  background: rgba(255, 217, 61, 0.55);
  transform: rotate(-4deg);
  border: 1.5px dashed rgba(45, 42, 38, 0.35);
  z-index: -1;
}
.header-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}
.logo {
  font-size: 20px;
  font-weight: 600;
  font-family: 'Ma Shan Zheng', 'ZCOOL KuaiLe', 'Kaiti SC', cursive;
  color: var(--primary);
  text-decoration: none;
  flex-shrink: 0;
  background: var(--yellow);
  padding: 2px 12px;
  border: 2px solid var(--text);
  border-radius: 255px 15px 225px 15px / 15px 225px 15px 255px;
  transform: rotate(-1.5deg);
  transition: transform 0.2s ease;
}
.logo:hover {
  transform: rotate(0deg) scale(1.03);
  background-image: none;
}
.nav {
  display: flex;
  align-items: center;
  gap: 16px;
}
.nav-link {
  color: var(--text-secondary);
  font-size: 15px;
  text-decoration: none;
  position: relative;
  padding: 4px 0;
  transition: color 0.2s ease;
}
.nav-link::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 0;
  height: 4px;
  background: var(--yellow);
  border-radius: 2px;
  transition: width 0.25s ease;
  z-index: -1;
}
.nav-link:hover {
  color: var(--primary);
  text-decoration: none;
}
.nav-link:hover::after {
  width: 100%;
}
.router-link-active.nav-link::after {
  width: 100%;
}
.router-link-active.nav-link {
  color: var(--primary);
}
.badge {
  background: var(--danger);
  color: #fff;
  font-size: 11px;
  padding: 1px 6px;
  border: 1.5px solid var(--text);
  border-radius: 255px 15px 225px 15px / 15px 225px 15px 255px;
  margin-left: 4px;
  vertical-align: top;
  animation: pulse-subtle 2s ease-in-out infinite;
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
  box-shadow: none;
  cursor: pointer;
}
.hamburger:hover {
  transform: none;
  box-shadow: none;
}
.hamburger span {
  display: block;
  width: 100%;
  height: 3px;
  background: var(--text);
  border-radius: 3px;
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
  background: #fffdf5;
  border-bottom: 2px solid var(--text);
  box-shadow: var(--shadow-md);
  padding: 8px 0;
  z-index: 99;
}
.mobile-link {
  display: block;
  padding: 12px 20px;
  font-size: 16px;
  color: var(--text);
  text-decoration: none;
  border-bottom: 1px dashed var(--border);
}
.mobile-link:last-child {
  border-bottom: none;
}
.mobile-link:hover {
  background: var(--primary-light);
  text-decoration: none;
}
.logout-btn {
  color: var(--danger);
  background: none;
  border: none;
  box-shadow: none;
  width: 100%;
  text-align: left;
  cursor: pointer;
  font-size: 16px;
}
.logout-btn:hover {
  transform: none;
  box-shadow: none;
  background: var(--primary-light);
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

<template>
  <div class="admin-shell">
    <!-- 侧边导航 -->
    <aside class="admin-aside">
      <div class="admin-brand">漫燃社区 · 后台</div>
      <nav class="admin-nav">
        <router-link to="/admin/users" class="admin-nav-item">用户管理</router-link>
        <router-link to="/admin/posts" class="admin-nav-item">帖子管理</router-link>
        <router-link to="/admin/goods" class="admin-nav-item">商品管理</router-link>
      </nav>
      <div class="admin-aside-footer">
        <router-link to="/posts" class="admin-nav-item">← 返回前台</router-link>
        <button class="admin-nav-item admin-logout" @click="handleLogout">退出登录</button>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="admin-main">
      <header class="admin-topbar">
        <span class="admin-who">
          {{ whoami.nickname || whoami.username || '管理员' }}
          <span class="admin-who-email">{{ whoami.email }}</span>
        </span>
      </header>
      <div class="admin-content">
        <router-view v-slot="{ Component }">
          <component :is="Component" />
        </router-view>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { userApi, clearAuth } from '../../api/index.js'

const router = useRouter()

const whoami = computed(() => {
  try {
    return JSON.parse(localStorage.getItem('user_info') || '{}')
  } catch {
    return {}
  }
})

async function handleLogout() {
  // 退出后台 = 退出整个账号（前后台同一套 token），回后台登录页
  try {
    await userApi.logout()
  } catch (e) {
    // 登出接口失败（如 token 已失效）不阻塞登出：本地状态照清。
    // 但要留痕 —— 空 catch 会把真实故障（网络断/后端挂）静默吞掉
    console.warn('logout 接口失败，仍继续本地登出:', e)
  }
  clearAuth()
  router.push('/admin/login')
}
</script>

<style scoped>
.admin-shell {
  display: flex;
  min-height: 100vh;
  background: var(--bg);
  color: var(--text);
}
.admin-aside {
  width: 200px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-card-solid);
  border-right: 1px solid var(--border);
  padding: 16px 10px;
}
.admin-brand {
  font-size: 15px;
  font-weight: 600;
  padding: 8px 10px 20px;
  color: var(--primary);
}
.admin-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}
.admin-nav-item {
  display: block;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 14px;
  color: var(--text-secondary);
  text-decoration: none;
  background: none;
  border: none;
  text-align: left;
  cursor: pointer;
  font-family: inherit;
  width: 100%;
}
.admin-nav-item:hover {
  background: var(--primary-light);
  color: var(--text);
}
.admin-nav-item.router-link-active {
  background: var(--primary-light);
  color: var(--primary);
  font-weight: 600;
}
.admin-aside-footer {
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-top: 1px solid var(--border);
  padding-top: 10px;
}
.admin-logout {
  color: var(--danger);
}
.admin-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.admin-topbar {
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 24px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-card-solid);
}
.admin-who {
  font-size: 14px;
}
.admin-who-email {
  margin-left: 10px;
  font-size: 12px;
  color: var(--text-muted);
}
.admin-content {
  flex: 1;
  padding: 24px;
}
@media (max-width: 768px) {
  .admin-shell { flex-direction: column; }
  .admin-aside { width: 100%; flex-direction: row; align-items: center; padding: 8px; }
  .admin-nav { flex-direction: row; }
  .admin-brand { padding: 8px; }
  .admin-aside-footer { flex-direction: row; border-top: none; padding: 0 8px; }
  .admin-nav-item { padding: 8px 10px; white-space: nowrap; }
}
</style>

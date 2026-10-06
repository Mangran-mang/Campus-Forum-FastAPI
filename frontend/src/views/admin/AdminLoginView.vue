<template>
  <div class="admin-login-page">
    <div class="admin-login-card card">
      <h2>后台管理</h2>
      <p class="admin-hint">仅管理员账号可登录</p>
      <form @submit.prevent="handleLogin">
        <div class="field">
          <label>邮箱</label>
          <input v-model="email" type="email" placeholder="管理员邮箱" required />
        </div>
        <div class="field">
          <label>密码</label>
          <input v-model="password" type="password" placeholder="请输入密码" required />
        </div>
        <p v-if="error" class="error-msg">{{ error }}</p>
        <button type="submit" class="btn-primary" style="width:100%;margin-top:8px" :disabled="loading">
          {{ loading ? '登录中...' : '登录后台' }}
        </button>
      </form>
      <p class="back-link">
        <router-link to="/posts">← 返回前台</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { adminApi } from '../../api/index.js'
import { pickErrorMessage } from '../../utils/errorMessage.js'

const router = useRouter()
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    const res = await adminApi.login({ email: email.value, password: password.value })
    if (res.code === 200) {
      // 后端登录时已验证 is_superuser，走到这里必定是管理员
      router.push('/admin/users')
    } else {
      // 非管理员/密码错/邮箱不存在，后端一律返回 401「邮箱或密码错误」——
      // 不区分文案是后端的防枚举设计，前端不要试图细分
      error.value = pickErrorMessage(res, '登录失败')
    }
  } catch (e) {
    error.value = '网络错误，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.admin-login-page {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}
.admin-login-card {
  width: 100%;
  max-width: 380px;
  padding: 32px 28px;
}
.admin-login-card h2 {
  margin-bottom: 4px;
  font-size: 22px;
}
.admin-hint {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 20px;
}
.field {
  margin-bottom: 16px;
}
.field label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}
.back-link {
  margin-top: 16px;
  text-align: center;
  font-size: 13px;
}
</style>

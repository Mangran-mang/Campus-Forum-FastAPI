<template>
  <div class="auth-page">
    <div class="auth-card card">
      <h2>注册</h2>
      <form @submit.prevent="handleRegister">
        <div class="field">
          <label>邮箱</label>
          <input v-model="email" type="email" placeholder="请输入邮箱" required />
        </div>
        <div class="field">
          <label>昵称</label>
          <input v-model="nickname" placeholder="给自己取个名字" />
        </div>
        <div class="field">
          <label>密码</label>
          <input v-model="password" type="password" placeholder="至少6位" required minlength="6" />
        </div>
        <p v-if="error" class="error-msg">{{ error }}</p>
        <button type="submit" class="btn-primary" style="width:100%;margin-top:8px" :disabled="loading">
          {{ loading ? '注册中...' : '注册' }}
        </button>
      </form>
      <p style="margin-top:16px;text-align:center;font-size:13px;color:var(--text-secondary)">
        已有账号？<router-link to="/login">去登录</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { userApi } from '../api/index.js'

const router = useRouter()
const email = ref('')
const nickname = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleRegister() {
  error.value = ''
  loading.value = true
  try {
    const res = await userApi.register({
      email: email.value,
      password: password.value,
      nickname: nickname.value || undefined,
    })
    if (res.code === 200) {
      router.push('/login')
    } else {
      error.value = res.detail || res.message || '注册失败'
    }
  } catch (e) {
    error.value = '网络错误'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  display: flex;
  justify-content: center;
  padding-top: 60px;
}
.auth-card {
  width: 100%;
  max-width: 380px;
}
.auth-card h2 {
  margin-bottom: 24px;
  font-size: 22px;
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

@media (max-width: 768px) {
  .auth-page {
    padding-top: 20px;
  }
  .auth-card {
    max-width: 100%;
  }
  .auth-card h2 {
    font-size: 20px;
    margin-bottom: 20px;
  }
}
</style>

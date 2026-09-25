<template>
  <div class="auth-page">
    <div class="auth-card card content-enter">
      <h2>注册</h2>
      <form @submit.prevent="handleRegister">
        <div class="field">
          <label>邮箱</label>
          <input v-model="email" type="email" placeholder="请输入邮箱" required autocomplete="email" />
        </div>
        <div class="field">
          <label>昵称</label>
          <input v-model="nickname" placeholder="给自己取个名字" maxlength="50" />
        </div>
        <div class="field">
          <label>密码</label>
          <input v-model="password" type="password" placeholder="请输入密码" required autocomplete="new-password" />
          <p class="field-hint">至少 8 位</p>
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
import { pickErrorMessage } from '../utils/errorMessage.js'

const router = useRouter()
const email = ref('')
const nickname = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

// 与 models/model_user.py 的 String(50) 对齐，避免超长昵称打过去被数据库拒绝
const MAX_NICKNAME = 50
const MIN_PASSWORD = 8

// 本地校验：给出明确的中文提示，同时避免发一次注定失败的请求
//
// ## 为什么密码框上【不写】HTML 的 minlength 属性
// 浏览器的原生校验发生在 submit 事件**之前**：只要 minlength 不满足，
// submit 根本不会触发，handleRegister 里这段提示永远轮不到执行。
// 用户看到的会是浏览器自己的文案（"请将该文本延长到 8 个字符或更多"），
// 既不说清是"密码"的限制，各浏览器还不一致。
// 所以长度规则只在前端写这一处（外加后端 min_length 作真正把关），文案才可控。
//
// ## 为什么这里要多校验一遍，后端不是也有吗
// 后端那道 422 是**最后防线**，不是交互层。让用户填完点提交、转一圈再被打回，
// 体验差且浪费一次往返。本地这层的职责是"提前说清楚规则"，
// 后端的职责是"无论前端怎么做都不能被绕过"——两层都要有，不是重复。
function validate() {
  if (!email.value.trim()) return '请输入邮箱'
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim())) {
    return '邮箱格式不正确，请检查是否漏了 @ 或域名'
  }
  if (password.value.length < MIN_PASSWORD) {
    return `密码至少 ${MIN_PASSWORD} 位（当前 ${password.value.length} 位）`
  }
  if (nickname.value.length > MAX_NICKNAME) {
    return `昵称最多 ${MAX_NICKNAME} 个字符（当前 ${nickname.value.length} 个）`
  }
  return ''
}

async function handleRegister() {
  error.value = ''
  const localMsg = validate()
  if (localMsg) {
    error.value = localMsg
    return
  }

  loading.value = true
  try {
    const res = await userApi.register({
      email: email.value.trim(),
      password: password.value,
      nickname: nickname.value || undefined,
    })
    if (res.code === 200) {
      router.push('/login')
    } else {
      // 422 时后端把字段级明细放在 data 里，由 pickErrorMessage 翻成中文
      error.value = pickErrorMessage(res, '注册失败，请稍后重试')
    }
  } catch (e) {
    error.value = '网络错误，请检查网络后重试'
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
/* 常驻的规则提示：placeholder 一输入就没了，规则类信息要一直看得见 */
.field-hint {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--text-secondary);
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

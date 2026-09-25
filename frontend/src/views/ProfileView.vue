<template>
  <div v-if="!isLoggedIn" class="empty-state">
    <p>请先登录</p>
    <router-link to="/login" class="btn-primary" style="display:inline-block;margin-top:12px">去登录</router-link>
  </div>
  <div v-else-if="loading" class="skeleton-list">
    <div class="skeleton-card">
      <div class="skeleton skeleton-title" style="width:40%"></div>
      <div class="skeleton skeleton-text" style="width:60%"></div>
      <div class="skeleton skeleton-text" style="width:50%"></div>
      <div class="skeleton skeleton-text" style="width:45%"></div>
      <div class="skeleton skeleton-text" style="width:55%"></div>
      <div class="skeleton skeleton-text" style="width:40%"></div>
    </div>
  </div>
  <div v-else class="content-enter">
    <!-- 个人信息卡片（查看/编辑模式） -->
    <div class="card">
      <div class="flex-between" style="margin-bottom:16px">
        <h2 style="font-size:20px">个人主页</h2>
        <button class="btn-outline btn-sm" @click="toggleEdit">
          {{ editing ? '取消' : '编辑资料' }}
        </button>
      </div>

      <!-- 查看模式 -->
      <template v-if="!editing">
        <div class="info-row"><label>邮箱</label><span>{{ user.email }}</span></div>
        <div class="info-row"><label>昵称</label><span>{{ user.nickname || '未设置' }}</span></div>
        <div class="info-row"><label>用户名</label><span>{{ user.username || '未设置' }}</span></div>
        <div class="info-row"><label>性别</label><span>{{ user.gender || '未知' }}</span></div>
        <div class="info-row">
          <label>等级</label>
          <span class="level-badge">{{ levelLabel(user.level) }} {{ levelName(user.level) }}</span>
        </div>
        <div class="info-row">
          <label>经验</label><span>{{ user.experience || 0 }}</span>
          <div class="level-progress" style="flex:1;margin-left:12px">
            <div class="level-progress-bar" :style="{ width: levelProgress(user.experience || 0, user.level) + '%' }"></div>
          </div>
        </div>
        <div class="info-row level-hint" v-if="nextLevelExp(user.level) !== null">
          <label></label>
          <span>距 {{ levelLabel(user.level + 1) }} 还差 <b>{{ nextLevelExp(user.level) - (user.experience || 0) }}</b> 经验</span>
        </div>
        <div class="info-row level-hint" v-else>
          <label></label>
          <span>已达到最高等级 🎉</span>
        </div>
        <div class="info-row">
          <label>身份</label>
          <span class="role-badge" :class="user.is_superuser ? 'role-admin' : 'role-user'">
            {{ user.is_superuser ? '管理员' : '普通用户' }}
          </span>
        </div>
        <div class="info-row"><label>注册时间</label><span>{{ formatTime(user.created_time) }}</span></div>
      </template>

      <!-- 编辑模式 -->
      <template v-else>
        <form @submit.prevent="handleSave">
          <div class="field">
            <label>昵称</label>
            <input v-model="editForm.nickname" placeholder="给自己取个名字" maxlength="50" />
          </div>
          <div class="field">
            <label>用户名</label>
            <input v-model="editForm.username" placeholder="设置用户名" maxlength="50" />
          </div>
          <div class="field">
            <label>性别</label>
            <select v-model="editForm.gender">
              <option value="未知">未知</option>
              <option value="男">男</option>
              <option value="女">女</option>
            </select>
          </div>
          <p v-if="saveError" class="error-msg">{{ saveError }}</p>
          <p v-if="saveSuccess" style="color:var(--success);font-size:13px;margin-top:4px">保存成功</p>
          <button type="submit" class="btn-primary" :disabled="saving" style="margin-top:8px">
            {{ saving ? '保存中...' : '保存修改' }}
          </button>
        </form>
      </template>
    </div>

    <!-- 修改密码（独立卡片：改资料只动昵称/性别，改密码是敏感操作，单独一条路） -->
    <div class="card" style="margin-top:24px">
      <div class="flex-between" style="margin-bottom:12px">
        <h3 style="font-size:16px">修改密码</h3>
        <button v-if="!pwdEditing" class="btn-outline btn-sm" @click="togglePwd">修改</button>
      </div>

      <p v-if="!pwdEditing" style="font-size:13px;color:var(--text-secondary);margin:0">
        需要先输入当前密码。修改成功后当前登录状态会失效，请用新密码重新登录。
      </p>

      <form v-else @submit.prevent="handleChangePassword">
        <div class="field">
          <label>当前密码</label>
          <input v-model="pwdForm.old_password" type="password" autocomplete="current-password"
                 placeholder="请输入当前使用的密码" />
        </div>
        <div class="field">
          <label>新密码</label>
          <input v-model="pwdForm.new_password" type="password" autocomplete="new-password"
                 placeholder="至少 8 位" />
        </div>
        <div class="field">
          <label>确认新密码</label>
          <input v-model="pwdForm.confirm_password" type="password" autocomplete="new-password"
                 placeholder="再输入一次新密码" />
        </div>
        <p v-if="pwdError" class="error-msg">{{ pwdError }}</p>
        <div style="display:flex;gap:8px;margin-top:4px">
          <button type="submit" class="btn-primary" :disabled="pwdSaving">
            {{ pwdSaving ? '提交中...' : '确认修改' }}
          </button>
          <button type="button" class="btn-outline" @click="togglePwd">取消</button>
        </div>
      </form>
    </div>

    <!-- 我的帖子 -->
    <div style="margin-top:24px">
      <h3 style="font-size:16px;margin-bottom:12px">我的帖子</h3>
      <PostCard v-for="post in myPosts" :key="post.id" :post="post" />
      <div v-if="myPosts.length === 0" class="empty-state">还没有发过帖子</div>
    </div>

    <div style="margin-top:24px;padding-top:24px;border-top:1px solid var(--border)">
      <button class="btn-danger" @click="handleLogout">退出登录</button>
      <button class="btn-danger" style="margin-left:8px" @click="handleDeleteAccount">删除账号</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import PostCard from '../components/PostCard.vue'
import { userApi, postApi, clearAuth } from '../api/index.js'
import { levelLabel, levelName, levelProgress, nextLevelExp } from '../utils/level.js'
import { pickErrorMessage } from '../utils/errorMessage.js'

const router = useRouter()
const isLoggedIn = ref(!!localStorage.getItem('access_token'))
const loading = ref(true)
const user = ref({})
const myPosts = ref([])
const editing = ref(false)
const saving = ref(false)
const saveError = ref('')
const saveSuccess = ref(false)

const editForm = reactive({
  nickname: '',
  username: '',
  gender: '未知',
  avatar_url: '',
})

// ========== 修改密码 ==========
const pwdEditing = ref(false)
const pwdSaving = ref(false)
const pwdError = ref('')
const pwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

function formatTime(t) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN')
}

async function loadProfile() {
  loading.value = true
  try {
    const res = await userApi.getCurrentUser()
    if (res.code === 200) {
      user.value = res.data || res
      // 同步到编辑表单
      editForm.nickname = user.value.nickname || ''
      editForm.username = user.value.username || ''
      editForm.gender = user.value.gender || '未知'
      editForm.avatar_url = user.value.avatar_url || ''
    }
    const postRes = await postApi.getList({ author_uid: user.value.uid, page_size: 50 })
    if (postRes.code === 200) myPosts.value = postRes.data || []
  } catch {} finally {
    loading.value = false
  }
}

function toggleEdit() {
  editing.value = !editing.value
  saveError.value = ''
  saveSuccess.value = false
  // 取消编辑时恢复原始值
  if (!editing.value) {
    editForm.nickname = user.value.nickname || ''
    editForm.username = user.value.username || ''
    editForm.gender = user.value.gender || '未知'
    editForm.avatar_url = user.value.avatar_url || ''
  }
}

async function handleSave() {
  saveError.value = ''
  saveSuccess.value = false
  saving.value = true
  try {
    const res = await userApi.updateUser({
      email: user.value.email,
      nickname: editForm.nickname || null,
      username: editForm.username || null,
      gender: editForm.gender,
      avatar_url: editForm.avatar_url || null,
    })
    if (res.code === 200) {
      user.value = res.data
      saveSuccess.value = true
      setTimeout(() => { editing.value = false }, 1000)
    } else {
      saveError.value = pickErrorMessage(res, '保存失败，请稍后重试')
    }
  } catch {
    saveError.value = '网络错误，请稍后重试'
  } finally {
    saving.value = false
  }
}

function handleLogout() {
  userApi.logout().catch(() => {})
  clearAuth()
  router.push('/login')
}

async function handleDeleteAccount() {
  if (!confirm('确定删除账号？此操作不可恢复！')) return
  if (!confirm('再次确认：真的要删除账号吗？')) return
  try {
    await userApi.deleteUser(user.value.email)
    clearAuth()
    router.push('/login')
  } catch {}
}

// ========== 修改密码 ==========
function togglePwd() {
  pwdEditing.value = !pwdEditing.value
  pwdError.value = ''
  // 收起时清空，避免把上次输的密码留在页面上
  pwdForm.old_password = ''
  pwdForm.new_password = ''
  pwdForm.confirm_password = ''
}

async function handleChangePassword() {
  pwdError.value = ''
  // ## 前端这道校验只是"少发一次注定失败的请求"，真正的约束在后端
  // ChangePasswordModel 里 new_password 有 min_length=8，old_password 故意没有
  // （存量用户的旧密码可能是老规则下设的短密码，卡了他们就永远改不了密码）
  if (!pwdForm.old_password) { pwdError.value = '请输入当前密码'; return }
  if (pwdForm.new_password.length < 8) { pwdError.value = '新密码至少 8 位'; return }
  if (pwdForm.new_password !== pwdForm.confirm_password) { pwdError.value = '两次输入的新密码不一致'; return }
  if (pwdForm.new_password === pwdForm.old_password) { pwdError.value = '新密码不能与当前密码相同'; return }

  pwdSaving.value = true
  try {
    const res = await userApi.changePassword({
      old_password: pwdForm.old_password,
      new_password: pwdForm.new_password,
    })
    if (res.code === 200) {
      // 后端已经作废本用户的全部会话（删 token 行 + 拉黑 refresh 的 jti），
      // 本地这份 token 随即失效——不清掉的话后续请求会到处 401/403
      alert('密码修改成功，请使用新密码重新登录')
      clearAuth()
      router.push('/login')
    } else {
      // 统一走 pickErrorMessage：422 时它会读 data 里的字段明细并翻成中文。
      // 原来手工拼 `${field}: ${message}` 会把 pydantic 的英文原文直接甩给用户
      // （"new_password: String should have at least 8 characters"），等于没说。
      // 401（原密码不正确）这类业务异常本来 message 就是中文，直接透传。
      pwdError.value = pickErrorMessage(res, '修改失败，请稍后重试')
    }
  } catch {
    pwdError.value = '网络错误，请稍后重试'
  } finally {
    pwdSaving.value = false
  }
}

onMounted(() => {
  if (isLoggedIn.value) loadProfile()
  else loading.value = false
})
</script>

<style scoped>
.info-row {
  display: flex;
  margin-bottom: 10px;
  font-size: 14px;
}
.info-row label {
  color: var(--text-secondary);
  width: 80px;
  flex-shrink: 0;
}
.field {
  margin-bottom: 14px;
}
.field label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

@media (max-width: 768px) {
  .info-row {
    flex-direction: column;
    margin-bottom: 12px;
  }
  .info-row label {
    width: auto;
    margin-bottom: 2px;
  }
}
</style>

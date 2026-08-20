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
            <input v-model="editForm.nickname" placeholder="给自己取个名字" />
          </div>
          <div class="field">
            <label>用户名</label>
            <input v-model="editForm.username" placeholder="设置用户名" />
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
      saveError.value = res.detail || res.message || '保存失败'
    }
  } catch {
    saveError.value = '网络错误'
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

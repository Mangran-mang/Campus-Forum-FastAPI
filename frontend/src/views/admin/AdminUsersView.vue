<template>
  <div class="admin-page">
    <h3 class="admin-title">用户管理</h3>

    <div class="card admin-table-card">
      <table class="admin-table">
        <thead>
          <tr>
            <th>昵称</th>
            <th>邮箱</th>
            <th>性别</th>
            <th>等级</th>
            <th>发帖</th>
            <th>评论</th>
            <th>商品</th>
            <th>注册时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="9" class="admin-empty">加载中...</td>
          </tr>
          <tr v-else-if="users.length === 0">
            <td colspan="9" class="admin-empty">暂无数据</td>
          </tr>
          <tr v-for="u in users" :key="u.uid">
            <td>
              {{ u.nickname }}
              <span v-if="u.is_superuser" class="tag-admin">管理员</span>
            </td>
            <td>{{ u.email }}</td>
            <td>{{ u.gender }}</td>
            <td>{{ u.level }}</td>
            <td>{{ u.post_count }}</td>
            <td>{{ u.comment_count }}</td>
            <td>{{ u.goods_count }}</td>
            <td>{{ formatTime(u.created_time) }}</td>
            <td class="admin-actions">
              <button class="btn-outline btn-sm" @click="openEdit(u)">编辑</button>
              <button
                class="btn-danger btn-sm"
                :disabled="u.email === whoami.email"
                :title="u.email === whoami.email ? '不能删除自己' : ''"
                @click="handleDelete(u)"
              >
                删除
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="admin-pager">
        <button class="btn-outline btn-sm" :disabled="page <= 1 || loading" @click="load(page - 1)">上一页</button>
        <span class="admin-pager-info">第 {{ page }} 页 / 共 {{ totalPages }} 页（{{ total }} 人）</span>
        <button class="btn-outline btn-sm" :disabled="page >= totalPages || loading" @click="load(page + 1)">下一页</button>
      </div>
    </div>

    <!-- 编辑弹窗 -->
    <div v-if="editing" class="modal-mask" @click.self="editing = null">
      <div class="card modal-card">
        <h4>编辑用户：{{ editing.email }}</h4>
        <div class="field">
          <label>昵称</label>
          <input v-model="editForm.nickname" type="text" maxlength="30" />
        </div>
        <div class="field">
          <label>性别</label>
          <select v-model="editForm.gender">
            <option>男</option>
            <option>女</option>
            <option>未知</option>
          </select>
        </div>
        <p v-if="editError" class="error-msg">{{ editError }}</p>
        <div class="modal-actions">
          <button class="btn-outline btn-sm" @click="editing = null">取消</button>
          <button class="btn-primary btn-sm" :disabled="editLoading" @click="submitEdit">
            {{ editLoading ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { adminApi } from '../../api/index.js'
import { pickErrorMessage } from '../../utils/errorMessage.js'

const PAGE_SIZE = 10

const users = ref([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const error = ref('')

const editing = ref(null) // 被编辑用户的原始数据
const editForm = ref({ email: '', nickname: '', gender: '未知' })
const editError = ref('')
const editLoading = ref(false)

const whoami = computed(() => {
  try {
    return JSON.parse(localStorage.getItem('user_info') || '{}')
  } catch {
    return {}
  }
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

function formatTime(iso) {
  return iso ? String(iso).slice(0, 10) : ''
}

async function load(p = page.value) {
  loading.value = true
  error.value = ''
  try {
    const res = await adminApi.getUsers({ page: p, page_size: PAGE_SIZE })
    if (res.code === 200) {
      users.value = res.data.users
      total.value = res.data.total
      // 后端可能 clamp 过 page/size，用回显的生效值更新本地页码，
      // 否则分页器显示的页码和后端实际执行的页码会静默不一致
      page.value = res.data.page
    } else {
      error.value = pickErrorMessage(res, '获取用户列表失败')
    }
  } catch (e) {
    error.value = '网络错误，请稍后重试'
  } finally {
    loading.value = false
  }
}

function openEdit(u) {
  editing.value = u
  editError.value = ''
  editForm.value = { email: u.email, nickname: u.nickname || '', gender: u.gender || '未知' }
}

async function submitEdit() {
  editError.value = ''
  editLoading.value = true
  try {
    // UserUpdateModel 的 password 是 Optional 且有 exclude_unset —— 不传就不改密码
    const res = await adminApi.updateUser({
      email: editForm.value.email,
      nickname: editForm.value.nickname,
      gender: editForm.value.gender,
    })
    if (res.code === 200) {
      editing.value = null
      await load(page.value)
    } else {
      editError.value = pickErrorMessage(res, '更新失败')
    }
  } catch (e) {
    editError.value = '网络错误，请稍后重试'
  } finally {
    editLoading.value = false
  }
}

async function handleDelete(u) {
  // ## 前端先挡「删自己」
  // 后端 delete_user 目前没有这层拦截，删了只能 ssh 上服务器改库；
  // 前端禁用按钮是体验层，真正的拦截要等后端补（两行 if 的事）
  if (u.email === whoami.value.email) return

  // ## 二次确认必须写明级联后果（注意事项 3.2）
  // User 的所有关系都是 ON DELETE CASCADE，删一个人实际会连带删掉
  // 他帖子下【别人写的评论】—— 这是管理员必须看到的代价
  const msg =
    `确定删除用户「${u.nickname || u.email}」？\n\n` +
    '此操作不可逆：该用户的帖子、评论、商品、私信、点赞收藏将全部删除，\n' +
    '且其帖子下其他人写的评论也会被连带删除。'
  if (!window.confirm(msg)) return

  try {
    const res = await adminApi.deleteUser(u.email)
    // 操作类请求：先确认 code===200 再动本地数据，避免 4xx 也当成功
    if (res.code === 200) {
      await load(page.value)
    } else {
      window.alert(pickErrorMessage(res, '删除失败'))
    }
  } catch (e) {
    window.alert('网络错误，请稍后重试')
  }
}

onMounted(() => load(1))
</script>

<style scoped>
.admin-page {
  max-width: 1100px;
}
.admin-title {
  margin-bottom: 16px;
  font-size: 18px;
}
.admin-table-card {
  overflow-x: auto;
}
.admin-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.admin-table th,
.admin-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
.admin-table th {
  color: var(--text-secondary);
  font-weight: 600;
  font-size: 12px;
}
.admin-empty {
  text-align: center;
  color: var(--text-muted);
  padding: 32px 0;
}
.tag-admin {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
  background: var(--primary-light);
  color: var(--primary);
}
.admin-actions {
  display: flex;
  gap: 8px;
}
.admin-pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding-top: 16px;
}
.admin-pager-info {
  font-size: 13px;
  color: var(--text-secondary);
}
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.modal-card {
  width: 100%;
  max-width: 380px;
  padding: 24px;
}
.modal-card h4 {
  margin-bottom: 16px;
  font-size: 16px;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
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
.field input,
.field select {
  width: 100%;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--bg-card-solid);
  color: var(--text);
  font-family: inherit;
}
</style>

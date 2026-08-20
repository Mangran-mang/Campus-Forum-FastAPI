<template>
  <div>
    <div class="flex-between mb-16">
      <h2 style="font-size:20px">私信</h2>
      <button class="btn-primary btn-sm" @click="showSearch = !showSearch">
        {{ showSearch ? '收起搜索' : '＋ 添加私信' }}
      </button>
    </div>

    <!-- 搜索用户添加私信 -->
    <div v-if="showSearch" class="search-panel card mb-16 content-enter">
      <div class="search-box">
        <input
          v-model="keyword"
          type="text"
          placeholder="搜索昵称 / 用户名 / 邮箱…"
          @keyup.enter="doSearch"
        />
        <button class="btn-primary" @click="doSearch">搜索</button>
      </div>

      <div v-if="searching" class="loading" style="padding:16px"><span class="spinner"></span></div>
      <div v-else-if="searchResults.length > 0" class="search-results">
        <div v-for="u in searchResults" :key="u.uid" class="search-item">
          <div class="search-user-info">
            <span class="search-nickname">{{ u.nickname || u.username || u.email }}</span>
            <span v-if="u.nickname && u.username && u.nickname !== u.username" class="search-username">@{{ u.username }}</span>
            <span class="lv-badge">Lv.{{ u.level ?? 0 }}</span>
          </div>
          <button class="btn-outline btn-sm" @click="startChat(u)" :disabled="u._starting">
            {{ u._starting ? '…' : '私信' }}
          </button>
        </div>
      </div>
      <div v-else-if="searched" class="empty-state" style="padding:16px">
        <p>没有找到相关用户</p>
      </div>
    </div>

    <!-- 会话列表 -->
    <div v-if="loading" class="skeleton-list">
      <div class="skeleton-card" v-for="i in 3" :key="i">
        <div class="skeleton-meta">
          <div class="skeleton skeleton-avatar"></div>
          <div class="skeleton skeleton-text" style="width:120px"></div>
        </div>
      </div>
    </div>
    <div v-else-if="conversations.length === 0" class="empty-state">
      <p>还没有私信会话</p>
      <p style="font-size:13px;margin-top:8px">点击上方「添加私信」，搜索用户开始聊天</p>
    </div>
    <div v-else>
      <div
        v-for="(conv, idx) in conversations"
        :key="conv.id"
        class="conv-item card stagger-item"
        @click="openChat(conv)"
      >
        <div class="conv-avatar">{{ (conv.other_user?.nickname || conv.other_user?.username || '?').slice(0, 1) }}</div>
        <div class="conv-body">
          <div class="conv-header">
            <span class="conv-name">
              {{ conv.other_user?.nickname || conv.other_user?.username || '未知用户' }}
              <span v-if="conv.other_user?.is_superuser" class="admin-badge">管理员</span>
            </span>
            <span class="conv-time">{{ formatTime(conv.updated_time) }}</span>
          </div>
          <div class="conv-last">{{ conv.last_message ? conv.last_message.content : '暂无消息' }}</div>
        </div>
        <div v-if="idx === 0" class="conv-arrow">→</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { messageApi } from '../api/index.js'

const router = useRouter()
const conversations = ref([])
const loading = ref(true)

// 搜索
const showSearch = ref(false)
const keyword = ref('')
const searching = ref(false)
const searched = ref(false)
const searchResults = ref([])

// 轮询（2 分钟）
let timer = null

function formatTime(t) {
  if (!t) return ''
  const d = new Date(t)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return d.toLocaleDateString('zh-CN')
}

async function loadConversations() {
  try {
    const res = await messageApi.getConversations({ page: 1, page_size: 50 })
    if (res.code === 200) {
      conversations.value = res.data?.conversations || []
    }
  } catch {} finally {
    loading.value = false
  }
}

async function doSearch() {
  const kw = keyword.value.trim()
  if (!kw) return
  searching.value = true
  searched.value = true
  try {
    const res = await messageApi.searchUsers(kw)
    searchResults.value = res.code === 200 ? (res.data || []) : []
  } catch {
    searchResults.value = []
  } finally {
    searching.value = false
  }
}

async function startChat(user) {
  user._starting = true
  try {
    const res = await messageApi.getOrCreateConversation(user.uid)
    if (res.code === 200 && res.data?.id) {
      router.push(`/messages/${res.data.id}`)
    }
  } catch {} finally {
    user._starting = false
  }
}

function openChat(conv) {
  router.push(`/messages/${conv.id}`)
}

onMounted(() => {
  loadConversations()
  timer = setInterval(loadConversations, 120000)  // 2 分钟轮询刷新
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.search-panel {
  padding: 16px;
}
.search-box {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.search-box input {
  flex: 1;
}
.search-results {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.search-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: rgba(17, 26, 48, 0.45);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.search-item:hover {
  border-color: var(--border-hover);
  box-shadow: var(--shadow);
}
.search-user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.search-nickname {
  font-weight: 600;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.search-username {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
}
.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.skeleton-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}
.skeleton-meta .skeleton-text { margin-bottom: 0; }
.conv-item {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: box-shadow 0.25s ease, transform 0.25s ease;
}
.conv-item:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.conv-avatar {
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary), var(--purple));
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  box-shadow: 0 0 12px rgba(106, 168, 255, 0.35);
}
.conv-body {
  flex: 1;
  min-width: 0;
}
.conv-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2px;
  gap: 8px;
}
.conv-name {
  font-size: 15px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.conv-time {
  font-size: 12px;
  color: var(--text-muted);
  flex-shrink: 0;
}
.conv-last {
  font-size: 13px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.conv-arrow {
  font-size: 18px;
  color: var(--primary);
  flex-shrink: 0;
}
</style>

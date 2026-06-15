<template>
  <div>
    <div class="flex-between mb-16">
      <h2 style="font-size:20px">通知</h2>
      <button class="btn-outline btn-sm" @click="markAllRead" v-if="hasUnread">全部标记已读</button>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="notifications.length === 0" class="empty-state"><p>暂无通知</p></div>
    <div v-else>
      <div
        v-for="notif in notifications"
        :key="notif.id"
        class="notif-item card"
        :class="{ unread: !notif.is_read }"
        @click="handleClick(notif)"
      >
        <div class="notif-header">
          <span class="notif-type">{{ notifTypeLabel(notif.notif_type) }}</span>
          <span class="notif-time">{{ formatTime(notif.created_time) }}</span>
        </div>
        <div class="notif-content">{{ notif.content }}</div>
        <div v-if="!notif.is_read" class="unread-dot"></div>
      </div>

      <div class="pagination">
        <button class="btn-outline btn-sm" :disabled="page <= 1" @click="loadNotifs(page - 1)">上一页</button>
        <span style="font-size:13px;color:var(--text-secondary)">第 {{ page }} 页</span>
        <button class="btn-outline btn-sm" :disabled="!hasMore" @click="loadNotifs(page + 1)">下一页</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { notificationApi } from '../api/index.js'

const router = useRouter()
const notifications = ref([])
const loading = ref(true)
const page = ref(1)
const hasMore = ref(false)
const hasUnread = ref(false)

function notifTypeLabel(type) {
  const map = { reply: '回复', like: '点赞', system: '系统通知' }
  return map[type] || type
}

function formatTime(t) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN')
}

async function loadNotifs(p) {
  page.value = p
  loading.value = true
  try {
    const res = await notificationApi.getList({ page: p, page_size: 20 })
    if (res.code === 200) {
      notifications.value = res.data?.notifications || []
      hasMore.value = notifications.value.length >= 20
      hasUnread.value = notifications.value.some(n => !n.is_read)
    }
  } catch {} finally {
    loading.value = false
  }
}

async function markAllRead() {
  try {
    await notificationApi.markAllRead()
    notifications.value.forEach(n => n.is_read = true)
    hasUnread.value = false
    window.dispatchEvent(new Event('auth-change'))
  } catch {}
}

async function handleClick(notif) {
  if (!notif.is_read) {
    await notificationApi.markRead(notif.id)
    notif.is_read = true
    window.dispatchEvent(new Event('auth-change'))
  }
  if (notif.post_id) {
    router.push(`/posts/${notif.post_id}`)
  }
}

onMounted(() => loadNotifs(1))
</script>

<style scoped>
.notif-item {
  margin-bottom: 8px;
  cursor: pointer;
  position: relative;
}
.notif-item.unread {
  border-left: 3px solid var(--primary);
}
.notif-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}
.notif-type {
  font-size: 12px;
  background: var(--primary-light);
  color: var(--primary);
  padding: 2px 8px;
  border-radius: 4px;
}
.notif-time {
  font-size: 12px;
  color: var(--text-muted);
}
.notif-content {
  font-size: 14px;
  line-height: 1.5;
}
.unread-dot {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 8px;
  height: 8px;
  background: var(--danger);
  border-radius: 50%;
}
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 24px;
}
</style>

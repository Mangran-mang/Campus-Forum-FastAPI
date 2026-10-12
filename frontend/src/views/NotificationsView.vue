<template>
  <div>
    <div class="flex-between mb-16">
      <h2 style="font-size:20px">通知</h2>
      <div style="display:flex;gap:8px">
        <button class="btn-outline btn-sm" @click="clearRead" v-if="hasRead">清空已读</button>
        <button class="btn-outline btn-sm" @click="markAllRead" v-if="hasUnread">全部标记已读</button>
      </div>
    </div>

    <div v-if="loading" class="skeleton-list">
      <div class="skeleton-card" v-for="i in 3" :key="i">
        <div class="skeleton-meta">
          <div class="skeleton skeleton-text" style="width:60px"></div>
          <div class="skeleton skeleton-text" style="width:100px"></div>
        </div>
        <div class="skeleton skeleton-text"></div>
      </div>
    </div>
    <div v-else-if="notifications.length === 0" class="empty-state"><p>暂无通知</p></div>
    <div v-else>
      <div
        v-for="notif in notifications"
        :key="notif.id"
        class="notif-item card stagger-item"
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
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { notificationApi, messageApi } from '../api/index.js'

const router = useRouter()
const notifications = ref([])
const loading = ref(true)
const page = ref(1)
const hasMore = ref(false)
const hasUnread = ref(false)
// 有已读通知时才显示"清空已读"按钮（与 hasUnread 对称：没得清就别摆按钮）
const hasRead = computed(() => notifications.value.some((n) => n.is_read))

function notifTypeLabel(type) {
  const map = {
    reply: '回复',
    like: '点赞',
    system: '系统通知',
    report: '举报',
    goods_reserve: '商品预定',
    goods_sold: '商品已售出',
  }
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

// 清空已读通知（未读的保留）
async function clearRead() {
  // 删除不可撤销，必须先确认；文案里说清"未读会保留"，避免用户以为要清空全部
  const ok = window.confirm(
    '清空所有已读通知？\n\n未读的通知会保留；已读的清掉后无法恢复。',
  )
  if (!ok) return
  try {
    const res = await notificationApi.clearRead()
    if (res.code === 200) {
      // 用服务端返回的条数（message 里带着），比笼统的"成功"更能确认做了什么
      window.alert(res.message || '已清理')
      await loadNotifs(1)
      window.dispatchEvent(new Event('auth-change'))
    }
  } catch (e) {
    console.warn('清空已读失败:', e)
  }
}

async function handleClick(notif) {
  if (!notif.is_read) {
    await notificationApi.markRead(notif.id)
    notif.is_read = true
    window.dispatchEvent(new Event('auth-change'))
  }
  if (notif.post_id) {
    router.push(`/posts/${notif.post_id}`)
    return
  }
  // 商品预定通知：直接进与买家的会话
  // ## 为什么前端要再调一次建会话接口，而不是让通知带 conversation_id
  // 会话是"两个人一条记录"，与商品无关（uq_conversation_pair 决定的一对唯一）。
  // 卖家点通知的真实意图是"去找买家聊"，get_or_create 幂等，拿到的必然是同一个会话。
  if (notif.goods_id && notif.sender_uid) {
    try {
      const res = await messageApi.getOrCreateConversation(notif.sender_uid)
      if (res.code === 200) router.push(`/messages/${res.data.id}`)
    } catch (e) {
      console.warn('进入会话失败:', e)
    }
  }
}

onMounted(() => loadNotifs(1))
</script>

<style scoped>
.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.skeleton-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.skeleton-meta .skeleton-text { width: 80px; margin-bottom: 0; }
.notif-item {
  margin-bottom: 8px;
  cursor: pointer;
  position: relative;
  transition: box-shadow 0.25s ease, transform 0.25s ease, border-color 0.25s ease;
}
.notif-item:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}
.notif-item.unread {
  border-left: 3px solid var(--primary);
  background: #fafbff;
}
.notif-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  margin-bottom: 4px;
  gap: 6px;
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
  word-break: break-word;
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

@media (max-width: 768px) {
  .unread-dot {
    top: 10px;
    right: 10px;
  }
  .pagination {
    gap: 10px;
    margin-top: 16px;
  }
}
</style>

<template>
  <div class="chat-page">
    <div class="chat-header card">
      <button class="btn-outline btn-sm" @click="router.back()">← 返回</button>
      <div class="chat-title">
        <span class="chat-avatar">{{ otherName.slice(0, 1) }}</span>
        <span class="chat-name">
          {{ otherName }}
          <span v-if="otherUser?.is_superuser" class="admin-badge">管理员</span>
        </span>
      </div>
      <span class="chat-hint">实时消息</span>
    </div>

    <div class="chat-body card">
      <div v-if="loading" class="loading"><span class="spinner"></span></div>
      <div v-else-if="messages.length === 0" class="empty-state">
        <p>还没有消息，说点什么吧～</p>
      </div>
      <div v-else class="msg-list" ref="msgListEl">
        <div
          v-for="m in messages"
          :key="m.id"
          class="msg-row"
          :class="{ mine: m.sender_uid === myUid }"
        >
          <div class="msg-bubble">
            <div class="msg-content">{{ m.content }}</div>
            <div class="msg-time">{{ formatTime(m.created_time) }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="chat-input">
      <textarea
        v-model="draft"
        rows="2"
        placeholder="输入消息，Enter 发送 / Shift+Enter 换行"
        @keydown.enter.exact.prevent="send"
      ></textarea>
      <button class="btn-primary" @click="send" :disabled="sending || !draft.trim()">发送</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { messageApi } from '../api/index.js'

const route = useRoute()
const router = useRouter()
const convId = route.params.id

const messages = ref([])
const loading = ref(true)
const draft = ref('')
const sending = ref(false)
const msgListEl = ref(null)
const otherUser = ref(null)
// 当前用户 uid：优先用后端返回的 current_uid，兜底读 localStorage
const myUid = ref('')
const otherName = computed(() => otherUser.value?.nickname || otherUser.value?.username || '未知用户')

let ws = null   // WebSocket 连接对象

function formatTime(t) {
  if (!t) return ''
  const d = new Date(t)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return d.toLocaleString('zh-CN')
}

async function loadMessages() {
  try {
    const res = await messageApi.getMessages(convId, { page: 1, page_size: 50 })
    if (res.code === 200) {
      const data = res.data?.messages || []
      // 用后端返回的当前用户 uid 判断左右（不再依赖 localStorage）
      if (res.data?.current_uid) myUid.value = res.data.current_uid
      // 会话内对方信息从任意一条消息的 sender 推导（排除自己）
      const other = data.find(m => m.sender_uid !== myUid.value)
      if (other?.sender) otherUser.value = other.sender
      messages.value = data
      scrollToBottom(false)
    }
  } catch {} finally {
    loading.value = false
  }
}

function scrollToBottom(smooth = true) {
  nextTick(() => {
    const el = msgListEl.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

async function send() {
  const content = draft.value.trim()
  if (!content || sending.value) return
  sending.value = true
  try {
    // 通过 WebSocket 发送（不再是 HTTP 接口）
    if (!ws || ws.readyState !== 1) {   // readyState===1 表示连接已就绪
      alert('连接尚未就绪，请稍后重试')
      return
    }
    ws.send(content)
    draft.value = ''
    // 不再手动 loadMessages：后端会同时给双方推信号，自己也能收到信号后刷新
  } catch {} finally {
    sending.value = false
  }
}

// ========== WebSocket 实时通讯 ==========
function connectWs() {
  const token = localStorage.getItem('access_token')
  // ws:// 协议，走 vite 代理到后端 8000
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  ws = new WebSocket(`${protocol}//${window.location.host}/ws/chat/${convId}?token=${token}`)

  // 收到服务器推送的信号（对方发了消息）
  ws.onmessage = () => {
    loadMessages()   // 方案B：收到信号就刷新消息列表
  }

  // 连接异常时回退：仍保留轮询兜底（可选，先不写）
}

onMounted(() => {
  loadMessages()   // 进来先加载历史消息
  connectWs()      // 建立 WebSocket 连接，实时收信号
})

onUnmounted(() => {
  if (ws) ws.close()   // 关页面时关闭连接（替代原来的 clearInterval）
})
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 140px);
}
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.chat-title {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.chat-avatar {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary), var(--purple));
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 600;
  color: #fff;
}
.chat-name {
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.chat-hint {
  font-size: 12px;
  color: var(--text-muted);
}
.chat-body {
  flex: 1;
  padding: 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.msg-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 4px;
  max-height: 55vh;
}
.msg-row {
  display: flex;
  justify-content: flex-start;
}
.msg-row.mine {
  justify-content: flex-end;
}
.msg-bubble {
  max-width: 70%;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 14px 14px 14px 4px;
  background: rgba(20, 30, 56, 0.6);
  box-shadow: none;
}
.msg-row.mine .msg-bubble {
  background: rgba(106, 168, 255, 0.22);
  border-color: rgba(106, 168, 255, 0.45);
  border-radius: 14px 14px 4px 14px;
}
.msg-content {
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
  white-space: pre-wrap;
}
.msg-time {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
  text-align: right;
}
.chat-input {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
.chat-input textarea {
  flex: 1;
  resize: none;
}
.chat-input button {
  align-self: flex-end;
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .msg-bubble {
    max-width: 82%;
  }
  .chat-hint {
    display: none;
  }
}
</style>

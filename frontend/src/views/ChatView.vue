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
      <span class="chat-hint" :class="{ 'chat-hint--alert': connState !== 'open' }">{{ connHint }}</span>
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

// ========== WebSocket 连接状态 ==========
let ws = null                 // 当前 WebSocket 连接对象
let reconnectTimer = null     // 重连定时器（组件卸载时必须清掉）
let reconnectAttempts = 0     // 连续失败次数，用于指数退避
let closedByUs = false        // 组件卸载时置 true，阻止 onclose 又去发起重连
let everOpened = false        // 本次挂载是否成功握手过（区分"握手失败"与"连上后又断"）
let handshakeFailures = 0     // 连续握手失败次数
const MAX_BACKOFF = 10000     // 退避上限 10 秒
const MAX_HANDSHAKE_FAILURES = 5   // 连续握手失败上限，超过就停手，避免无限重连

// connecting=首次连接中 / open=正常 / reconnecting=断线重连中 / failed=反复握手失败
// ## 为什么需要这个状态：原实现连接断了前端毫无感知，用户点发送只看到一句
// ## "连接尚未就绪"，既不知道发生了什么，也没有任何自愈动作。
const connState = ref('connecting')
const connHint = computed(() => ({
  connecting: '连接中…',
  open: '实时消息',
  reconnecting: '连接已断开，正在重连…',
  failed: '连接失败，请刷新页面重试',
}[connState.value]))

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

  // ## 为什么不再只弹一句提示：原来断线后用户只能干等，这里主动踢一次重连，
  // ## 并且不清空草稿——用户刚打的一段字不能因为连接问题白丢。
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    // 已经放弃重连了就别再踢一次，直接告诉用户刷新
    if (connState.value === 'failed') {
      alert('连接失败，请刷新页面后重试')
      return
    }
    connState.value = 'reconnecting'
    scheduleReconnect(0)          // 立即重连，不等退避
    alert('连接已断开，正在重连，请稍后再发送')
    return
  }

  sending.value = true
  try {
    // 通过 WebSocket 发送（不再是 HTTP 接口）
    ws.send(content)
    draft.value = ''              // 发成功了才清空
    // 不再手动 loadMessages：后端会同时给双方推信号，自己也能收到信号后刷新
  } catch {
    alert('发送失败，请稍后重试')   // 保留草稿，方便用户直接重发
  } finally {
    sending.value = false
  }
}

// ========== WebSocket 实时通讯 ==========
function connectWs() {
  // 已在连接中(0)或已打开(1)时不重复建连，否则同一账号会多登记一条连接
  if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) return

  // ## token 每次都重新读，不缓存在闭包里：HTTP 层刷新过 token 后，
  // ## 断线重连能自动拿到新的，不会拿着过期 token 反复撞 1008。
  const token = localStorage.getItem('access_token')
  // ws:// 协议，走 vite 代理到后端 8000
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const socket = new WebSocket(`${protocol}//${window.location.host}/ws/chat/${convId}?token=${token}`)
  ws = socket

  socket.onopen = () => {
    reconnectAttempts = 0
    everOpened = true
    handshakeFailures = 0
    connState.value = 'open'
    loadMessages()   // 断线期间对方可能发过消息，重连后补拉一次
  }

  // 收到服务器推送的信号（对方发了消息）——推送只当信号用，不解析内容（方案B）
  socket.onmessage = () => {
    loadMessages()
  }

  // onerror 之后浏览器必定还会触发 onclose，所以重连统一在 onclose 里处理，
  // 否则 error + close 会各发起一次重连，退避计数被打乱
  socket.onerror = () => {}

  socket.onclose = async (e) => {
    // 组件已卸载，或这已经是条被替换掉的旧连接 —— 都不是"该重连"的情形
    if (closedByUs || socket !== ws) return

    // ## 为什么不能靠 close code 判断鉴权失败（实测结论）：
    // ## 后端在 accept 之前调用 close(1008) 时，浏览器看到的是 **HTTP 403 握手失败**
    // ## （InvalidStatus），压根不会产生 code=1008 的 close 事件 —— 握手失败时
    // ## 浏览器只能给 1006，拿不到服务端语义。所以改按"连续失败次数"兜底。
    if (!everOpened) {
      handshakeFailures++
      if (handshakeFailures >= MAX_HANDSHAKE_FAILURES) {
        // 反复握不上（token 失效 / 服务未就绪），继续重试没意义，让用户刷新
        connState.value = 'failed'
        return
      }
    }

    // 网络中断（拔网线/切 WiFi/休眠）会走这里，close code 通常是 1006
    connState.value = 'reconnecting'
    scheduleReconnect()
  }
}

// 指数退避重连：1s → 2s → 4s → 8s → 10s 封顶，避免服务端挂掉时被高频重试压垮
function scheduleReconnect(delay) {
  if (closedByUs || reconnectTimer) return      // 已有待执行的重连就别排第二个
  const wait = delay === undefined ? Math.min(1000 * 2 ** reconnectAttempts, MAX_BACKOFF) : delay
  reconnectAttempts++
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null
    connectWs()
  }, wait)
}

onMounted(() => {
  loadMessages()   // 进来先加载历史消息
  connectWs()      // 建立 WebSocket 连接，实时收信号
})

onUnmounted(() => {
  // ## 顺序很重要：先置 closedByUs，再 close()。否则 close() 触发的 onclose
  // ## 会看到 closedByUs 还是 false，于是又排一个重连 —— 离开页面后仍偷偷连。
  closedByUs = true
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (ws) ws.close()
  ws = null
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
/* 断线/重连提示不属于装饰信息，移动端也必须能看到（见下方 media query 的例外） */
.chat-hint--alert {
  color: #f0a020;
  font-weight: 600;
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
  /* 只隐藏"实时消息"这类装饰文案，断线提示要留着 */
  .chat-hint:not(.chat-hint--alert) {
    display: none;
  }
}
</style>

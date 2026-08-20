<template>
  <article class="post-card card" @click="$router.push(`/posts/${post.id}`)">
    <div class="post-header">
      <span class="post-author">
        {{ post.author?.nickname || post.author?.username || '匿名' }}
        <span v-if="post.author" class="lv-badge">Lv.{{ post.author.level }}</span>
        <span v-if="post.author?.is_superuser" class="admin-badge">管理员</span>
      </span>
      <span class="post-time">{{ formatTime(post.created_time) }}</span>
    </div>
    <h3 class="post-title">{{ post.title }}</h3>
    <p class="post-summary">{{ post.summary || post.content?.slice(0, 120) }}</p>
    <div class="post-meta">
      <span v-if="post.category" class="tag">{{ post.category.name }}</span>
      <span>{{ post.view_count || 0 }} 次浏览</span>
      <span v-if="post.like_count !== undefined">{{ post.like_count }} 赞</span>
      <span v-if="post.comment_count !== undefined">{{ post.comment_count }} 评论</span>
    </div>
    <button
      v-if="canReport"
      class="report-btn"
      @click.stop="handleReport"
      :disabled="reporting"
      title="举报"
    >{{ reporting ? 'AI 审核中...' : '举报' }}</button>
  </article>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { postApi, userApi } from '../api/index.js'

const props = defineProps({
  post: { type: Object, required: true },
})

const router = useRouter()
const currentUser = ref(JSON.parse(localStorage.getItem('user_info') || '{}'))
const isLoggedIn = ref(!!localStorage.getItem('access_token'))
const reporting = ref(false)

// 异步刷新当前用户信息，防止账号切换后 localStorage 残留导致按钮误判
onMounted(async () => {
  if (!isLoggedIn.value) return
  try {
    const res = await userApi.getCurrentUser()
    if (res.code === 200 && res.data) {
      currentUser.value = res.data
      localStorage.setItem('user_info', JSON.stringify(res.data))
    }
  } catch {}
})

// 可以举报：已登录、不是自己的帖子、不是管理员
const canReport = computed(() => {
  if (!isLoggedIn.value) return false
  if (currentUser.value.is_superuser) return false
  if (String(currentUser.value.uid ?? '') === String(props.post.author_uid ?? '')) return false
  return true
})

async function handleReport() {
  if (!confirm('确定要举报该帖子吗？举报后将由 AI 自动审核内容')) return
  reporting.value = true
  try {
    const res = await postApi.report(props.post.id)
    if (res.code === 200) {
      // 展示 AI 审核结果
      const data = res.data || {}
      if (data.violated) {
        alert(`AI 审核判定违规（${data.type || '违规'}）：${data.reason || ''}\n帖子已被删除`)
        router.push('/posts')
      } else {
        alert('AI 审核未发现违规内容，帖子已保留')
      }
    } else {
      alert(res.message || res.detail || '举报失败')
    }
  } catch {
    alert('举报失败，请稍后重试')
  } finally {
    reporting.value = false
  }
}

function formatTime(t) {
  if (!t) return ''
  const d = new Date(t)
  const now = new Date()
  const diff = now - d
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return d.toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.post-card {
  margin-bottom: 12px;
  cursor: pointer;
  position: relative;
  transition: box-shadow 0.3s ease, transform 0.3s ease;
}
.post-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.post-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
  gap: 4px;
}
.post-author {
  font-weight: 600;
  transition: color 0.2s ease;
}
.post-card:hover .post-author {
  color: var(--primary);
}
.post-title {
  font-size: 17px;
  font-weight: 600;
  margin-bottom: 6px;
  line-height: 1.4;
  transition: color 0.2s ease;
}
.post-card:hover .post-title {
  color: var(--primary);
}
.post-summary {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 12px;
  word-break: break-word;
}
.post-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: var(--text-muted);
}
.tag {
  background: var(--primary-light);
  color: var(--primary);
  padding: 2px 9px;
  border: 1px solid rgba(106, 168, 255, 0.4);
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  transition: background 0.2s ease, color 0.2s ease;
}
.post-card:hover .tag {
  background: rgba(106, 168, 255, 0.3);
}
.report-btn {
  position: absolute;
  bottom: 12px;
  right: 12px;
  font-size: 12px;
  padding: 1px 8px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: transparent;
  color: var(--text-muted);
  box-shadow: none;
  cursor: pointer;
  transition: color 0.2s ease, border-color 0.2s ease;
  z-index: 1;
}
.report-btn:hover {
  color: var(--danger);
  border-color: var(--danger);
  transform: none;
}

@media (max-width: 768px) {
  .post-title {
    font-size: 15px;
  }
  .post-summary {
    font-size: 13px;
  }
  .post-meta {
    gap: 8px;
  }
}
</style>

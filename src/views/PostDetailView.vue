<template>
  <div v-if="loading" class="skeleton-list">
    <div class="skeleton-card">
      <div class="skeleton skeleton-title" style="width:75%"></div>
      <div class="skeleton-meta">
        <div class="skeleton skeleton-text" style="width:80px"></div>
        <div class="skeleton skeleton-text" style="width:100px"></div>
      </div>
      <div class="skeleton skeleton-text"></div>
      <div class="skeleton skeleton-text"></div>
      <div class="skeleton skeleton-text"></div>
      <div class="skeleton skeleton-text"></div>
    </div>
  </div>
  <div v-else-if="!post" class="empty-state"><p>帖子不存在</p></div>
  <div v-else>
    <!-- 帖子详情 -->
    <article class="card">
      <h1 style="font-size:22px;margin-bottom:8px">{{ post.title }}</h1>
      <div class="meta">
        <span>作者：{{ post.author?.nickname || post.author?.username || '匿名' }}
          <span v-if="post.author" class="lv-badge">Lv.{{ post.author.level }}</span>
          <span v-if="post.author?.is_superuser" class="admin-badge">管理员</span>
        </span>
        <span>{{ formatTime(post.created_time) }}</span>
      </div>
      <div class="content" style="margin:16px 0;white-space:pre-wrap;line-height:1.8">{{ post.content }}</div>

      <div class="actions">
        <button class="btn-outline btn-sm" @click="toggleLike" :class="{ liked: isLiked, 'like-pop': likeAnimating }">
          {{ isLiked ? '已赞' : '点赞' }} ({{ likeCount }})
        </button>
        <button class="btn-outline btn-sm" @click="toggleBookmark" :class="{ bookmarked: isBookmarked, 'like-pop': bookmarkAnimating }">
          {{ isBookmarked ? '已收藏' : '收藏' }}
        </button>
        <button v-if="isAuthor" class="btn-danger btn-sm" @click="handleDelete">删除</button>
        <button v-if="canReport" class="btn-outline btn-sm report-action-btn" @click="handleReport" :disabled="reporting">
          {{ reporting ? 'AI 审核中...' : '举报' }}
        </button>
      </div>
    </article>

    <!-- 评论 -->
    <div style="margin-top:24px">
      <h3 style="font-size:16px;margin-bottom:12px">评论 ({{ totalComments }})</h3>

      <!-- 写评论 -->
      <div v-if="isLoggedIn" class="card" style="margin-bottom:16px">
        <textarea v-model="newComment" rows="3" placeholder="写下你的评论..." style="resize:vertical"></textarea>
        <div style="margin-top:8px;display:flex;justify-content:flex-end">
          <button class="btn-primary btn-sm" @click="submitComment" :disabled="!newComment.trim()">发表评论</button>
        </div>
      </div>

      <div v-if="comments.length === 0" class="empty-state"><p>暂无评论</p></div>
      <div v-else>
        <div v-for="comment in comments" :key="comment.id" class="comment-item card">
          <div class="comment-header">
            <strong>{{ comment.author?.nickname || comment.author?.username || '匿名' }}
              <span v-if="comment.author" class="lv-badge">Lv.{{ comment.author.level }}</span>
              <span v-if="comment.author?.is_superuser" class="admin-badge">管理员</span>
            </strong>
            <span class="comment-time">{{ formatTime(comment.created_time) }}</span>
          </div>
          <div class="comment-content">{{ comment.content }}</div>
          <button class="btn-outline btn-sm" @click="replyTo = replyTo === comment.id ? null : comment.id">
            {{ replyTo === comment.id ? '取消回复' : '回复' }}
          </button>
          <button v-if="canDeleteComment(comment)" class="btn-danger btn-sm" @click="deleteComment(comment.id)">删除</button>

          <!-- 回复输入 -->
          <div v-if="replyTo === comment.id" style="margin-top:8px">
            <textarea v-model="replyContent" rows="2" placeholder="回复 {{ comment.author?.nickname }}..." style="resize:vertical"></textarea>
            <button class="btn-primary btn-sm" style="margin-top:4px" @click="submitReply(comment.id)">回复</button>
          </div>

          <!-- 楼中楼回复 -->
          <div v-if="comment.replies && comment.replies.length > 0" class="replies">
            <div v-for="reply in comment.replies" :key="reply.id" class="reply-item">
              <div class="comment-header">
                <strong>{{ reply.author?.nickname || reply.author?.username || '匿名' }}
                  <span v-if="reply.author" class="lv-badge">Lv.{{ reply.author.level }}</span>
                  <span v-if="reply.author?.is_superuser" class="admin-badge">管理员</span>
                </strong>
                <span class="comment-time">{{ formatTime(reply.created_time) }}</span>
              </div>
              <div class="comment-content">{{ reply.content }}</div>
              <button v-if="canDeleteComment(reply)" class="btn-danger btn-sm" @click="deleteComment(reply.id)">删除</button>
            </div>
          </div>
        </div>

        <!-- 分页 -->
        <div class="pagination" v-if="totalComments > pageSize">
          <button class="btn-outline btn-sm" :disabled="commentPage <= 1" @click="loadComments(commentPage - 1)">上一页</button>
          <span style="font-size:13px;color:var(--text-secondary)">第 {{ commentPage }} / {{ Math.ceil(totalComments / pageSize) }} 页</span>
          <button class="btn-outline btn-sm" :disabled="commentPage * pageSize >= totalComments" @click="loadComments(commentPage + 1)">下一页</button>
        </div>
      </div>
    </div>
  </div>

</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { postApi, commentApi, likeApi, bookmarkApi, userApi } from '../api/index.js'

const route = useRoute()
const router = useRouter()
const postId = computed(() => Number(route.params.id))

const post = ref(null)
const loading = ref(true)
const isLiked = ref(false)
const likeCount = ref(0)
const isBookmarked = ref(false)
const isLoggedIn = ref(!!localStorage.getItem('access_token'))
const currentUser = ref(JSON.parse(localStorage.getItem('user_info') || '{}'))
// 本人或管理员 → 显示删除；uid 统一转字符串比较，避免数字/字符串类型误判
const isAuthor = computed(() =>
  String(currentUser.value?.uid ?? '') === String(post.value?.author_uid ?? '') || !!currentUser.value?.is_superuser
)

// 举报权限：已登录、非作者、非管理员 → 显示举报按钮（召唤 AI 审核）
const canReport = computed(() => {
  if (!isLoggedIn.value) return false
  if (currentUser.value?.is_superuser) return false
  if (String(currentUser.value?.uid ?? '') === String(post.value?.author_uid ?? '')) return false
  return true
})

// AI 审核状态
const reporting = ref(false)

// 动画状态
const likeAnimating = ref(false)
const bookmarkAnimating = ref(false)

// 评论
const comments = ref([])
const totalComments = ref(0)
const commentPage = ref(1)
const pageSize = 10
const newComment = ref('')
const replyTo = ref(null)
const replyContent = ref('')

function formatTime(t) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN')
}

function canDeleteComment(comment) {
  return currentUser.value?.uid === comment.author_uid || currentUser.value?.is_superuser
}

async function loadPost() {
  loading.value = true
  try {
    const res = await postApi.getDetail(postId.value)
    if (res.code === 200) post.value = res.data
  } catch {} finally {
    loading.value = false
  }
}

async function loadLikeStatus() {
  // 点赞数：公开信息，不管是否登录都加载
  try {
    const countRes = await likeApi.count(postId.value)
    if (countRes.code === 200) likeCount.value = countRes.data.count
  } catch {}
  // 当前用户的点赞状态：仅登录后查询
  if (!isLoggedIn.value) return
  try {
    const res = await likeApi.check(postId.value)
    if (res.code === 200) isLiked.value = res.data.liked
  } catch {}
}

async function loadBookmarkStatus() {
  if (!isLoggedIn.value) return
  try {
    const res = await bookmarkApi.getMy()
    if (res.code === 200) {
      isBookmarked.value = (res.data || []).some(b => b.post_id === postId.value)
    }
  } catch {}
}

async function toggleLike() {
  try {
    const res = await likeApi.toggle(postId.value)
    if (res.code === 200) {
      isLiked.value = res.data.liked
      likeCount.value += res.data.liked ? 1 : -1
      likeAnimating.value = true
      setTimeout(() => { likeAnimating.value = false }, 400)
    }
  } catch {}
}

async function toggleBookmark() {
  try {
    const res = await bookmarkApi.toggle(postId.value)
    if (res.code === 200) {
      isBookmarked.value = res.data.bookmarked
      bookmarkAnimating.value = true
      setTimeout(() => { bookmarkAnimating.value = false }, 400)
    }
  } catch {}
}

async function handleDelete() {
  if (!confirm('确定删除此帖子？')) return
  try {
    const res = await postApi.delete(postId.value)
    if (res.code === 200) {
      router.push('/posts')
    } else {
      alert(res.message || res.detail || '删除失败')
    }
  } catch {
    alert('删除失败，请稍后重试')
  }
}

async function handleReport() {
  if (!confirm('确定要举报该帖子吗？举报后将由 AI 自动审核内容')) return
  reporting.value = true
  try {
    const res = await postApi.report(postId.value)
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

// 评论相关
async function loadComments(page = 1) {
  commentPage.value = page
  try {
    const res = await commentApi.getList(postId.value, { page, page_size: pageSize })
    if (res.code === 200) {
      comments.value = res.data || []
      totalComments.value = res.total || 0
    }
  } catch {}
}

async function submitComment() {
  if (!newComment.value.trim()) return
  try {
    const res = await commentApi.add(postId.value, { content: newComment.value })
    if (res.code === 200) {
      newComment.value = ''
      loadComments(1)
    }
  } catch {}
}

async function submitReply(parentId) {
  if (!replyContent.value.trim()) return
  try {
    await commentApi.add(postId.value, { content: replyContent.value, parent_id: parentId })
    replyContent.value = ''
    replyTo.value = null
    loadComments(commentPage.value)
  } catch {}
}

async function deleteComment(commentId) {
  if (!confirm('确定删除此评论？')) return
  try {
    await commentApi.delete(commentId)
    loadComments(commentPage.value)
  } catch {}
}

// 关键：从后端拉取真实用户信息覆盖 localStorage，防止账号切换后残留
// 旧 user_info（含错误的 is_superuser）导致删除按钮误显示
async function refreshCurrentUser() {
  if (!isLoggedIn.value) return
  try {
    const res = await userApi.getCurrentUser()
    if (res.code === 200 && res.data) {
      currentUser.value = res.data
      localStorage.setItem('user_info', JSON.stringify(res.data))
    }
  } catch {}
}

onMounted(() => {
  refreshCurrentUser()
  loadPost()
  loadComments()
  loadLikeStatus()
  loadBookmarkStatus()
})
</script>

<style scoped>
.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.skeleton-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.skeleton-meta .skeleton-text { width: 80px; margin-bottom: 0; }
.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 13px;
  color: var(--text-secondary);
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  border-top: 1px solid var(--border);
  padding-top: 12px;
}
.liked {
  background: var(--primary-light);
  color: var(--primary);
  border-color: var(--primary);
}
.bookmarked {
  color: var(--warning);
}
.report-action-btn {
  color: var(--text-muted);
}
.report-action-btn:hover {
  color: var(--danger);
  border-color: var(--danger);
}
.comment-item {
  margin-bottom: 12px;
}
.comment-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  font-size: 13px;
  margin-bottom: 6px;
}
.comment-header strong {
  font-size: 14px;
}
.comment-time {
  color: var(--text-muted);
}
.comment-content {
  margin-bottom: 8px;
  white-space: pre-wrap;
  line-height: 1.6;
  word-break: break-word;
}
.replies {
  margin-left: 24px;
  margin-top: 12px;
  border-left: 2px solid var(--border);
  padding-left: 16px;
}
.reply-item {
  margin-bottom: 12px;
}
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 16px;
}

@media (max-width: 768px) {
  .meta {
    font-size: 12px;
    gap: 8px;
  }
  .actions {
    gap: 6px;
    padding-top: 10px;
  }
  .replies {
    margin-left: 12px;
    padding-left: 10px;
  }
  .pagination {
    gap: 10px;
    margin-top: 12px;
  }
}
</style>

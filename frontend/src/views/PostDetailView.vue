<template>
  <div v-if="loading" class="loading">加载中...</div>
  <div v-else-if="!post" class="empty-state"><p>帖子不存在</p></div>
  <div v-else>
    <!-- 帖子详情 -->
    <article class="card">
      <h1 style="font-size:22px;margin-bottom:8px">{{ post.title }}</h1>
      <div class="meta">
        <span>作者：{{ post.author?.nickname || post.author?.username || '匿名' }}</span>
        <span>{{ formatTime(post.created_time) }}</span>
        <span v-if="post.updated_time !== post.created_time">（编辑于 {{ formatTime(post.updated_time) }}）</span>
      </div>
      <div class="content" style="margin:16px 0;white-space:pre-wrap;line-height:1.8">{{ post.content }}</div>
      <div class="actions">
        <button class="btn-outline btn-sm" @click="toggleLike" :class="{ liked: isLiked }">
          {{ isLiked ? '已赞' : '点赞' }} ({{ likeCount }})
        </button>
        <button class="btn-outline btn-sm" @click="toggleBookmark" :class="{ bookmarked: isBookmarked }">
          {{ isBookmarked ? '已收藏' : '收藏' }}
        </button>
        <button v-if="isAuthor" class="btn-danger btn-sm" @click="handleDelete">删除</button>
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
            <strong>{{ comment.author?.nickname || comment.author?.username || '匿名' }}</strong>
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
                <strong>{{ reply.author?.nickname || reply.author?.username || '匿名' }}</strong>
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
import { postApi, commentApi, likeApi, bookmarkApi } from '../api/index.js'

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
const isAuthor = computed(() => currentUser.value?.uid === post.value?.author_uid)

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
  return currentUser.value?.uid === comment.author_uid
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
  if (!isLoggedIn.value) return
  try {
    const [likeRes, bookmarkRes] = await Promise.all([
      likeApi.check(postId.value),
      likeApi.count(postId.value),
    ])
    if (likeRes.code === 200) isLiked.value = likeRes.data.liked
    if (bookmarkRes.code === 200) likeCount.value = bookmarkRes.data.count
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
    }
  } catch {}
}

async function toggleBookmark() {
  try {
    const res = await bookmarkApi.toggle(postId.value)
    if (res.code === 200) isBookmarked.value = res.data.bookmarked
  } catch {}
}

async function handleDelete() {
  if (!confirm('确定删除此帖子？')) return
  try {
    await postApi.delete(postId.value)
    router.push('/posts')
  } catch {}
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

onMounted(() => {
  loadPost()
  loadComments()
  loadLikeStatus()
  loadBookmarkStatus()
})
</script>

<style scoped>
.meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: var(--text-secondary);
}
.actions {
  display: flex;
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
.comment-item {
  margin-bottom: 12px;
}
.comment-header {
  display: flex;
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
</style>

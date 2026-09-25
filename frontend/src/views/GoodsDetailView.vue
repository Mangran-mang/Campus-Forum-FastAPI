<template>
  <div>
  <div v-if="loading" class="skeleton-list">
    <div class="skeleton-card">
      <div style="display:flex;gap:24px">
        <div class="skeleton" style="width:240px;height:240px;border-radius:8px;flex-shrink:0"></div>
        <div style="flex:1">
          <div class="skeleton skeleton-title" style="width:60%"></div>
          <div class="skeleton" style="width:100px;height:32px;border-radius:6px;margin-bottom:16px"></div>
          <div class="skeleton skeleton-text" style="width:80px"></div>
          <div class="skeleton skeleton-text"></div>
          <div class="skeleton skeleton-text"></div>
        </div>
      </div>
    </div>
  </div>
  <div v-else-if="!goods" class="empty-state"><p>商品不存在或已下架</p></div>
  <div v-else>
    <p v-if="pageError" class="error-msg" style="margin-bottom:8px">{{ pageError }}</p>
    <article class="card goods-detail">
      <!-- 商品图片 -->
      <div v-if="images.length > 0" class="goods-images">
        <img
          :src="imgPath(mainImage)"
          alt=""
          class="goods-main-img"
          @click="lightbox = imgPath(mainImage)"
        />
        <div class="goods-thumb-strip" v-if="images.length > 1">
          <img
            v-for="img in images"
            :key="img.id"
            :src="imgPath(img)"
            alt=""
            class="goods-thumb"
            :class="{ active: mainImage.id === img.id }"
            @click="mainImage = img"
          />
        </div>
      </div>
      <div v-else class="goods-image-placeholder">
        <span>暂无图片</span>
      </div>

      <div class="goods-info">
        <h1 class="goods-name">{{ goods.name }}</h1>
        <div class="goods-price">&yen;{{ formatPrice(goods.price) }}</div>

        <div class="goods-tags">
          <span class="tag" v-if="goods.classify_rel">{{ goods.classify_rel.name }}</span>
          <span class="status-badge" :class="goods.status === '在售' ? 'status-on' : 'status-off'">
            {{ goods.status }}
          </span>
        </div>

        <div class="goods-meta">
          <div class="meta-row">
            <span class="meta-label">发布者</span>
            <span>{{ goods.author?.nickname || goods.author?.username || goods.author_uid?.slice(0,8) || '匿名' }}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">发布时间</span>
            <span>{{ formatTime(goods.created_time) }}</span>
          </div>
          <div class="meta-row" v-if="goods.update_time !== goods.created_time">
            <span class="meta-label">更新时间</span>
            <span>{{ formatTime(goods.update_time) }}</span>
          </div>
        </div>

        <div class="goods-actions" v-if="isAuthor">
          <router-link :to="`/goods/${goods.gid}/edit`" class="btn-outline btn-sm">编辑</router-link>
          <button class="btn-danger btn-sm" @click="handleDelete">删除</button>
          <button class="btn-outline btn-sm" v-if="goods.status === '在售'" @click="toggleStatus">
            标记为已售出
          </button>
          <button class="btn-outline btn-sm" v-else @click="toggleStatus">
            重新上架
          </button>
        </div>
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

    <!-- 返回按钮 -->
    <div style="margin-top:16px">
      <button class="btn-outline" @click="$router.push('/goods')">← 返回列表</button>
    </div>
  </div>

  <!-- 灯箱 -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="lightbox" class="lightbox-overlay" @click="lightbox = null">
        <img :src="lightbox" alt="" class="lightbox-img" @click.stop />
      </div>
    </Transition>
  </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { goodsApi, goodsCommentApi, imageApi } from '../api/index.js'
import { pickErrorMessage } from '../utils/errorMessage.js'

const route = useRoute()
const router = useRouter()
const gid = computed(() => route.params.gid)

const goods = ref(null)
const loading = ref(true)
const currentUser = ref(JSON.parse(localStorage.getItem('user_info') || '{}'))
const isAuthor = computed(() =>
  currentUser.value?.uid === goods.value?.author_uid || currentUser.value?.is_superuser
)
const isLoggedIn = ref(!!localStorage.getItem('access_token'))
const lightbox = ref(null)

// 图片
const images = ref([])
const mainImage = ref(null)

// 评论
const comments = ref([])
const totalComments = ref(0)
const commentPage = ref(1)
const pageSize = 10
const newComment = ref('')
const replyTo = ref(null)
const replyContent = ref('')

// 页面级错误提示：本文件原先从加载商品到发评论、改状态、删评论，一共 8 处 `catch {}`，
// 任何一步失败页面都**毫无反应**——用户只会觉得"点了没生效"然后反复点。
// 静默失败比报错更难排查：用户甚至没法告诉你"控制台报了个 500"。
// 所以这里统一收口，失败时至少说清是哪一步出的问题。
const pageError = ref('')

function canDeleteComment(comment) {
  return currentUser.value?.uid === comment.author_uid || currentUser.value?.is_superuser
}

function formatTime(t) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN')
}

function formatPrice(val) {
  if (val == null) return '0.00'
  return Number(val).toFixed(2)
}

function imgPath(img) {
  if (!img || !img.filename) return ''
  const type = img.target_type || 'goods'
  return `/uploads/${type}/${img.filename}`
}

async function loadGoods() {
  loading.value = true
  pageError.value = ''
  try {
    const res = await goodsApi.getDetail(gid.value)
    if (res.code === 200) {
      goods.value = res.data
    } else if (res && !res.code) {
      // 直接返回了对象
      goods.value = res
    } else {
      pageError.value = pickErrorMessage(res, '商品加载失败')
    }
  } catch {
    pageError.value = '商品加载失败，请检查网络后刷新重试'
  } finally {
    loading.value = false
  }
}

async function handleDelete() {
  if (!confirm('确定删除此商品？')) return
  pageError.value = ''
  try {
    const res = await goodsApi.delete(gid.value)
    // ## 为什么这里要检查 res.code
    // 原来是拿到响应就无脑 router.push，删失败（比如 403 无权、404 已不存在）
    // 也会跳走，用户以为删掉了，回头看列表东西还在——最迷惑的一类 bug。
    // 得先确认服务端真的删了再离开这个页面。
    if (res && res.code !== 200) {
      pageError.value = pickErrorMessage(res, '删除失败，请稍后重试')
      return
    }
    router.push('/goods')
  } catch {
    pageError.value = '删除失败，请检查网络后重试'
  }
}

async function toggleStatus() {
  const newStatus = goods.value.status === '在售' ? '已售出' : '在售'
  pageError.value = ''
  try {
    const res = await goodsApi.update(gid.value, {
      name: goods.value.name,
      classify: goods.value.classify_rel?.name || goods.value.classify,
      status: newStatus,
      price: Number(goods.value.price),
    })
    // 同样要确认服务端改成功了再动本地状态，否则界面显示"已售出"、
    // 数据库里还是"在售"，刷新一下就穿帮
    if (res && res.code !== 200) {
      pageError.value = pickErrorMessage(res, `改为「${newStatus}」失败`)
      return
    }
    goods.value.status = newStatus
  } catch {
    pageError.value = '修改商品状态失败，请检查网络后重试'
  }
}

// 评论相关
async function loadComments(page = 1) {
  commentPage.value = page
  try {
    const res = await goodsCommentApi.getList(gid.value, { page, page_size: pageSize })
    if (res.code === 200) {
      // 字段名从 list 统一成 comments（与帖子评论接口保持一致）
      comments.value = res.data?.comments || []
      totalComments.value = res.data?.total || 0
    } else {
      pageError.value = pickErrorMessage(res, '评论加载失败')
    }
  } catch {
    pageError.value = '评论加载失败，请检查网络后重试'
  }
}

async function submitComment() {
  if (!newComment.value.trim()) return
  pageError.value = ''
  try {
    const res = await goodsCommentApi.add(gid.value, { content: newComment.value })
    if (res.code === 200) {
      newComment.value = ''
      loadComments(1)
    } else {
      // 不清空输入框：失败时把用户刚打的内容留着，否则白打一遍
      pageError.value = pickErrorMessage(res, '评论发布失败，请稍后重试')
    }
  } catch {
    pageError.value = '评论发布失败，请检查网络后重试（内容已保留）'
  }
}

async function submitReply(parentId) {
  if (!replyContent.value.trim()) return
  pageError.value = ''
  try {
    const res = await goodsCommentApi.add(gid.value, { content: replyContent.value, parent_id: parentId })
    if (res && res.code !== 200) {
      pageError.value = pickErrorMessage(res, '回复失败，请稍后重试')
      return
    }
    replyContent.value = ''
    replyTo.value = null
    loadComments(commentPage.value)
  } catch {
    pageError.value = '回复失败，请检查网络后重试（内容已保留）'
  }
}

async function deleteComment(commentId) {
  if (!confirm('确定删除此评论？')) return
  pageError.value = ''
  try {
    const res = await goodsCommentApi.delete(commentId)
    // 失败还去刷新列表的话，会让人以为"删了但没刷新出来"，实际是根本没删掉
    if (res && res.code !== 200) {
      pageError.value = pickErrorMessage(res, '删除评论失败')
      return
    }
    loadComments(commentPage.value)
  } catch {
    pageError.value = '删除评论失败，请检查网络后重试'
  }
}

async function loadImages() {
  try {
    const res = await imageApi.getList('goods', gid.value)
    if (res.code === 200 && (res.data || []).length > 0) {
      images.value = res.data
      mainImage.value = res.data[0]
    }
  } catch (e) {
    // 图片挂了不该盖住商品信息本身 —— 只记控制台，页面上仍显示"暂无图片"
    console.warn('商品图片加载失败', e)
  }
}

onMounted(() => {
  loadGoods()
  loadComments()
  loadImages()
})
</script>

<style scoped>
.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.goods-detail {
  display: flex;
  gap: 24px;
}
.goods-image-placeholder {
  width: 240px;
  height: 240px;
  background: rgba(17, 26, 48, 0.45);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 14px;
  flex-shrink: 0;
}
.goods-images {
  flex-shrink: 0;
  width: 240px;
}
.goods-main-img {
  width: 240px;
  height: 240px;
  object-fit: cover;
  border-radius: var(--radius);
  cursor: pointer;
  border: 1px solid var(--border);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.goods-main-img:hover {
  transform: scale(1.03);
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
}
.goods-thumb-strip {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}
.goods-thumb {
  width: 50px;
  height: 50px;
  object-fit: cover;
  border-radius: 4px;
  cursor: pointer;
  border: 2px solid transparent;
  transition: border-color 0.15s;
}
.goods-thumb.active {
  border-color: var(--primary);
}
.goods-thumb:hover {
  border-color: var(--border-hover);
}
.lightbox-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}
.lightbox-img {
  max-width: 90vw;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 4px;
}
.goods-info {
  flex: 1;
  min-width: 0;
}
.goods-name {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 8px;
  word-break: break-word;
}
.goods-price {
  font-size: 28px;
  font-weight: 700;
  color: var(--danger);
  margin-bottom: 16px;
}
.goods-tags {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}
.tag {
  background: var(--primary-light);
  color: var(--primary);
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 13px;
}
.status-badge {
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
}
.status-on {
  background: rgba(61, 220, 151, 0.14);
  color: #4fe3a4;
  border: 1px solid rgba(61, 220, 151, 0.4);
}
.status-off {
  background: rgba(255, 184, 107, 0.14);
  color: #ffb86b;
  border: 1px solid rgba(255, 184, 107, 0.4);
}
.goods-meta {
  border-top: 1px solid var(--border);
  padding-top: 16px;
  margin-bottom: 20px;
}
.meta-row {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
  font-size: 14px;
}
.meta-label {
  color: var(--text-secondary);
  min-width: 56px;
}
.goods-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  border-top: 1px solid var(--border);
  padding-top: 16px;
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
  .goods-detail {
    flex-direction: column;
    gap: 16px;
  }
  .goods-image-placeholder {
    width: 100%;
    height: 200px;
  }
  .goods-images {
    width: 100%;
  }
  .goods-main-img {
    width: 100%;
    height: 220px;
  }
  .goods-name {
    font-size: 18px;
  }
  .goods-price {
    font-size: 24px;
  }
  .goods-actions {
    gap: 6px;
    padding-top: 12px;
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

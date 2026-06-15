<template>
  <article class="post-card card" @click="$router.push(`/posts/${post.id}`)">
    <div class="post-header">
      <span class="post-author">{{ post.author?.nickname || post.author?.username || '匿名' }}</span>
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
  </article>
</template>

<script setup>
defineProps({
  post: { type: Object, required: true },
})

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
  transition: box-shadow 0.2s;
}
.post-card:hover {
  box-shadow: var(--shadow-md);
}
.post-header {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}
.post-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 6px;
  line-height: 1.4;
}
.post-summary {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 12px;
}
.post-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--text-muted);
}
.tag {
  background: var(--primary-light);
  color: var(--primary);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}
</style>

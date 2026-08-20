<template>
  <article class="goods-card card" @click="$router.push(`/goods/${goods.gid}`)">
    <div class="goods-left">
      <h3 class="goods-name">{{ goods.name }}</h3>
      <div class="goods-meta">
        <span class="tag" v-if="goods.classify_rel">{{ goods.classify_rel.name }}</span>
        <span v-else class="tag tag--default">未分类</span>
        <span class="status-badge" :class="goods.status === '在售' ? 'status-on' : 'status-off'">
          {{ goods.status }}
        </span>
      </div>
      <div class="goods-footer">
        <span class="goods-author">{{ goods.author?.nickname || goods.author?.username || goods.author_uid?.slice(0,8) || '匿名' }}</span>
        <span class="goods-time">{{ formatTime(goods.update_time) }}</span>
      </div>
    </div>
    <div class="goods-right">
      <span class="goods-price">&yen;{{ formatPrice(goods.price) }}</span>
    </div>
  </article>
</template>

<script setup>
import { defineProps } from 'vue'

defineProps({
  goods: { type: Object, required: true },
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

function formatPrice(val) {
  if (val == null) return '0.00'
  return Number(val).toFixed(2)
}
</script>

<style scoped>
.goods-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  cursor: pointer;
  position: relative;
  transition: box-shadow 0.3s ease, transform 0.3s ease;
}
.goods-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.goods-left {
  flex: 1;
  min-width: 0;
}
.goods-name {
  font-size: 17px;
  font-weight: 600;
  margin-bottom: 8px;
  line-height: 1.4;
  word-break: break-word;
  transition: color 0.2s ease;
}
.goods-card:hover .goods-name {
  color: var(--primary);
}
.goods-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
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
.goods-card:hover .tag {
  background: rgba(106, 168, 255, 0.3);
}
.tag--default {
  background: rgba(130, 165, 230, 0.08);
  color: var(--text-muted);
  border-color: var(--border);
}
.status-badge {
  padding: 2px 9px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
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
.goods-footer {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-muted);
  gap: 4px;
}
.goods-right {
  flex-shrink: 0;
  margin-left: 16px;
}
.goods-price {
  font-size: 20px;
  font-weight: 700;
  color: var(--danger);
  white-space: nowrap;
  transition: transform 0.3s ease;
  display: inline-block;
}
.goods-card:hover .goods-price {
  transform: scale(1.05);
}

@media (max-width: 768px) {
  .goods-name {
    font-size: 15px;
  }
  .goods-price {
    font-size: 18px;
  }
}
</style>

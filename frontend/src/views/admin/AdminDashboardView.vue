<template>
  <div class="admin-page">
    <h3 class="admin-title">数据看板</h3>

    <p v-if="error" class="error-msg">{{ error }}</p>
    <p v-else-if="!data" class="admin-loading">加载中...</p>

    <div v-else class="dash-cards">
      <div v-for="item in cards" :key="item.key" class="card dash-card">
        <span class="dash-label">{{ item.label }}</span>
        <span class="dash-value">{{ item.total }}</span>
        <span class="dash-today" :class="{ 'is-zero': item.today === 0 }">
          今日新增 {{ item.today }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { adminApi } from '../../api/index.js'
import { pickErrorMessage } from '../../utils/errorMessage.js'

const data = ref(null)
const error = ref('')

// 卡片顺序 = 运营视角的优先级：人 → 内容 → 交易
const cards = computed(() => {
  if (!data.value) return []
  const d = data.value
  return [
    { key: 'user', label: '用户总数', total: d.user_total, today: d.user_today },
    { key: 'post', label: '帖子总数', total: d.post_total, today: d.post_today },
    { key: 'goods', label: '商品总数', total: d.goods_total, today: d.goods_today },
  ]
})

onMounted(async () => {
  try {
    const res = await adminApi.getOverview()
    if (res.code === 200) {
      data.value = res.data
    } else {
      error.value = pickErrorMessage(res, '加载失败')
    }
  } catch (e) {
    // adminRequest 遇到 401/403 时已清会话并跳登录页，这里只兜底文案
    error.value = '加载失败，请重新登录后再试'
  }
})
</script>

<style scoped>
.admin-page {
  max-width: 1100px;
}
.admin-title {
  margin-bottom: 16px;
  font-size: 18px;
}
.admin-loading {
  color: var(--text-muted);
  font-size: 14px;
}
.dash-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
.dash-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 20px;
}
.dash-label {
  font-size: 13px;
  color: var(--text-secondary);
}
.dash-value {
  font-size: 32px;
  font-weight: 600;
  line-height: 1.1;
  color: var(--text);
}
.dash-today {
  font-size: 12px;
  color: var(--primary);
}
/* 今日 0 新增时弱化，避免"全是 0"看起来像坏了 */
.dash-today.is-zero {
  color: var(--text-muted);
}
@media (max-width: 900px) {
  .dash-cards {
    grid-template-columns: 1fr;
  }
}
</style>

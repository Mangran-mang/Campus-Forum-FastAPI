<template>
  <div>
    <div class="flex-between mb-16">
      <h2 style="font-size:20px">二手交易</h2>
      <div class="flex-between gap-8">
        <select v-model="filterClassify" class="classify-select">
          <option value="">全部分类</option>
          <option v-for="c in classifyList" :key="c" :value="c">{{ c }}</option>
        </select>
        <router-link to="/goods/create" class="btn-primary" v-if="isLoggedIn">发布商品</router-link>
      </div>
    </div>

    <div v-if="loading" class="skeleton-list">
      <div class="skeleton-card" v-for="i in 3" :key="i">
        <div class="skeleton-row">
          <div style="flex:1">
            <div class="skeleton skeleton-title"></div>
            <div class="skeleton skeleton-text" style="width:80px"></div>
            <div class="skeleton skeleton-text" style="width:120px;height:10px"></div>
          </div>
          <div class="skeleton" style="width:72px;height:28px;border-radius:6px"></div>
        </div>
      </div>
    </div>
    <div v-else-if="filteredGoods.length === 0" class="empty-state">
      <p v-if="goods.length === 0">暂无商品</p>
      <p v-else>没有找到符合条件的商品</p>
      <p style="font-size:13px;margin-top:8px">快来发布第一件二手宝贝吧</p>
    </div>
    <template v-else>
      <div class="goods-list">
        <GoodsCard v-for="(item, idx) in pagedGoods" :key="item.gid" :goods="item" :style="{ animationDelay: idx * 0.05 + 's' }" class="stagger-item" />
      </div>

      <div class="pagination" v-if="totalPages > 1">
        <button class="btn-outline btn-sm" :disabled="page <= 1" @click="page--">上一页</button>
        <span style="font-size:13px;color:var(--text-secondary)">第 {{ page }} / {{ totalPages }} 页</span>
        <button class="btn-outline btn-sm" :disabled="page >= totalPages" @click="page++">下一页</button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import GoodsCard from '../components/GoodsCard.vue'
import { goodsApi } from '../api/index.js'

const goods = ref([])
const loading = ref(true)
const filterClassify = ref('')
const page = ref(1)
const pageSize = 10
const isLoggedIn = ref(!!localStorage.getItem('access_token'))

const classifyList = computed(() => {
  const names = new Set()
  goods.value.forEach(g => {
    const name = g.classify_rel?.name
    if (name) names.add(name)
  })
  return [...names]
})

const filteredGoods = computed(() => {
  if (!filterClassify.value) return goods.value
  return goods.value.filter(g => g.classify_rel?.name === filterClassify.value)
})

const totalPages = computed(() => Math.ceil(filteredGoods.value.length / pageSize) || 1)

const pagedGoods = computed(() => {
  const start = (page.value - 1) * pageSize
  return filteredGoods.value.slice(start, start + pageSize)
})

async function loadGoods() {
  loading.value = true
  try {
    const res = await goodsApi.getList()
    if (res.code === 200 || Array.isArray(res)) {
      goods.value = Array.isArray(res) ? res : (res.data || [])
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadGoods()
})
</script>

<style scoped>
.classify-select {
  width: auto;
  min-width: 100px;
  padding: 6px 12px;
  font-size: 13px;
}
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 24px;
}
.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.skeleton-row {
  display: flex;
  align-items: center;
  gap: 16px;
}
.goods-list {
  animation: fadeIn 0.3s ease-out;
}

@media (max-width: 768px) {
  .classify-select {
    min-width: 80px;
    font-size: 12px;
    padding: 5px 8px;
  }
  .pagination {
    gap: 10px;
    margin-top: 16px;
  }
}
</style>

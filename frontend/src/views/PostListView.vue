<template>
  <div>
    <div class="flex-between mb-16">
      <h2 style="font-size:20px">帖子列表</h2>
      <div class="flex-between gap-8">
        <select v-model="filterCategory" @change="loadPosts(1)" class="category-select">
          <option value="">全部板块</option>
          <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>
    </div>

    <div v-if="loading" class="skeleton-list">
      <div class="skeleton-card" v-for="i in 3" :key="i">
        <div class="skeleton-meta">
          <div class="skeleton skeleton-avatar"></div>
          <div>
            <div class="skeleton skeleton-text" style="width:60px"></div>
            <div class="skeleton skeleton-text" style="width:40px;height:10px"></div>
          </div>
        </div>
        <div class="skeleton skeleton-title"></div>
        <div class="skeleton skeleton-text"></div>
        <div class="skeleton skeleton-text"></div>
      </div>
    </div>
    <div v-else-if="posts.length === 0" class="empty-state">
      <p>暂无帖子</p>
      <p style="font-size:13px;margin-top:8px">还没有人发帖，快来抢沙发吧</p>
    </div>
    <template v-else>
      <div class="post-list">
        <PostCard v-for="post in posts" :key="post.id" :post="post" class="stagger-item" />
      </div>

      <div class="pagination">
        <button class="btn-outline btn-sm" :disabled="page <= 1" @click="loadPosts(page - 1)">上一页</button>
        <span style="font-size:13px;color:var(--text-secondary)">第 {{ page }} 页</span>
        <button class="btn-outline btn-sm" :disabled="!hasMore" @click="loadPosts(page + 1)">下一页</button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import PostCard from '../components/PostCard.vue'
import { postApi, categoryApi } from '../api/index.js'

const posts = ref([])
const categories = ref([])
const page = ref(1)
const hasMore = ref(false)
const loading = ref(true)
const filterCategory = ref('')

async function loadPosts(p) {
  page.value = p
  loading.value = true
  try {
    const params = { page: p, page_size: 10 }
    if (filterCategory.value) params.category_id = filterCategory.value
    const res = await postApi.getList(params)
    if (res.code === 200) {
      posts.value = res.data || []
      hasMore.value = posts.value.length >= 10
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function loadCategories() {
  try {
    const res = await categoryApi.getAll()
    if (res.code === 200) categories.value = res.data || []
  } catch {}
}

onMounted(() => {
  loadCategories()
  loadPosts(1)
})
</script>

<style scoped>
.category-select {
  width: auto;
  min-width: 120px;
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
.post-list {
  animation: fadeIn 0.3s ease-out;
}

@media (max-width: 768px) {
  .category-select {
    min-width: 100px;
    font-size: 12px;
    padding: 5px 8px;
  }
  .pagination {
    gap: 10px;
    margin-top: 16px;
  }
}
</style>

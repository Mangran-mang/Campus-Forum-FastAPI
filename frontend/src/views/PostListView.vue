<template>
  <div>
    <div class="flex-between mb-16">
      <h2 style="font-size:20px">帖子列表</h2>
      <div class="flex-between gap-8">
        <select v-model="filterCategory" @change="loadPosts(1)" class="category-select">
          <option value="">全部板块</option>
          <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
        <router-link to="/posts/create" class="btn-primary" v-if="isLoggedIn">写帖子</router-link>
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="posts.length === 0" class="empty-state">
      <p>暂无帖子</p>
      <p style="font-size:13px;margin-top:8px">还没有人发帖，快来抢沙发吧</p>
    </div>
    <template v-else>
      <PostCard v-for="post in posts" :key="post.id" :post="post" />

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
const isLoggedIn = ref(!!localStorage.getItem('access_token'))

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
</style>

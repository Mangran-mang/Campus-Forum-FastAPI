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

    <!-- 搜索框：用 form + submit 而不是只监听 input，
         ① 让回车能提交（输入框在原生的 form 里回车会自动触发 submit）
         ② 避免"每敲一个字就发一次请求"（键盘防抖要额外写，用提交更简单直观） -->
    <form class="search-bar" @submit.prevent="handleSearch">
      <input
        v-model="keywordInput"
        type="search"
        placeholder="搜索帖子标题或内容…"
        class="search-input"
        aria-label="搜索帖子"
      />
      <button type="submit" class="btn-primary btn-sm">搜索</button>
      <button
        v-if="keyword"
        type="button"
        class="btn-outline btn-sm"
        @click="clearSearch"
      >清除</button>
    </form>

    <p v-if="pageError" class="error-msg">{{ pageError }}</p>

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
      <!-- 有搜索词时的空结果和"论坛还没帖子"是两回事，文案要分开，
           否则用户会以为帖子被删了 -->
      <template v-if="keyword">
        <p>没有找到包含「{{ keyword }}」的帖子</p>
        <p style="font-size:13px;margin-top:8px">换个关键词试试，或清除搜索查看全部</p>
      </template>
      <template v-else>
        <p>暂无帖子</p>
        <p style="font-size:13px;margin-top:8px">还没有人发帖，快来抢沙发吧</p>
      </template>
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
import { pickErrorMessage } from '../utils/errorMessage.js'

const posts = ref([])
const categories = ref([])
const page = ref(1)
const hasMore = ref(false)
const loading = ref(true)
const filterCategory = ref('')

// keywordInput 是输入框里的原始文字，keyword 是"已提交生效"的搜索词。
// ## 为什么拆成两个 ref
// 如果只用 v-model 绑一个变量并在 watch 里发请求，会变成"每敲一个字查一次库"；
// 拆开后 input 只管打字，只有提交（回车/点按钮）才把它同步给 keyword 并触发查询。
const keywordInput = ref('')
const keyword = ref('')
const pageError = ref('')

async function loadPosts(p) {
  page.value = p
  loading.value = true
  pageError.value = ''
  try {
    const params = { page: p, page_size: 10 }
    if (filterCategory.value) params.category_id = filterCategory.value
    if (keyword.value) params.keyword = keyword.value
    const res = await postApi.getList(params)
    if (res.code === 200) {
      posts.value = res.data || []
      hasMore.value = posts.value.length >= 10
    } else {
      // 拿到非 200 也要提示，否则页面停留在上一次的结果上，用户以为是"没搜到"
      pageError.value = pickErrorMessage(res, '加载帖子失败')
    }
  } catch (e) {
    pageError.value = '网络异常，请稍后重试'
    console.warn(e)
  } finally {
    loading.value = false
  }
}

// 提交搜索：把输入框的内容同步到生效的 keyword，然后回到第 1 页
// ## 为什么必须回到第 1 页
// 如果用户在第 5 页搜索，新结果可能只有 2 页 → offset 落在结果集之外 → 空白页。
function handleSearch() {
  keyword.value = keywordInput.value.trim()
  loadPosts(1)
}

// 清除搜索：输入框和生效词一起清空，再查一次全部
function clearSearch() {
  keywordInput.value = ''
  keyword.value = ''
  loadPosts(1)
}

async function loadCategories() {
  try {
    const res = await categoryApi.getAll()
    if (res.code === 200) categories.value = res.data || []
  } catch (e) {
    // 板块列表只用于下拉筛选，加载失败不影响帖子展示，降级为"只有全部板块"
    console.warn('加载板块列表失败', e)
  }
}

onMounted(() => {
  loadCategories()
  loadPosts(1)
})
</script>

<style scoped>
.search-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}
.search-input {
  flex: 1;
  min-width: 0;
  padding: 8px 14px;
  font-size: 14px;
}
/* 原生 search 输入框在 WebKit 里自带一个清除小叉，和右侧的"清除"按钮重复，
   而且它在深色主题下是浅色图标、看不清。统一隐藏，改用我们自己的按钮。 */
.search-input::-webkit-search-cancel-button {
  -webkit-appearance: none;
  appearance: none;
}
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
  .search-bar {
    gap: 6px;
  }
  .search-input {
    padding: 7px 10px;
    font-size: 13px;
  }
  .pagination {
    gap: 10px;
    margin-top: 16px;
  }
}
</style>

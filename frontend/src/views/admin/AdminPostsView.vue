<template>
  <div class="admin-page">
    <h3 class="admin-title">帖子管理</h3>

    <div class="card admin-table-card">
      <table class="admin-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>标题</th>
            <th>作者</th>
            <th>浏览</th>
            <th>评论</th>
            <th>点赞</th>
            <th>公开</th>
            <th>置顶</th>
            <th>更新时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="9" class="admin-empty">加载中...</td>
          </tr>
          <tr v-else-if="posts.length === 0">
            <td colspan="9" class="admin-empty">暂无数据</td>
          </tr>
          <tr v-for="p in posts" :key="p.id">
            <td>{{ p.id }}</td>
            <td>
              <router-link :to="`/posts/${p.id}`" class="admin-link" :title="p.title">
                {{ truncate(p.title, 24) }}
              </router-link>
            </td>
            <td>{{ p.author ? p.author.nickname || p.author.uid.slice(0, 8) : p.author_uid.slice(0, 8) }}</td>
            <td>{{ p.view_count }}</td>
            <td>{{ p.comment_count }}</td>
            <td>{{ p.like_count }}</td>
            <td>
              <span :class="p.is_public ? 'tag-ok' : 'tag-warn'">{{ p.is_public ? '公开' : '私密' }}</span>
            </td>
            <td>{{ p.is_top ? '置顶' : '' }}</td>
            <td>{{ formatTime(p.updated_time) }}</td>
          </tr>
        </tbody>
      </table>

      <div class="admin-pager">
        <button class="btn-outline btn-sm" :disabled="page <= 1 || loading" @click="load(page - 1)">上一页</button>
        <span class="admin-pager-info">第 {{ page }} 页 / 共 {{ totalPages }} 页（{{ total }} 篇）</span>
        <button class="btn-outline btn-sm" :disabled="page >= totalPages || loading" @click="load(page + 1)">下一页</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { adminApi } from '../../api/index.js'
import { pickErrorMessage } from '../../utils/errorMessage.js'

const PAGE_SIZE = 10

const posts = ref([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const error = ref('')

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

function formatTime(iso) {
  return iso ? String(iso).slice(0, 10) : ''
}

function truncate(str, n) {
  return str && str.length > n ? str.slice(0, n) + '…' : str
}

async function load(p = page.value) {
  loading.value = true
  error.value = ''
  try {
    const res = await adminApi.getPosts({ page: p, page_size: PAGE_SIZE })
    if (res.code === 200) {
      posts.value = res.data.posts
      total.value = res.data.total
      page.value = res.data.page // clamp 后的生效值，保持分页器一致
    } else {
      error.value = pickErrorMessage(res, '获取帖子列表失败')
    }
  } catch (e) {
    error.value = '网络错误，请稍后重试'
  } finally {
    loading.value = false
  }
}

onMounted(() => load(1))
</script>

<style scoped>
.admin-page {
  max-width: 1100px;
}
.admin-title {
  margin-bottom: 16px;
  font-size: 18px;
}
.admin-table-card {
  overflow-x: auto;
}
.admin-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.admin-table th,
.admin-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
.admin-table th {
  color: var(--text-secondary);
  font-weight: 600;
  font-size: 12px;
}
.admin-empty {
  text-align: center;
  color: var(--text-muted);
  padding: 32px 0;
}
.admin-link {
  color: var(--primary);
  text-decoration: none;
}
.admin-link:hover {
  text-decoration: underline;
}
.tag-ok,
.tag-warn {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
}
.tag-ok {
  background: rgba(61, 220, 151, 0.15);
  color: var(--success);
}
.tag-warn {
  background: rgba(255, 184, 107, 0.15);
  color: var(--warning);
}
.admin-pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding-top: 16px;
}
.admin-pager-info {
  font-size: 13px;
  color: var(--text-secondary);
}
</style>

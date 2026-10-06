<template>
  <div class="admin-page">
    <h3 class="admin-title">商品管理</h3>

    <div class="card admin-table-card">
      <table class="admin-table">
        <thead>
          <tr>
            <th>名称</th>
            <th>价格</th>
            <th>状态</th>
            <th>分类</th>
            <th>作者</th>
            <th>更新时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="6" class="admin-empty">加载中...</td>
          </tr>
          <tr v-else-if="goods.length === 0">
            <td colspan="6" class="admin-empty">暂无数据</td>
          </tr>
          <tr v-for="g in goods" :key="g.gid">
            <td>{{ g.name }}</td>
            <td>¥{{ g.price }}</td>
            <td>
              <span :class="g.status === '在售' ? 'tag-ok' : 'tag-muted'">{{ g.status }}</span>
            </td>
            <td>{{ g.classify_rel ? g.classify_rel.name : '-' }}</td>
            <td>{{ g.author ? g.author.nickname || g.author.uid.slice(0, 8) : g.author_uid.slice(0, 8) }}</td>
            <td>{{ formatTime(g.update_time) }}</td>
          </tr>
        </tbody>
      </table>

      <div class="admin-pager">
        <button class="btn-outline btn-sm" :disabled="page <= 1 || loading" @click="load(page - 1)">上一页</button>
        <span class="admin-pager-info">第 {{ page }} 页 / 共 {{ totalPages }} 页（{{ total }} 件）</span>
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

const goods = ref([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const error = ref('')

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

function formatTime(iso) {
  return iso ? String(iso).slice(0, 10) : ''
}

async function load(p = page.value) {
  loading.value = true
  error.value = ''
  try {
    const res = await adminApi.getGoods({ page: p, page_size: PAGE_SIZE })
    if (res.code === 200) {
      goods.value = res.data.goods
      total.value = res.data.total
      page.value = res.data.page
    } else {
      error.value = pickErrorMessage(res, '获取商品列表失败')
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
.tag-ok,
.tag-muted {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
}
.tag-ok {
  background: rgba(61, 220, 151, 0.15);
  color: var(--success);
}
.tag-muted {
  background: rgba(120, 132, 156, 0.18);
  color: var(--text-muted);
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

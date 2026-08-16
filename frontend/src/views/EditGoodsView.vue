<template>
  <div>
    <h2 style="font-size:20px;margin-bottom:16px">编辑商品</h2>
    <div v-if="loading" class="loading"><span class="spinner"></span> 加载中...</div>
    <div v-else-if="!goods" class="empty-state"><p>商品不存在</p></div>
    <div v-else class="card content-enter">
      <form @submit.prevent="handleSubmit">
        <div class="field">
          <label>商品名称</label>
          <input v-model="name" placeholder="输入商品名称" required maxlength="30" />
        </div>
        <div class="field">
          <label>商品分类</label>
          <select v-model="classify" required>
            <option value="" disabled>请选择分类</option>
            <option v-for="c in categories" :key="c.id" :value="c.name">{{ c.name }}</option>
          </select>
        </div>
        <div class="field">
          <label>价格（元）</label>
          <input v-model.number="price" type="number" step="0.01" min="0" placeholder="0.00" required />
        </div>
        <div class="field">
          <label>状态</label>
          <select v-model="status">
            <option value="在售">在售</option>
            <option value="已售出">已售出</option>
          </select>
        </div>
        <p v-if="error" class="error-msg">{{ error }}</p>
        <div style="display:flex;gap:8px;margin-top:16px">
          <button type="submit" class="btn-primary" :disabled="submitting">
            {{ submitting ? '保存中...' : '保存修改' }}
          </button>
          <button type="button" class="btn-outline" @click="$router.push(`/goods/${gid}`)">取消</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { goodsApi, classifyApi } from '../api/index.js'

const route = useRoute()
const router = useRouter()
const gid = computed(() => route.params.gid)

const goods = ref(null)
const loading = ref(true)
const name = ref('')
const classify = ref('')
const price = ref(null)
const status = ref('在售')
const error = ref('')
const submitting = ref(false)
const categories = ref([])

async function loadData() {
  loading.value = true
  try {
    const [goodsRes, classifyRes] = await Promise.all([
      goodsApi.getDetail(gid.value),
      classifyApi.getAll(),
    ])

    // 加载分类
    if (classifyRes.code === 200 || Array.isArray(classifyRes)) {
      categories.value = Array.isArray(classifyRes) ? classifyRes : (classifyRes.data || [])
    }

    // 加载商品数据
    const data = goodsRes.code === 200 ? goodsRes.data : goodsRes
    if (!data) {
      goods.value = null
      loading.value = false
      return
    }
    goods.value = data
    name.value = data.name || ''
    classify.value = data.classify_rel?.name || data.classify || ''
    price.value = Number(data.price) || 0
    status.value = data.status || '在售'
  } catch {} finally {
    loading.value = false
  }
}

async function handleSubmit() {
  if (!name.value.trim()) return
  error.value = ''
  submitting.value = true
  try {
    const res = await goodsApi.update(gid.value, {
      name: name.value.trim(),
      classify: classify.value,
      price: Number(price.value) || 0,
      status: status.value,
    })
    if (res.code === 200 || (res && !res.code)) {
      router.push(`/goods/${gid.value}`)
    } else {
      error.value = res.detail || res.message || '修改失败'
    }
  } catch {
    error.value = '网络错误，请稍后重试'
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.field {
  margin-bottom: 16px;
}
.field label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}
</style>

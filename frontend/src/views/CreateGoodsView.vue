<template>
  <div class="content-enter">
    <h2 style="font-size:20px;margin-bottom:16px">发布二手商品</h2>
    <div class="card">
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
        <div class="field">
          <label>商品图片（最多5张）</label>
          <ImageUploader ref="uploaderRef" :images="[]" :max="5" :removable="true" />
        </div>
        <p v-if="error" class="error-msg">{{ error }}</p>
        <div style="display:flex;gap:8px;margin-top:16px">
          <button type="submit" class="btn-primary" :disabled="submitting">
            {{ submitting ? '发布中...' : '发布' }}
          </button>
          <button type="button" class="btn-outline" @click="$router.push('/goods')">取消</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { goodsApi, classifyApi, imageApi } from '../api/index.js'
import ImageUploader from '../components/ImageUploader.vue'

const router = useRouter()
const name = ref('')
const classify = ref('')
const price = ref(null)
const status = ref('在售')
const error = ref('')
const submitting = ref(false)
const categories = ref([])
const uploaderRef = ref(null)

async function handleSubmit() {
  if (!name.value.trim()) return
  error.value = ''
  submitting.value = true
  try {
    const res = await goodsApi.create({
      name: name.value.trim(),
      classify: classify.value,
      price: Number(price.value) || 0,
      status: status.value,
    })
    if (res.code === 200 || (res && !res.code)) {
      // 上传图片
      const gid = res.data?.gid || res.gid
      const failed = []
      if (gid) {
        const pendingFiles = uploaderRef.value?.getPendingFiles() || []
        for (const file of pendingFiles) {
          try {
            await imageApi.upload('goods', gid, file)
          } catch (e) {
            failed.push(file.name)
          }
        }
      }
      if (failed.length > 0) {
        error.value = `${failed.length} 张图片上传失败（${failed.join('、')}），商品已发布但暂无图片，请删除该商品后重新发布`
        submitting.value = false
        return
      }
      router.push('/goods')
    } else {
      error.value = res.detail || res.message || '发布失败'
    }
  } catch {
    error.value = '网络错误，请稍后重试'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  try {
    const res = await classifyApi.getAll()
    if (res.code === 200 || Array.isArray(res)) {
      categories.value = Array.isArray(res) ? res : (res.data || [])
    }
  } catch {}
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

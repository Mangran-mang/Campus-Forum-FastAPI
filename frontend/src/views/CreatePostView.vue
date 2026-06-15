<template>
  <div>
    <h2 style="font-size:20px;margin-bottom:16px">发布新帖</h2>
    <div class="card">
      <form @submit.prevent="handleSubmit">
        <div class="field">
          <label>标题</label>
          <input v-model="title" placeholder="起个吸引人的标题" required maxlength="255" />
        </div>
        <div class="field">
          <label>板块</label>
          <select v-model="categoryId">
            <option :value="null">不选择板块</option>
            <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>
        <div class="field">
          <label>内容</label>
          <textarea v-model="content" rows="12" placeholder="写下你想分享的内容..." required style="resize:vertical"></textarea>
        </div>
        <div class="field">
          <label>摘要（可选，不填自动截取）</label>
          <input v-model="summary" placeholder="简短描述一下" maxlength="255" />
        </div>
        <div class="field flex-between">
          <label>
            <input type="checkbox" v-model="isPublic" />
            公开可见
          </label>
        </div>
        <p v-if="error" class="error-msg">{{ error }}</p>
        <div style="display:flex;gap:8px;margin-top:16px">
          <button type="submit" class="btn-primary" :disabled="submitting">{{ submitting ? '发布中...' : '发布' }}</button>
          <button type="button" class="btn-outline" @click="$router.push('/posts')">取消</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { postApi, categoryApi } from '../api/index.js'

const router = useRouter()
const title = ref('')
const content = ref('')
const summary = ref('')
const categoryId = ref(null)
const isPublic = ref(true)
const error = ref('')
const submitting = ref(false)
const categories = ref([])

async function handleSubmit() {
  if (!title.value.trim() || !content.value.trim()) return
  error.value = ''
  submitting.value = true
  try {
    const res = await postApi.create({
      title: title.value,
      content: content.value,
      summary: summary.value || undefined,
      category_id: categoryId.value || undefined,
      is_public: isPublic.value,
    })
    if (res.code === 200) {
      router.push(`/posts/${res.data.id}`)
    } else {
      error.value = res.detail || res.message || '发布失败'
    }
  } catch {
    error.value = '网络错误'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  const res = await categoryApi.getAll()
  if (res.code === 200) categories.value = res.data || []
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
textarea {
  min-height: 200px;
}
</style>

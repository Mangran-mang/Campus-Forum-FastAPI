<template>
  <div class="content-enter">
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
        <!-- 配图：复用商品的 ImageUploader 组件（最多 5 张，和后端 MAX_IMAGES_PER_TARGET 一致）
             注意这里先【只选不上传】——文件存在组件的 previewFiles 里，
             等帖子创建成功、拿到 post_id 之后才逐张传（见 handleSubmit） -->
        <div class="field">
          <label>配图（可选，最多 5 张）</label>
          <ImageUploader ref="uploaderRef" :images="[]" :max="5" :removable="true" />
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
import { postApi, categoryApi, imageApi } from '../api/index.js'
import { pickErrorMessage } from '../utils/errorMessage.js'
import ImageUploader from '../components/ImageUploader.vue'

const router = useRouter()
const title = ref('')
const content = ref('')
const summary = ref('')
const categoryId = ref(null)
const isPublic = ref(true)
const error = ref('')
const submitting = ref(false)
const categories = ref([])
const uploaderRef = ref(null)

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
      // ===== 图片上传 =====
      // ## 为什么必须"先发帖、再传图"
      // 图片表用的是多态软关联（target_type + target_id），传图时必须知道 post_id，
      // 所以只能等帖子创建成功、拿到 id 之后才能传 —— 没法反过来。
      //
      // ## 为什么单张失败不中断整批
      // 图片是"锦上添花"，不该因为某一张传失败就把已经发出去的帖子作废。
      // 所以逐张 try，失败的收集起来最后一起提示用户。
      const postId = res.data?.id
      const failed = []
      if (postId) {
        const pendingFiles = uploaderRef.value?.getPendingFiles() || []
        for (const file of pendingFiles) {
          try {
            await imageApi.upload('post', postId, file)
          } catch (e) {
            failed.push(file.name)
          }
        }
      }
      if (failed.length > 0) {
        // 帖子已经发出去了，所以这里不跳转 —— 让用户看到提示，
        // 自己决定是去详情页补图（重新发布一张）还是就这样。
        error.value = `帖子已发布，但有 ${failed.length} 张图片上传失败（${failed.join('、')}）`
        submitting.value = false
        return
      }
      router.push(`/posts/${postId}`)
    } else {
      error.value = pickErrorMessage(res, '发布失败，请稍后重试')
    }
  } catch {
    error.value = '网络错误，请稍后重试'
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

@media (max-width: 768px) {
  textarea {
    min-height: 150px;
  }
}
</style>

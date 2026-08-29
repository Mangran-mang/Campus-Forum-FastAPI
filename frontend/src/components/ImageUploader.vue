<template>
  <div class="image-uploader">
    <div class="images-grid">
      <!-- 已有图片 -->
      <div v-for="img in images" :key="img.id || img.filename" class="image-item">
        <img :src="imgUrl(img)" alt="" @click="openLightbox(imgUrl(img))" />
        <button v-if="removable" class="remove-btn" @click.stop="$emit('remove', img)">×</button>
      </div>

      <!-- 新选中的预览 -->
      <div v-for="(file, idx) in previewFiles" :key="'new-'+idx" class="image-item pending">
        <img :src="file.preview" alt="" />
        <button class="remove-btn" @click.stop="removePreview(idx)">×</button>
      </div>

      <!-- 添加按钮 -->
      <label v-if="!maxReached" class="add-btn">
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          multiple
          hidden
          @change="onSelect"
          ref="fileInput"
        />
        <span>+</span>
      </label>
    </div>
    <p v-if="errorText" class="error-msg">{{ errorText }}</p>
  </div>

  <!-- 灯箱 -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="lightbox" class="lightbox-overlay" @click="lightbox = null">
        <img :src="lightbox" alt="" class="lightbox-img" @click.stop />
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  images: { type: Array, default: () => [] },      // 已上传的图片 [{id, filename}, ...]
  removable: { type: Boolean, default: true },
  max: { type: Number, default: 5 },
})

const emit = defineEmits(['remove'])

const previewFiles = ref([])       // {file, preview} 二元组
const errorText = ref('')
const lightbox = ref(null)
const fileInput = ref(null)

const maxReached = computed(() => (props.images.length + previewFiles.value.length) >= props.max)

function imgUrl(img) {
  if (!img) return ''
  if (img.preview) return img.preview
  const name = img.filename || img
  if (!name) return ''
  const type = img.target_type || 'goods'
  return `/uploads/${type}/${name}`
}

function onSelect(e) {
  errorText.value = ''
  const files = Array.from(e.target.files || [])
  const slotsLeft = props.max - props.images.length - previewFiles.value.length
  if (slotsLeft <= 0) return

  const toAdd = files.slice(0, slotsLeft)
  if (files.length > slotsLeft) {
    errorText.value = `最多只能添加 ${props.max} 张图片`
  }

  toAdd.forEach(f => {
    if (!f.type.startsWith('image/')) {
      errorText.value = '只能选择图片文件'
      return
    }
    if (f.size > 2 * 1024 * 1024) {
      errorText.value = '单张图片不能超过 2MB'
      return
    }
    previewFiles.value.push({
      file: f,
      preview: URL.createObjectURL(f),
    })
  })

  if (fileInput.value) fileInput.value.value = ''
}

function removePreview(idx) {
  const removed = previewFiles.value.splice(idx, 1)[0]
  if (removed?.preview) URL.revokeObjectURL(removed.preview)
}

function openLightbox(url) {
  lightbox.value = url
}

function getPendingFiles() {
  return previewFiles.value.map(p => p.file)
}

function clearPreviews() {
  previewFiles.value.forEach(p => URL.revokeObjectURL(p.preview))
  previewFiles.value = []
}

defineExpose({ getPendingFiles, clearPreviews })
</script>

<style scoped>
.images-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.image-item {
  width: 100px;
  height: 100px;
  border-radius: 6px;
  overflow: hidden;
  position: relative;
  cursor: pointer;
  border: 1px solid var(--border);
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}
.image-item:hover {
  transform: scale(1.04);
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.image-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}
.image-item:hover img {
  transform: scale(1.08);
}
.image-item.pending {
  border-style: dashed;
  border-color: var(--primary);
}
.remove-btn {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  border: none;
  font-size: 14px;
  line-height: 1;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.remove-btn:hover {
  background: var(--danger);
}
.add-btn {
  width: 100px;
  height: 100px;
  border: 2px dashed var(--border);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: var(--text-muted);
  cursor: pointer;
  transition: border-color 0.25s ease, color 0.25s ease, transform 0.2s ease, background 0.25s ease;
}
.add-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
  transform: scale(1.04);
  background: var(--primary-light);
}
.error-msg {
  margin-top: 6px;
}

.lightbox-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}
.lightbox-img {
  max-width: 90vw;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 4px;
}

@media (max-width: 768px) {
  .image-item, .add-btn {
    width: 80px;
    height: 80px;
  }
}
</style>

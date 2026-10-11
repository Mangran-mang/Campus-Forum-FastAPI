<template>
  <div class="card stat-card">
    <span class="stat-label">{{ label }}</span>
    <span class="stat-value">{{ value }}</span>
    <span class="stat-sub" :class="{ 'is-muted': muted }">{{ sub }}</span>
  </div>
</template>

<script setup>
// 后台统计卡片：主值是"总量"，副标题放"今日新增 / 昨日对比"这类上下文
defineProps({
  label: { type: String, required: true },
  value: { type: [Number, String], default: 0 },
  sub: { type: String, default: '' },
  // 副标题弱化：值为 0 时用灰色，避免"一片 0"看起来像坏了
  muted: { type: Boolean, default: false },
})
</script>

<style scoped>
.stat-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 18px 20px;
}
.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
}
.stat-value {
  font-size: 30px;
  font-weight: 600;
  line-height: 1.1;
  color: var(--text);
}
.stat-sub {
  font-size: 12px;
  color: var(--primary);
}
.stat-sub.is-muted {
  color: var(--text-muted);
}
</style>

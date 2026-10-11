<template>
  <div ref="el" class="admin-chart" :style="{ height: height + 'px' }"></div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import echarts from '../../utils/echarts.js'

const props = defineProps({
  option: { type: Object, required: true },
  height: { type: Number, default: 240 },
})

const el = ref(null)
let chart = null

function render() {
  if (!el.value || !props.option) return
  // 实例复用：首次 init，之后 setOption 更新即可
  // notMerge=true：换数据时清掉旧 series，否则切换图表类型会残留上一份配置
  if (!chart) chart = echarts.init(el.value)
  chart.setOption(props.option, true)
}

function handleResize() {
  chart?.resize()
}

onMounted(() => {
  render()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  // ## 必须 dispose
  // ECharts 实例挂在 window 之外，GC 收不走；不释放则每次进出页面都多留一个
  // canvas + 事件监听，切几次路由就漏几个实例
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})

// 父组件拿到数据后 option 会变（deep 才能捕捉到嵌套属性变化），此时重绘
watch(() => props.option, render, { deep: true })
</script>

<style scoped>
.admin-chart {
  width: 100%;
}
</style>

<template>
  <div class="admin-page">
    <h3 class="admin-title">数据看板</h3>

    <p v-if="error" class="error-msg">{{ error }}</p>
    <p v-else-if="!overview" class="admin-loading">加载中...</p>

    <template v-else>
      <!-- 总量卡片：总数 + 今日新增 -->
      <div class="dash-cards">
        <div v-for="item in cards" :key="item.key" class="card dash-card">
          <span class="dash-label">{{ item.label }}</span>
          <span class="dash-value">{{ item.total }}</span>
          <span class="dash-today" :class="{ 'is-zero': item.today === 0 }">
            今日新增 {{ item.today }}
          </span>
        </div>

        <!-- 日活单独一张：数据来自 Redis（另两个接口查的是 MySQL），副标题形态也不同 -->
        <div v-if="activity" class="card dash-card">
          <span class="dash-label">今日活跃</span>
          <span class="dash-value">{{ activity.today }}</span>
          <span class="dash-today" :class="{ 'is-zero': activity.today === 0 }">
            昨日 {{ activity.yesterday }}
            <template v-if="activity.delta !== null">
              · {{ activity.delta >= 0 ? '↑' : '↓' }}{{ Math.abs(activity.delta) }}%
            </template>
          </span>
        </div>
      </div>

      <!-- 趋势折线 -->
      <div class="card dash-chart-card">
        <div class="dash-chart-head">
          <span class="dash-chart-title">每日新增帖子</span>
          <div class="dash-range">
            <button
              v-for="n in [7, 30]"
              :key="n"
              class="dash-range-btn"
              :class="{ active: days === n }"
              :disabled="loadingTrend"
              @click="switchDays(n)"
            >
              近 {{ n }} 天
            </button>
          </div>
        </div>
        <div ref="trendRef" class="dash-chart"></div>
      </div>

      <!-- 两个分布饼图 -->
      <div class="dash-pies">
        <div class="card dash-chart-card">
          <span class="dash-chart-title">帖子板块分布</span>
          <div ref="postPieRef" class="dash-chart"></div>
        </div>
        <div class="card dash-chart-card">
          <span class="dash-chart-title">商品分类分布</span>
          <div ref="goodsPieRef" class="dash-chart"></div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import echarts from '../../utils/echarts.js'
import { adminApi } from '../../api/index.js'
import { pickErrorMessage } from '../../utils/errorMessage.js'

const overview = ref(null)
const trends = ref(null)
const distribution = ref(null)
const activityRaw = ref(null)
const error = ref('')
const days = ref(7)
const loadingTrend = ref(false)

const trendRef = ref(null)
const postPieRef = ref(null)
const goodsPieRef = ref(null)
let trendChart = null
let postPieChart = null
let goodsPieChart = null

// ## ECharts 是 canvas 渲染，不解析 CSS 变量
// getComputedStyle 读 var(--text) 只能拿到 "var(--text)" 字面量，
// 所以这里把主题色值显式抄一份（改了主题要同步改这里）
const TEXT_SECONDARY = '#a9b4cc'
const CARD_BG = '#131c33'
const SPLIT_LINE = 'rgba(130, 165, 230, 0.18)'
const PRIMARY = '#6aa8ff'
// 饼图色板：太空色系（与 main.css 的 --primary/--success/--warning/... 同源）
const PIE_COLORS = ['#6aa8ff', '#3ddc97', '#ffb86b', '#9d8cff', '#3ed6c8', '#ff7a90', '#f5c542']

const cards = computed(() => {
  if (!overview.value) return []
  const d = overview.value
  return [
    { key: 'user', label: '用户总数', total: d.user_total, today: d.user_today },
    { key: 'post', label: '帖子总数', total: d.post_total, today: d.post_today },
    { key: 'goods', label: '商品总数', total: d.goods_total, today: d.goods_today },
  ]
})

// 日活卡片：后端固定给 [昨天, 今天] 两天（Redis 里只存两天）
// delta 为 null 表示不显示环比 —— 昨日为 0 时算不出百分比（除零），
// 而且埋点首日的"今日"只是从埋点时刻起的半天数据，拿它跟 0 比是误导
const activity = computed(() => {
  if (!activityRaw.value) return null
  const uv = activityRaw.value.uv
  if (!uv.length) return null
  const today = uv[uv.length - 1]
  const yesterday = uv.length > 1 ? uv[uv.length - 2] : 0
  return {
    today,
    yesterday,
    delta: yesterday > 0 ? Math.round(((today - yesterday) / yesterday) * 100) : null,
  }
})

onMounted(async () => {
  window.addEventListener('resize', handleResize)
  await loadAll()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  // ## 不 dispose 就是内存泄漏：每次进出这个页面都会多留一个 canvas + 事件监听，
  // 切换几次路由后旧实例还在（ECharts 实例挂在 window 之外，GC 收不走）
  trendChart?.dispose()
  postPieChart?.dispose()
  goodsPieChart?.dispose()
  trendChart = postPieChart = goodsPieChart = null
})

async function loadAll() {
  try {
    const [o, t, dist, act] = await Promise.all([
      adminApi.getOverview(),
      adminApi.getTrends(days.value),
      adminApi.getDistribution(),
      adminApi.getActivity(),
    ])
    if (o.code !== 200) {
      error.value = pickErrorMessage(o, '加载失败')
      return
    }
    overview.value = o.data
    if (t.code === 200) trends.value = t.data
    if (dist.code === 200) distribution.value = dist.data
    // 日活失败不阻断整页 —— 数据源是 Redis，挂了不该让卡片和图表全白
    if (act.code === 200) activityRaw.value = act.data

    await nextTick() // 等 v-else 分支的 DOM 真正渲染出来，容器有尺寸才能 init
    renderTrend()
    renderPostPie()
    renderGoodsPie()
  } catch (e) {
    // adminRequest 遇到 401/403 已清会话并跳登录页，这里只兜底文案
    error.value = '加载失败，请重新登录后再试'
  }
}

async function switchDays(n) {
  if (days.value === n || loadingTrend.value) return
  days.value = n
  loadingTrend.value = true
  try {
    const res = await adminApi.getTrends(n)
    if (res.code === 200) {
      trends.value = res.data
      renderTrend()
    }
  } catch (e) {
    console.warn('趋势数据加载失败:', e)
  } finally {
    loadingTrend.value = false
  }
}

function renderTrend() {
  if (!trendRef.value || !trends.value) return
  // 实例复用（首次 init，之后 setOption 更新即可）
  if (!trendChart) trendChart = echarts.init(trendRef.value)
  trendChart.setOption(
    {
      backgroundColor: 'transparent',
      grid: { left: 44, right: 20, top: 20, bottom: 28 },
      tooltip: {
        trigger: 'axis',
        backgroundColor: CARD_BG,
        borderColor: SPLIT_LINE,
        textStyle: { color: '#e9edf6' },
      },
      xAxis: {
        type: 'category',
        // 后端给的是 "2026-10-09"，轴上只留 "10-09" 更清爽
        data: trends.value.dates.map((d) => d.slice(5)),
        axisLine: { lineStyle: { color: SPLIT_LINE } },
        axisLabel: { color: TEXT_SECONDARY },
      },
      yAxis: {
        type: 'value',
        minInterval: 1, // 计数类数据不出现小数刻度
        splitLine: { lineStyle: { color: SPLIT_LINE } },
        axisLabel: { color: TEXT_SECONDARY },
      },
      series: [
        {
          name: '新增帖子',
          type: 'line',
          smooth: true,
          symbolSize: 7,
          data: trends.value.posts,
          itemStyle: { color: PRIMARY },
          lineStyle: { width: 2, color: PRIMARY },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(106, 168, 255, 0.35)' },
              { offset: 1, color: 'rgba(106, 168, 255, 0)' },
            ]),
          },
        },
      ],
    },
    true,
  )
}

function pieOption(items, unit) {
  return {
    backgroundColor: 'transparent',
    color: PIE_COLORS,
    tooltip: {
      trigger: 'item',
      formatter: `{b}<br/>{c} ${unit} ({d}%)`,
      backgroundColor: CARD_BG,
      borderColor: SPLIT_LINE,
      textStyle: { color: '#e9edf6' },
    },
    legend: {
      bottom: 0,
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
      textStyle: { color: TEXT_SECONDARY, fontSize: 12 },
    },
    series: [
      {
        type: 'pie',
        // 环形：中间留白，视觉上比实心饼更轻
        radius: ['45%', '68%'],
        center: ['50%', '44%'],
        data: items,
        label: { color: TEXT_SECONDARY, fontSize: 11, formatter: '{b} {c}' },
        labelLine: { lineStyle: { color: SPLIT_LINE } },
        itemStyle: { borderColor: CARD_BG, borderWidth: 2 },
      },
    ],
  }
}

function renderPostPie() {
  if (!postPieRef.value || !distribution.value) return
  if (!postPieChart) postPieChart = echarts.init(postPieRef.value)
  const items = distribution.value.post_categories.map((i) => ({ name: i.name, value: i.count }))
  postPieChart.setOption(pieOption(items, '篇'), true)
}

function renderGoodsPie() {
  if (!goodsPieRef.value || !distribution.value) return
  if (!goodsPieChart) goodsPieChart = echarts.init(goodsPieRef.value)
  const items = distribution.value.goods_classifies.map((i) => ({ name: i.name, value: i.count }))
  goodsPieChart.setOption(pieOption(items, '件'), true)
}

function handleResize() {
  trendChart?.resize()
  postPieChart?.resize()
  goodsPieChart?.resize()
}
</script>

<style scoped>
.admin-page {
  max-width: 1100px;
}
.admin-title {
  margin-bottom: 16px;
  font-size: 18px;
}
.admin-loading {
  color: var(--text-muted);
  font-size: 14px;
}
.dash-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
.dash-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 20px;
}
.dash-label {
  font-size: 13px;
  color: var(--text-secondary);
}
.dash-value {
  font-size: 32px;
  font-weight: 600;
  line-height: 1.1;
  color: var(--text);
}
.dash-today {
  font-size: 12px;
  color: var(--primary);
}
/* 今日 0 新增时弱化，避免"全是 0"看起来像坏了 */
.dash-today.is-zero {
  color: var(--text-muted);
}
.dash-chart-card {
  margin-top: 16px;
  padding: 16px 18px 10px;
}
.dash-chart-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.dash-chart-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}
.dash-range {
  display: flex;
  gap: 6px;
}
.dash-range-btn {
  padding: 3px 10px;
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text-secondary);
}
.dash-range-btn:hover:not(:disabled) {
  border-color: var(--border-hover);
  color: var(--text);
}
.dash-range-btn.active {
  background: var(--primary-light);
  border-color: var(--primary);
  color: var(--primary);
}
.dash-range-btn:disabled {
  opacity: 0.6;
  cursor: default;
}
/* 容器必须有确定高度，否则 echarts.init 拿到 0 高度 → 图表不显示 */
.dash-chart {
  width: 100%;
  height: 260px;
}
.dash-pies {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
@media (max-width: 900px) {
  .dash-cards {
    grid-template-columns: repeat(2, 1fr);
  }
  .dash-pies {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 600px) {
  .dash-cards {
    grid-template-columns: 1fr;
  }
}
</style>

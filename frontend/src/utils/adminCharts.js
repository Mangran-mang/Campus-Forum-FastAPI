// 后台图表的 ECharts option 构造集中在这里
//
// ## 为什么不放在各页面里
// 折线/柱/饼的 option 结构长且重复（坐标轴、提示框、轴色、图例……），
// 三个管理页各写一遍就是三份会各自漂移的配置。抽到这里，一处调整全局生效。
//
// ## 为什么色值是硬编码而不是读 CSS 变量
// ECharts 用 canvas 渲染，不解析 CSS —— getComputedStyle 读 var(--text) 只会拿到
// "var(--text)" 这个字面量。所以主题色值在这里抄一份（改主题要同步改这里）。
const TEXT_SECONDARY = '#a9b4cc'
const CARD_BG = '#131c33'
const SPLIT_LINE = 'rgba(130, 165, 230, 0.18)'
const PRIMARY = '#6aa8ff'
// 太空色系，与 styles/main.css 的 --primary/--success/--warning/... 同源
const PIE_COLORS = ['#6aa8ff', '#3ddc97', '#ffb86b', '#9d8cff', '#3ed6c8', '#ff7a90', '#f5c542']

const tooltipBase = {
  backgroundColor: CARD_BG,
  borderColor: SPLIT_LINE,
  textStyle: { color: '#e9edf6' },
}

/**
 * 柱状图：用于"近 N 天每日新增"这类离散计数
 * 计数类数据用柱状而不是折线 —— 天与天之间没有连续关系，柱子更诚实
 */
export function barOption(dates, values, seriesName) {
  return {
    backgroundColor: 'transparent',
    grid: { left: 44, right: 16, top: 24, bottom: 28 },
    tooltip: { trigger: 'axis', ...tooltipBase },
    xAxis: {
      type: 'category',
      data: dates.map((d) => d.slice(5)), // "2026-10-11" → "10-11"
      axisLine: { lineStyle: { color: SPLIT_LINE } },
      axisLabel: { color: TEXT_SECONDARY },
    },
    yAxis: {
      type: 'value',
      minInterval: 1, // 计数类不出现小数刻度
      splitLine: { lineStyle: { color: SPLIT_LINE } },
      axisLabel: { color: TEXT_SECONDARY },
    },
    series: [
      {
        name: seriesName,
        type: 'bar',
        data: values,
        barMaxWidth: 36,
        itemStyle: { color: PRIMARY, borderRadius: [4, 4, 0, 0] },
      },
    ],
  }
}

/**
 * 环形饼图：用于分类占比
 *
 * items 形状 = **后端 distribution 接口的原始契约** [{ name, count }]
 * （注意不是 ECharts 的 { name, value } —— 转换在函数内部做，见下）
 * unit 只影响 tooltip 文案（"篇" / "件"）
 */
export function pieOption(items, unit) {
  return {
    backgroundColor: 'transparent',
    color: PIE_COLORS,
    tooltip: {
      trigger: 'item',
      formatter: `{b}<br/>{c} ${unit} ({d}%)`,
      ...tooltipBase,
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
        radius: ['42%', '66%'],
        center: ['50%', '42%'],
        // ## 这里必须做 count → value 的字段名转换
        // ECharts 只认 data 项里的 value 字段，字段名不对它**不报错**：
        // 图例照常渲染（legend 读的是 name），但每个扇区半径为 0 ——
        // 表现就是"图例在、饼图没了"。2026-10-11 踩过一次。
        data: items.map((i) => ({ name: i.name, value: i.count })),
        label: { color: TEXT_SECONDARY, fontSize: 11, formatter: '{b} {c}' },
        labelLine: { lineStyle: { color: SPLIT_LINE } },
        itemStyle: { borderColor: CARD_BG, borderWidth: 2 },
      },
    ],
  }
}

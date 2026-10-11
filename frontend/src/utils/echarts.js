// ECharts 按需注册（统一出口，各页面 import 本文件而不是直连 echarts）
//
// ## 为什么要按需引入
// `import * as echarts from 'echarts'` 会把全部图表类型（地图、K线、桑基图…）
// 一起打进来（约 1MB，gzip 后 ~330KB）。这里只注册实际用到的类型，
// 体积降到十分之一。
//
// ## ⚠️ 代价：新增图表类型必须回到这里补注册
// 漏注册的表现**不是报错，而是图表空白** —— canvas 照样存在（坐标轴能画出来），
// 只有控制台一行警告：`[ECharts] Series bar is used but not imported.`
// 2026-10-11 就踩过一次：加了柱状图却忘了注册 BarChart。
// 所以改图表类型后，务必打开控制台确认没有这行警告。
import * as echarts from 'echarts/core'
import { BarChart, PieChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  BarChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  CanvasRenderer,
])

export default echarts

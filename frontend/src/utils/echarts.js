// ECharts 按需注册（统一出口，各页面 import 本文件而不是直连 echarts）
//
// ## 为什么要按需引入
// `import * as echarts from 'echarts'` 会把全部图表类型（地图、K线、桑基图…）
// 一起打进来（约 1MB，gzip 后 ~330KB）。这里只注册实际用到的四个模块，
// 体积降到十分之一 —— 对应的代价是：以后要用新图表类型，必须回来这里补注册，
// 否则运行时是"图表不显示且不报错"（比报错更难查）。
import * as echarts from 'echarts/core'
import { LineChart, PieChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  LineChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  CanvasRenderer,
])

export default echarts

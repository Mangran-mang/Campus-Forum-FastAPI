// 等级展示工具
// 门槛与后端 level_config 表保持一致（仅用于前端展示进度，调级只需改后端）
// 索引即等级：thresholds[0]=0 表示 Lv.0 新人，thresholds[1]=100 表示 Lv.1 萌新 ...
export const LEVEL_THRESHOLDS = [0, 100, 500, 1000, 2000, 3000, 5000, 10000, 15000, 20000, 50000]
export const LEVEL_NAMES = [
  '新人', '萌新', '新手', '积极分子', '活跃用户',
  '资深用户', '达人', '专家', '大佬', '宗师', '传奇',
]
export const MAX_LEVEL = 10

export function levelLabel(level) {
  return `Lv.${level}`
}

export function levelName(level) {
  return LEVEL_NAMES[level] || ''
}

// 下一级所需经验；已满级返回 null
export function nextLevelExp(level) {
  if (level >= MAX_LEVEL) return null
  return LEVEL_THRESHOLDS[level + 1] ?? null
}

// 当前等级到下一级的经验进度百分比（0~100，满级 100）
export function levelProgress(exp, level) {
  const e = exp || 0
  if (level >= MAX_LEVEL) return 100
  const cur = LEVEL_THRESHOLDS[level] ?? 0
  const next = LEVEL_THRESHOLDS[level + 1]
  if (next === undefined || next <= cur) return 100
  const pct = ((e - cur) / (next - cur)) * 100
  return Math.max(0, Math.min(100, Math.floor(pct)))
}

# -*- coding: utf-8 -*-
"""从 CSS3全屏星空动态特效 style.css 提取星空层，适配为全屏固定背景层 stars.css"""
import re
import io

SRC = r"E:\学习资料\前端特效大全\CSS3全屏星空动态特效代码\css\style.css"
DST = r"E:\PythonItems\PythonProjects\MyFastAPIproject\frontend\src\styles\stars.css"

with io.open(SRC, "r", encoding="utf-8-sig") as f:
    css = f.read()

# 按顶层块提取：selector { ... }
blocks = {}
for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css, re.S):
    sel = " ".join(m.group(1).split())
    body = m.group(2).strip()
    if sel in blocks:  # 重复的选择器（如两个 #title span）只保留第一个
        continue
    blocks[sel] = body

# @keyframes animStar 是嵌套结构（from{...} to{...}），单独提取（位于文件末尾）
km = re.search(r"@keyframes\s+animStar\s*\{[\s\S]*", css)
if km:
    # 取到最后一个 } 为止
    end = km.group(0).rfind("}")
    blocks["@keyframes animStar"] = km.group(0)[:end + 1].strip()

order = ["#stars", "#stars:after", "#stars2", "#stars2:after", "#stars3", "#stars3:after", "@keyframes animStar"]

out = []
out.append("/* 星空背景层 —— 提取自 CSS3全屏星空动态特效，已适配为全屏固定背景 */")
out.append("/* 三层星星（1px / 2px / 3px）以不同速度缓慢上移，营造深邃太空感 */")
for sel in order:
    if sel not in blocks:
        raise SystemExit("缺少选择器块: " + sel)
    body = blocks[sel]
    if sel in ("#stars", "#stars2", "#stars3"):
        # 主层：固定铺满视口、置于内容之下、不拦截点击
        add = "position: fixed; top: 0; left: 0; z-index: 0; pointer-events: none;"
        body = add + "\n" + body
    elif sel in ("#stars:after", "#stars2:after", "#stars3:after"):
        # 副本层保持 absolute（相对 fixed 主层定位），top:2000px 实现无缝滚动
        pass
    if sel.startswith("@keyframes"):
        # keyframes 块完整自带 @keyframes 头部，不再包裹
        out.append(body)
    else:
        out.append(sel + " {\n" + body + "\n}")

with io.open(DST, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(out) + "\n")

print("生成完成:", DST)
print("块数:", len(blocks), "| 写入选择器:", len(order))

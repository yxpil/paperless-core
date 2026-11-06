# -*- coding: utf-8 -*-
"""T5: 全局交叉引用审计
检查项:
  A. 每章末尾「下一章：`xx.md`」指向正确且连续
  B. 全文反引号引用的 *.md 文件都存在
  C. 「第 NN 章」章号引用均在 00-33 范围且对应章节存在
  D. 00 章文档地图(0.1 表)与实际文件一一对应
"""
import os, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DOCS = os.path.dirname(os.path.abspath(__file__)) if os.path.basename(os.path.abspath(__file__)) != "audit_refs.py" else None
DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")

files = sorted(f for f in os.listdir(DOCS) if f.endswith(".md"))
nums = {}
for f in files:
    m = re.match(r"^(\d{2})_", f)
    if m:
        nums[int(m.group(1))] = f

problems = []

# A: 下一章链
for n in sorted(nums):
    f = nums[n]
    text = open(os.path.join(DOCS, f), encoding="utf-8").read()
    links = re.findall(r"下一章：`([^`]+)`", text)
    if n == max(nums):
        if links:
            problems.append(f"[A] {f}: 末章不应有下一章链接 -> {links}")
        continue
    if not links:
        problems.append(f"[A] {f}: 缺少「下一章」链接")
    else:
        for L in links:
            if L not in files:
                problems.append(f"[A] {f}: 下一章指向不存在的文件 {L}")
            elif not L.startswith(f"{n+1:02d}_"):
                problems.append(f"[A] {f}: 下一章应为 {n+1:02d} 号章节, 实际指向 {L}")

# ??????????????????????
ARTIFACT_MD = {"verify.md", "README.md", "CHANGELOG.md"}

# B: 反引号 .md 引用
for f in files:
    text = open(os.path.join(DOCS, f), encoding="utf-8").read()
    for ref in set(re.findall(r"`([\w\- \u4e00-\u9fff]+\.(?:md|docx|py|txt|json))`", text)):
        if ref.endswith(".md") and ref not in ARTIFACT_MD:
            if not os.path.exists(os.path.join(DOCS, ref)) and not os.path.exists(os.path.join(os.path.dirname(DOCS), ref)):
                problems.append(f"[B] {f}: 反引号引用的 md 不存在 -> {ref}")

# C: 第 NN 章 引用
for f in files:
    text = open(os.path.join(DOCS, f), encoding="utf-8").read()
    for n_str in set(re.findall(r"第\s*(\d{1,2})\s*章", text)):
        n = int(n_str)
        if n not in nums:
            problems.append(f"[C] {f}: 引用第 {n} 章, 但该章文件不存在")

# D: 00 文档地图
zero = open(os.path.join(DOCS, nums[0]), encoding="utf-8").read()
map_rows = re.findall(r"^\|\s*(\d{2})\s*\|", zero, re.M)
map_nums = sorted(set(int(x) for x in map_rows))
expected = sorted(nums)
if map_nums != expected:
    problems.append(f"[D] 00 文档地图与实际章节不一致: 地图缺 {set(expected)-set(map_nums)}, 多 {set(map_nums)-set(expected)}")
# 地图行内的编号顺序
seq = [int(x) for x in map_rows]
dups = [x for x in set(seq) if seq.count(x) > 1]
if dups:
    problems.append(f"[D] 00 文档地图有重复编号行: {dups}")

# E: 「NN §M.K」节引用：章号与节号前缀需一致，且目标章内存在该节标题
sec_refs = []
for f in files:
    text = open(os.path.join(DOCS, f), encoding="utf-8").read()
    for m in re.finditer(r"(\d{2})\s*§\s*(\d+\.\d+)", text):
        sec_refs.append((f, int(m.group(1)), m.group(2)))
for src, n, sec in sorted(set(sec_refs)):
    if n not in nums:
        problems.append(f"[E] {src}: 引用 {n:02d} §{sec}, 但该章不存在")
        continue
    target = open(os.path.join(DOCS, nums[n]), encoding="utf-8").read()
    heads = set(re.findall(r"^#{2,4}\s+(\d+(?:\.\d+)*)", target, re.M))
    if sec not in heads:
        problems.append(f"[E] {src}: 引用 {n:02d} §{sec}, 但 {nums[n]} 中无此节标题")

# F: 首行 H1 与文件名标题一致（白名单：00 章品牌行允许前缀、23 章文件名 / 被替为 CICD）
for n in sorted(nums):
    f = nums[n]
    first = open(os.path.join(DOCS, f), encoding="utf-8").read().splitlines()
    first = first[0] if first else ""
    stem = re.match(r"^\d{2}_(.+)\.md$", f)
    if not stem:
        problems.append(f"[F] {f}: 文件名不符合 NN_标题.md 规范")
        continue
    title = stem.group(1)
    if n == 0:
        ok = first.startswith("# ") and first.endswith(title)
        if not ok:
            problems.append(f"[F] {f}: H1 应为以「{title}」结尾的品牌行 -> {first[:50]}")
        continue
    m = re.match(r"^# (\d{2}) (.+)$", first)
    if not m:
        problems.append(f"[F] {f}: 首行非规范 H1 -> {first[:50]}")
    elif m.group(1) != f[:2]:
        problems.append(f"[F] {f}: H1 章号 {m.group(1)} 与文件名 {f[:2]} 不符")
    elif m.group(2) != title and m.group(2).replace("/", "") != title:
        problems.append(f"[F] {f}: H1「{m.group(2)}」与文件名标题「{title}」不一致")

print(f"共 {len(files)} 个 md, 章节号 {sorted(nums)}, 节引用 {len(sec_refs)} 处")
if problems:
    print(f"发现 {len(problems)} 个问题:")
    for p in problems:
        print(" ", p)
else:
    print("AUDIT_OK: 交叉引用全部一致, 无悬空引用")

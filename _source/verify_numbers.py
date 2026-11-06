# -*- coding: utf-8 -*-
"""T14: 关键数字全书一致性审计（只读）
规则来源：README / docs/00 §0.1、§0.5、§0.6 / 18 章 87 人月 / 30-31 章用例与集合口径。
扫描范围：docs/*.md（排除 _merge_* 瞬时文件）。根目录 README.md 单独检查。
输出：PASS / FAIL / WARN；退出码 0 = 无 FAIL。
"""
import os, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")

texts = {}
for f in sorted(os.listdir(DOCS)):
    if f.endswith(".md") and not f.startswith("_merge_"):
        texts[f] = open(os.path.join(DOCS, f), encoding="utf-8").read()
texts["README.md"] = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()

fails, warns, passes = [], [], []

def check(rule, ok, detail, warn_only=False):
    if ok:
        passes.append(f"PASS [{rule}] {detail}")
    elif warn_only:
        warns.append(f"WARN [{rule}] {detail}")
    else:
        fails.append(f"FAIL [{rule}] {detail}")

# 1. 用例总数 332（白名单：326=回归集子集；排除「条/秒」与「写了…」反例句式）
for f, t in texts.items():
    for m in re.finditer(r"(\d{2,4})\s*条([^，。；\n]{0,8})用例|用例[^，。；\n]{0,8}(\d{2,4})\s*条", t):
        n = int(m.group(1) or m.group(3))
        ctx = (m.group(2) or "") + t[max(0, m.start()-12):m.start()]
        if n >= 100 and n != 332 and n != 326 and "秒" not in ctx and not re.search(r"写了|假如|假设|若", ctx):
            check("用例总数", False, f"{f}: 出现 {n} 条用例 (应为 332)")
check("用例总数", any("332" in t for t in texts.values()), "全书存在 332 条口径")

# 2. 测试集合 21（12 回归 + 1 性能 + 8 门禁）
for f, t in texts.items():
    for m in re.finditer(r"(\d{1,2})\s*个测试集合", t):
        if int(m.group(1)) != 21:
            check("测试集合数", False, f"{f}: {m.group(1)} 个测试集合 (应为 21)")
book31 = texts.get("31_测试集合规划与执行.md", "")
check("集合构成", bool(re.search(r"12 个.{0,20}回归", book31) and re.search(r"8 个.{0,20}(门禁|专项|隔离)", book31)),
      "31 章 12 回归 + 1 性能 + 8 门禁/专项/隔离")
m = re.search(r"(\d+)\s*条功能用例", book31)
if m:
    check("回归集用例数", m.group(1) == "326", f"31 章回归集 {m.group(1)} 条 (326+6=332)")

# 3. 人月合计 87
for f in ("18_路线图、团队与风险.md", "27_成本与资源预算.md", "32_完整开发所需清单.md", "33_部门与小组分工.md"):
    t = texts.get(f, "")
    for m in re.finditer(r"合计约?\s*(\d{1,3})\s*人月|(\d{1,3})\s*人月\s*(?:基准|总量)", t):
        n = int(m.group(1) or m.group(2))
        if n != 87:
            check("人月合计", False, f"{f}: 合计/基准 {n} 人月 (应为 87)")

# 4. 需求核对表条数：实数 75，与声明一致
zero = texts["00_总纲与逐条核对.md"]
rows = re.findall(r"^\| ([A-H])(\d+) \|", zero, re.M)
by_sec = {}
for sec, num in rows:
    by_sec[sec] = max(by_sec.get(sec, 0), int(num))
actual = sum(by_sec.values())
stated = []
for f, t in texts.items():
    for m in re.finditer(r"A–H\s*共\s*(\d+)\s*条", t):
        stated.append((f, int(m.group(1))))
for f, n in stated:
    check("需求条数", n == actual, f"{f}: 声明 {n} 条, 实际 {actual} 条 (分布 {by_sec})")
if not stated:
    check("需求条数", False, "无任何文件声明 A–H 总条数, 请在 README/00 补口径")
check("需求条数", actual == 75, f"00 核对表实数 {actual} 条 (基线 75)")

# 5. 用例模块数 25
for f in ("00_总纲与逐条核对.md", "24_测试与质量保障.md", "30_全功能测试用例清单.md", "31_测试集合规划与执行.md"):
    t = texts.get(f, "")
    for m in re.finditer(r"(\d{1,2})\s*个?模块", t):
        n = int(m.group(1))
        if 10 <= n <= 99 and n != 25:
            check("用例模块数", False, f"{f}: {n} 模块 (应为 25)")

# 6. 全集文件数 34（仅限明确指文档集的语境：全集 N 文件 / 本套 N 个文件）
for f, t in texts.items():
    for m in re.finditer(r"全集\s*(\d{1,2})\s*个?文件|本套\s*(\d{1,2})\s*个文件", t):
        n = int(m.group(1) or m.group(2))
        if n != 34:
            check("全集文件数", False, f"{f}: 文档集 {n} 文件 (应为 34)")

# 7. §0.6 默认基线：单租户 500 会议室 / 5000 并发端
for f, t in texts.items():
    for m in re.finditer(r"单租户[^，。；\n]{0,20}?(\d{2,5})\s*(?:间)?会议室|单租户[^，。；\n]{0,20}?(\d{2,5})\s*(?:个)?并发端", t):
        a = m.group(1); b = m.group(2)
        if a and a != "500":
            check("默认基线-会议室", False, f"{f}: 单租户 {a} 会议室 (应为 500)")
        if b and b != "5000":
            check("默认基线-并发端", False, f"{f}: 单租户 {b} 并发端 (应为 5000)")
t03 = texts.get("03_总体架构与六端.md", "")
if re.search(r"标准档[^|\n]{0,40}(\d{2,5})\s*(?:间)?会议室", t03):
    n = re.search(r"标准档[^|\n]{0,40}(\d{2,5})\s*(?:间)?会议室", t03).group(1)
    check("默认基线-标准档", n == "500", f"03 章标准档 ≤ {n} 会议室 (与 00 §0.6 的 500 对齐)")

# 8. 15.6 资产人月小计（观察项）
t15 = texts.get("15_对外集成与 GitHub 资产整合.md", "")
vals = [int(x) for x in re.findall(r"\| P\d \| `paperless-[a-z-]+` \|[^\n]*\| (\d+) 人月 \|", t15)]
if vals:
    check("15.6 资产小计", True, f"paperless-* 资产 {len(vals)} 项合计 {sum(vals)} 人月 (资产粒度, 不与 87 相加)", warn_only=True)
    check("15.6 口径说明", "不可逐行相加" in t15, "15.6 已写明与 18.4 的口径关系")

# 9. README 文档规模声明与实测一致（字符数=去空白口径, 汉字=严格 CJK, 万位保留 1 位小数）
def _measure(paths):
    raw = nows = han = 0
    for p in paths:
        s = open(p, encoding="utf-8").read()
        raw += len(s)
        nows += len(re.sub(r"\s", "", s))
        han += len(re.findall(r"[\u4e00-\u9fff]", s))
    return {f"{raw/10000:.1f}", f"{nows/10000:.1f}", f"{han/10000:.1f}"}, nows

base_dir = os.path.join(ROOT, "_source", "docs")
base_paths = [os.path.join(base_dir, f) for f in sorted(os.listdir(base_dir)) if f.endswith(".md")]
ext_paths = [os.path.join(DOCS, f) for f in sorted(os.listdir(DOCS)) if f.endswith(".md") and not f.startswith("_merge_")]
measured, base_nows = _measure(base_paths)
measured |= _measure(ext_paths)[0]
claims = re.findall(r"(\d+\.\d+)\s*万", texts["README.md"])
bad = [c for c in claims if c not in measured]
check("README规模声明", bool(claims) and not bad,
      f"README 声明 {claims} 万 vs 实测口径集合 {sorted(measured)}" + (f"; 无法复现: {bad}" if bad else ""))
nows_declared = {f"{base_nows/10000:.1f}", f"{_measure(ext_paths)[1]/10000:.1f}"}
check("README规模口径", nows_declared <= set(claims),
      f"去空白口径声明 {sorted(nows_declared)} 均在 README（基线/扩展两行各一条）")

print("\n".join(passes))
print("\n".join(warns))
if fails:
    print("\n".join(fails))
    print(f"SUMMARY: {len(passes)} PASS / {len(warns)} WARN / {len(fails)} FAIL")
    sys.exit(1)
print(f"SUMMARY: {len(passes)} PASS / {len(warns)} WARN / 0 FAIL -> NUMBERS_OK")

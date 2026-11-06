#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""交付内容一致性核验（补齐 verify_all.py / audit_refs.py 之外的空白）。

分工：
  - verify_all.py    只比对「表数 / H1 / 段落 / 字数」这类结构计数；
  - audit_refs.py    只在 md 侧审计交叉引用（下一章链、反引号引用、章号、00 地图）；
  - 本脚本（新增）   在 **docx 产物侧** 做正文级一致性抽查，防止「md 改对了但 docx 没重生成」。

检查项：
  1. 页脚计数一致性：每册 docx 中「下一章：」条数 == 该册各章 md 中「下一章：」条数之和。
     漏链（少一条）或并发写事故（多一条）都会在这里变成 ERR。
  2. 相邻重复页脚：docx 中不允许出现两个连续的、都含「下一章」的非空段落（回归闸门）。
  3. 关键标记抽检：见 MARKERS，覆盖已知的历史缺陷点。

退出码：0 = 全部 PASS；1 = 有 FAIL。控制台中文需 PYTHONIOENCODING=utf-8。
"""

import sys
from pathlib import Path

from docx import Document

from build_docx_all import VOLUMES, chapter_body, pick

SRC = Path(__file__).resolve().parent
DOCS = SRC.parent / "docs"
OUT = SRC.parent

# (说明, 限定册=code 或 None 表示全书, 目标字符串, 期望存在?)
MARKERS = [
    ("26 章追踪矩阵已指向 05 §5.3", "V10", "05 §5.3", True),
    ("全书不再出现悬空引用 03 §5.3", None, "03 §5.3", False),
    ("全书不再出现旧页脚「文档集到此结束」", None, "文档集到此结束", False),
    ("V6 §15.5 含真实仓库名 openmeet", "V6", "openmeet", True),
    ("V6 §15.5 含真实仓库名 ONRouter", "V6", "ONRouter", True),
    ("全书无「待填」占位符", None, "待填", False),
]


def docx_paras(path):
    doc = Document(str(path))
    return [p.text for p in doc.paragraphs]


def docx_all_text(path):
    parts = docx_paras(path)
    doc = Document(str(path))
    for t in doc.tables:
        for row in t.rows:
            for c in row.cells:
                parts.append(c.text)
    return "\n".join(parts)


def volume_files():
    return {code: sorted(OUT.glob(f"{code} *.docx")) for code, _t, _c, _s in VOLUMES}


def main():
    ok = True
    files = volume_files()
    all_text = {}

    print("== 1. 页脚计数一致性（下一章 条数）==")
    for code, _title, chapters, _scope in VOLUMES:
        md_n = sum(chapter_body(pick(c)).count("下一章") for c in chapters)
        if not files[code]:
            print(f"FAIL|{code}|缺少 docx")
            ok = False
            continue
        path = files[code][0]
        all_text[code] = docx_all_text(path)
        docx_n = all_text[code].count("下一章")
        status = "PASS" if docx_n == md_n else "FAIL"
        if docx_n != md_n:
            ok = False
        print(f"{status}|{code}|md={md_n} docx={docx_n}|{'; '.join(chapters)}")

    print("\n== 2. 相邻重复页脚（回归闸门）==")
    for code, _title, _chapters, _scope in VOLUMES:
        if not files[code]:
            continue
        paras = [t for t in docx_paras(files[code][0])]
        bad = []
        prev_hit = False
        for t in paras:
            hit = "下一章" in t
            if hit and prev_hit:
                bad.append(t.strip()[:40])
            prev_hit = hit
        if bad:
            ok = False
            print(f"FAIL|{code}|相邻重复 {len(bad)} 处：{bad}")
        else:
            print(f"PASS|{code}|无相邻重复页脚")

    print("\n== 3. 关键标记抽检 ==")
    for label, code, needle, expect in MARKERS:
        scope = all_text.get(code) if code else "\n".join(all_text.values())
        if scope is None:
            print(f"SKIP|{label}|{code} 缺失")
            ok = False
            continue
        found = needle in scope
        status = "PASS" if found == expect else "FAIL"
        if found != expect:
            ok = False
        print(f"{status}|{label}|{'存在' if found else '不存在'}")

    print("\nALL_PASS" if ok else "\nHAS_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

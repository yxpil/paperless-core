#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""对生成的 DOCX 做结构回读：表数、H1 数、段落数、正文字数，与 md 源对比。

期望值不由本脚本自行猜测，而是复用生成器自己的解析逻辑：
  - build_docx_all.chapter_body() 已包含「首行非 H1 则注入卷首标题」的规则；
  - build_docx.is_table_start() / SEP_RE 是 docx 侧真正的表格判定。
这样校验口径与生成口径同源，代码围栏内的 # 与 | 不再被误计。
"""
import re
from pathlib import Path

from docx import Document

from build_docx import SEP_RE, is_table_start, parse_front_matter
from build_docx_all import VOLUMES, chapter_body, pick

SRC = Path(__file__).resolve().parent
DOCS = SRC.parent / "docs"
OUT = SRC.parent
FENCE = re.compile(r"^\s*```")
H_RE = re.compile(r"^#{1,4}\s+\S")


def expected_stats(code):
    """按生成器的拼接顺序，算出这一册应当出现的表数与 H1 数。"""
    chapters = [chapter_body(pick(c)) for c in VOLUMES_DICT[code]]
    lines = "\n\n".join(chapters).splitlines()
    tables = 0
    h1 = 0
    in_code = False
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if FENCE.match(stripped):
            in_code = not in_code
            i += 1
            continue
        if in_code:
            i += 1
            continue
        if H_RE.match(stripped):
            if stripped.startswith("# "):
                h1 += 1
            i += 1
            continue
        if is_table_start(lines, i):
            tables += 1
            i += 1
            if i < len(lines) and SEP_RE.match(lines[i]):
                i += 1
            while i < len(lines) and lines[i].strip().startswith("|"):
                i += 1
            continue
        i += 1
    return tables, h1, chapters


def docx_stats(path):
    doc = Document(str(path))
    tables = len(doc.tables)
    h1 = 0
    paras = 0
    for p in doc.paragraphs:
        if p.style.name == "Heading 1":
            h1 += 1
        if p.text.strip():
            paras += 1
    chars = sum(len(p.text) for p in doc.paragraphs)
    for t in doc.tables:
        for row in t.rows:
            for c in row.cells:
                chars += len(c.text)
    return tables, h1, paras, chars


VOLUMES_DICT = {code: chapters for code, _title, chapters, _scope in VOLUMES}


def main():
    ok = True
    for code, _title, _chapters, _scope in VOLUMES:
        mt, mh, chapters = expected_stats(code)
        files = sorted(OUT.glob(f"{code} *.docx"))
        if not files:
            print(f"FIND|{code}|缺少 docx")
            ok = False
            continue
        dt, dh, dp, dc = docx_stats(files[0])
        # docx 封面信息表 1 张，正文前独立分节
        # 注入数按生成器规则复算：front matter 之后首行非 `# ` 的章节会补一个卷首 H1
        injected = 0
        for c in VOLUMES_DICT[code]:
            _meta, body = parse_front_matter(pick(c).read_text(encoding="utf-8"))
            if not next((l for l in body.splitlines() if l.strip()), "").startswith("# "):
                injected += 1
        status = "OK"
        if dt - 1 != mt:
            status = "ERR"
            ok = False
        if dh != mh:
            status = "ERR"
            ok = False
        print(
            f"{status}|{code}|表 md={mt} docx={dt - 1}|H1 md={mh}(含注入{injected}) docx={dh}"
            f"|段={dp}|字 docx={dc}"
        )
    print("ALL_OK" if ok else "HAS_ERR")


if __name__ == "__main__":
    main()

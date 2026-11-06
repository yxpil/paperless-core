# -*- coding: utf-8 -*-
"""合订本：把 docs/00-33 全部 34 章按章号顺序合为一册（单 DOCX，带封面+目录域）。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_docx import build
from build_docx_all import pick, chapter_body, DOCS, OUT, DATE

def main():
    parts, used = [], []
    for i in range(34):
        p = pick(f'{i:02d}')
        parts.append(chapter_body(p))
        used.append(p.stem)
    meta = ('---\n'
            'code: PL-DOC-BOOK\n'
            'title: 无纸化系统全套设计文档（合订本）\n'
            'subtitle: 全集 · 34 章\n'
            'version: V1.0\n'
            f'date: {DATE}\n'
            'secret: 内部公开\n'
            'phase: 设计 / 开发 / 测试 / 实施 / 运维\n'
            'org: 无纸化系统项目组\n'
            'scope: 需求、架构、详细设计、接口、安全、测试、实施、成本、组织全量\n'
            'output: 00 无纸化全集 合订本 V1.0.docx\n'
            '---\n\n')
    tmp = DOCS / '_merge_BOOK.md'
    tmp.write_text(meta + '\n\n'.join(parts) + '\n', encoding='utf-8')
    out = OUT / '00 无纸化全集 合订本 V1.0.docx'
    build(tmp, out)
    tmp.unlink()
    print(f'OK|{out.name}|{out.stat().st_size}|{len(used)} 章|{used[0]}..{used[-1]}')

if __name__ == '__main__':
    main()

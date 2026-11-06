#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""按代码块感知的方式统计 md 表数与 H1 数，复核 V8/V10 的差异是否来自代码块。"""
import re
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / 'docs'
SEP = re.compile(r'^\s*\|[\s:\-|]+\|\s*$')

TARGET = {
    'V8': ['21', '22', '23'],
    'V10': ['25', '26', '27', '28', '29'],
}


def pick(prefix):
    for p in sorted(DOCS.glob('*.md')):
        if p.name.startswith(prefix + '_'):
            return p
    raise FileNotFoundError(prefix)


def stats(path):
    lines = path.read_text(encoding='utf-8').splitlines()
    tables = 0
    h1 = 0
    fence = False
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith('```'):
            fence = not fence
            i += 1
            continue
        if fence:
            i += 1
            continue
        if re.match(r'^# ', lines[i]):
            h1 += 1
        if lines[i].lstrip().startswith('|') and i + 1 < len(lines) and (
                SEP.match(lines[i + 1]) or lines[i + 1].lstrip().startswith('|')):
            tables += 1
            i += 1
            if i < len(lines) and SEP.match(lines[i]):
                i += 1
            while i < len(lines) and lines[i].strip().startswith('|'):
                i += 1
            continue
        i += 1
    return tables, h1


for code, chapters in TARGET.items():
    t = h = 0
    detail = []
    for c in chapters:
        a, b = stats(pick(c))
        t += a
        h += b
        detail.append(f'{c}:表{a}/H1-{b}')
    print(f'{code}|表合计={t}|H1合计={h}|' + ' '.join(detail))

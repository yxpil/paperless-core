#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 docs/ 下的 Markdown 章节按主题合册输出 DOCX（沿用 build_docx 的排版）。

每册：封面信息表 + 动态目录域 + 正文独立分节（页码从 1 起）。
"""
import sys
from pathlib import Path

from build_docx import build, parse_front_matter

SRC = Path(__file__).resolve().parent
DOCS = SRC.parent / 'docs'
OUT = SRC.parent
DATE = '2026-11-05'

VOLUMES = [
    ('V1', '总纲与概念体系', ['00', '01'],
     '本册内容：总纲与逐条核对、概念与体系'),
    ('V2', '工程基线、架构与插件体系', ['02', '03', '04'],
     '本册内容：开发标准与工程基线、总体架构与六端、插件化接入体系'),
    ('V3', '多端联动、老设备与身份注册', ['05', '06', '07'],
     '本册内容：多设备联动与投屏远程控制、老设备与传统无纸化对接、身份注册与信任'),
    ('V4', '内容协作、检索审计与视频', ['08', '09', '10'],
     '本册内容：文档协作与文件互通、检索溯源与审计、视频会议录播与 AI 总结'),
    ('V5', '安全、高可用、网络与行业赋能', ['11', '12', '13', '14'],
     '本册内容：安全加密与危险感知、高可用熔断与运维、网络互通与去中心化、行业赋能与 DIY 交付'),
    ('V6', '对外集成、详细设计与 UI 标准', ['15', '16', '17'],
     '本册内容：对外集成与 GitHub 资产整合、服务端与前端详细设计、UI 设计标准'),
    ('V7', '路线、现场能力与组织分工', ['18', '19', '20', '32', '33'],
     '本册内容：路线图团队与风险、离线预下载与会议准备、多资源叠放与图层合成、完整开发所需清单、部门与小组分工'),
    ('V8', '工程治理与交付流程', ['21', '22', '23'],
     '本册内容：反焦油坑治理、进度控制与考核、CI/CD 流水线'),
    ('V9', '质量保障与测试体系', ['24', '30', '31'],
     '本册内容：测试与质量保障、全功能测试用例清单、测试集合规划与执行'),
    ('V10', '数据、需求、成本、实施与模板', ['25', '26', '27', '28', '29'],
     '本册内容：数据治理与存储、需求工程与变更控制、成本与资源预算、实施培训与运营移交、附录模板与清单'),
]


def pick(prefix):
    for p in sorted(DOCS.glob('*.md')):
        if p.name.startswith(prefix + '_'):
            return p
    raise FileNotFoundError(f'找不到章节 {prefix}')


def chapter_body(path):
    text = path.read_text(encoding='utf-8')
    meta, body = parse_front_matter(text)
    first = next((l for l in body.splitlines() if l.strip()), '')
    if not first.startswith('# '):
        body = f'# {path.stem}\n\n' + body
    return body.strip('\n')


def main():
    made = []
    for code, title, chapters, scope in VOLUMES:
        parts = []
        used = []
        for c in chapters:
            p = pick(c)
            parts.append(chapter_body(p))
            used.append(p.stem)
        meta = ('---\n'
                f'code: PL-DOC-{code}\n'
                f'title: {title}\n'
                f'subtitle: 无纸化全集 · {code}\n'
                'version: V1.0\n'
                f'date: {DATE}\n'
                'secret: 内部公开\n'
                'phase: 设计 / 开发 / 测试 / 实施 / 运维\n'
                'org: 无纸化系统项目组\n'
                f'scope: {scope}\n'
                f'output: {code} {title} V1.0.docx\n'
                '---\n\n')
        merged = meta + '\n\n'.join(parts) + '\n'
        tmp = DOCS / f'_merge_{code}.md'
        tmp.write_text(merged, encoding='utf-8')
        out = OUT / f'{code} {title} V1.0.docx'
        build(tmp, out)
        tmp.unlink()
        made.append((out.name, len(used), ', '.join(used), out.stat().st_size))

    for name, n, used, size in made:
        print(f'OK|{name}|{size}|{n}|{used}')
    print(f'TOTAL|{len(made)}')


if __name__ == '__main__':
    sys.exit(main())

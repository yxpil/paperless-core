#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Markdown -> DOCX 构建器（无纸化系统文档集专用）

支持：# 标题 / ## ### #### 层级、段落、- 与 1. 列表、GFM 表格、代码块、
> 提示块、![图题](相对路径) 图片、**粗体** 与 `代码` 内联。
统一输出 A4、2.5cm 页边距、黑体标题 + 宋体正文、动态目录域、正文页码从 1 起。
"""
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

CN_BODY = '宋体'
CN_HEAD = '黑体'
EN_FONT = 'Times New Roman'
CODE_FONT = 'Consolas'

GRAY = (0x59, 0x59, 0x59)
BLACK = (0, 0, 0)

INLINE_RE = re.compile(r'(\*\*[^*]+\*\*|`[^`]+`)')
SEP_RE = re.compile(r'^\s*\|[\s:\-|]+\|\s*$')


# ---------------------------------------------------------------- 基础工具
def set_run_font(run, cn=CN_BODY, en=EN_FONT, size=12, bold=False, color=BLACK, italic=False):
    run.font.name = en
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor(*color)
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = OxmlElement('w:rFonts')
        rpr.insert(0, rfonts)
    rfonts.set(qn('w:ascii'), en)
    rfonts.set(qn('w:hAnsi'), en)
    rfonts.set(qn('w:eastAsia'), cn)
    rfonts.set(qn('w:cs'), en)


def style_font(style, cn=CN_BODY, en=EN_FONT, size=12, bold=False, color=BLACK):
    style.font.name = en
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.color.rgb = RGBColor(*color)
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = OxmlElement('w:rFonts')
        rpr.insert(0, rfonts)
    rfonts.set(qn('w:ascii'), en)
    rfonts.set(qn('w:hAnsi'), en)
    rfonts.set(qn('w:eastAsia'), cn)
    rfonts.set(qn('w:cs'), en)


def shade(element, fill):
    """为段落 pPr 或单元格 tcPr 添加底纹。"""
    pr = element.get_or_add_pPr() if element.tag.endswith('}p') else element.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill)
    pr.append(shd)


def shade_cell(cell, fill):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill)
    tcpr.append(shd)


def add_field(paragraph, code, placeholder=''):
    run = paragraph.add_run()
    fld_begin = OxmlElement('w:fldChar')
    fld_begin.set(qn('w:fldCharType'), 'begin')
    instr = OxmlElement('w:instrText')
    instr.set(qn('xml:space'), 'preserve')
    instr.text = code
    fld_sep = OxmlElement('w:fldChar')
    fld_sep.set(qn('w:fldCharType'), 'separate')
    text = OxmlElement('w:t')
    text.text = placeholder
    fld_end = OxmlElement('w:fldChar')
    fld_end.set(qn('w:fldCharType'), 'end')
    for el in (fld_begin, instr, fld_sep, text, fld_end):
        run._r.append(el)
    return run


# ---------------------------------------------------------------- 样式初始化
def build_styles(doc):
    styles = doc.styles

    normal = styles['Normal']
    style_font(normal, CN_BODY, EN_FONT, 12)
    pf = normal.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf.line_spacing = 1.5
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.first_line_indent = Pt(24)

    for name, size, before, after in (('Heading 1', 16, 14, 6),
                                      ('Heading 2', 14, 11, 5),
                                      ('Heading 3', 12, 9, 4),
                                      ('Heading 4', 12, 6, 3)):
        st = styles[name]
        style_font(st, CN_HEAD, EN_FONT, size, bold=True, color=BLACK)
        p = st.paragraph_format
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.space_before = Pt(before)
        p.space_after = Pt(after)
        p.first_line_indent = Pt(0)
        p.line_spacing = 1.5
        p.keep_with_next = True
        p.keep_together = True

    title = styles['Title']
    style_font(title, CN_HEAD, EN_FONT, 18, bold=True)
    tp = title.paragraph_format
    tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tp.space_before = Pt(0)
    tp.space_after = Pt(18)
    tp.first_line_indent = Pt(0)
    tp.line_spacing = 1.5

    subtitle = styles['Subtitle']
    style_font(subtitle, '楷体', EN_FONT, 12)
    sp = subtitle.paragraph_format
    sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sp.space_after = Pt(12)
    sp.first_line_indent = Pt(0)
    sp.line_spacing = 1.5

    # 自定义样式
    from docx.enum.style import WD_STYLE_TYPE
    cap = styles.add_style('DocCaption', WD_STYLE_TYPE.PARAGRAPH)
    cap.base_style = normal
    style_font(cap, CN_BODY, EN_FONT, 10.5)
    cp = cap.paragraph_format
    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cp.first_line_indent = Pt(0)
    cp.line_spacing = 1.5
    cp.space_before = Pt(4)
    cp.space_after = Pt(4)

    tt = styles.add_style('TableText', WD_STYLE_TYPE.PARAGRAPH)
    tt.base_style = normal
    style_font(tt, CN_BODY, EN_FONT, 10.5)
    tp2 = tt.paragraph_format
    tp2.first_line_indent = Pt(0)
    tp2.left_indent = Pt(0)
    tp2.right_indent = Pt(0)
    tp2.line_spacing = 1.0
    tp2.space_before = Pt(1)
    tp2.space_after = Pt(1)
    tp2.alignment = WD_ALIGN_PARAGRAPH.LEFT

    code_st = styles.add_style('CodeBlock', WD_STYLE_TYPE.PARAGRAPH)
    code_st.base_style = normal
    style_font(code_st, CN_BODY, CODE_FONT, 9)
    cpf = code_st.paragraph_format
    cpf.first_line_indent = Pt(0)
    cpf.left_indent = Cm(0.4)
    cpf.line_spacing = 1.0
    cpf.space_before = Pt(3)
    cpf.space_after = Pt(3)
    cpf.alignment = WD_ALIGN_PARAGRAPH.LEFT

    note_st = styles.add_style('NoteBlock', WD_STYLE_TYPE.PARAGRAPH)
    note_st.base_style = normal
    style_font(note_st, '楷体', EN_FONT, 10.5, color=GRAY)
    npf = note_st.paragraph_format
    npf.first_line_indent = Pt(0)
    npf.left_indent = Cm(0.2)
    npf.right_indent = Cm(0.2)
    npf.line_spacing = 1.3
    npf.space_before = Pt(6)
    npf.space_after = Pt(6)


def page_setup(section):
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)


# ---------------------------------------------------------------- 内容写入
def add_inline(paragraph, text, size=12, bold=False, cn=CN_BODY, color=BLACK):
    for piece in INLINE_RE.split(text):
        if not piece:
            continue
        if piece.startswith('**') and piece.endswith('**'):
            run = paragraph.add_run(piece[2:-2])
            set_run_font(run, cn, EN_FONT, size, bold=True, color=color)
        elif piece.startswith('`') and piece.endswith('`'):
            run = paragraph.add_run(piece[1:-1])
            set_run_font(run, cn, CODE_FONT, size - 0.5, bold=bold, color=color)
        else:
            run = paragraph.add_run(piece)
            set_run_font(run, cn, EN_FONT, size, bold=bold, color=color)


def add_cover(doc, meta):
    for _ in range(3):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        set_run_font(p.add_run(''), CN_BODY, EN_FONT, 12)
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(6)
    set_run_font(p.add_run('无　纸　化　会　议　系　统'), CN_HEAD, EN_FONT, 22, bold=True)

    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(30)
    set_run_font(p.add_run('PaperlessCore · 企业级软件工程文档集'), '楷体', EN_FONT, 13, color=GRAY)

    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.space_after = Pt(8)
    set_run_font(p.add_run(meta.get('title', '')), CN_HEAD, EN_FONT, 26, bold=True)

    if meta.get('subtitle'):
        p = doc.add_paragraph()
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Pt(0)
        p.paragraph_format.space_after = Pt(40)
        set_run_font(p.add_run(meta['subtitle']), '楷体', EN_FONT, 13, color=GRAY)
    else:
        doc.add_paragraph()

    rows = [('文档编号', meta.get('code', '')),
            ('文档版本', meta.get('version', 'V1.0')),
            ('文档密级', meta.get('secret', '内部公开')),
            ('编制日期', meta.get('date', '')),
            ('适用阶段', meta.get('phase', '设计 / 开发 / 测试 / 实施 / 运维')),
            ('编制单位', meta.get('org', '无纸化系统项目组'))]
    table = doc.add_table(rows=len(rows), cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for idx, (k, v) in enumerate(rows):
        row = table.rows[idx]
        row.cells[0].width = Cm(3.4)
        row.cells[1].width = Cm(8.6)
        for c_idx, val in enumerate((k, v)):
            cell = row.cells[c_idx]
            cell.width = Cm(3.4 if c_idx == 0 else 8.6)
            para = cell.paragraphs[0]
            para.style = doc.styles['TableText']
            para.paragraph_format.alignment = (WD_ALIGN_PARAGRAPH.CENTER if c_idx == 0
                                               else WD_ALIGN_PARAGRAPH.LEFT)
            set_run_font(para.add_run(f'{val}：' if c_idx == 0 else val),
                         CN_BODY, EN_FONT, 10.5, bold=(c_idx == 0))
    # 去掉封面表格边框
    tbl = table._tbl
    tblpr = tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        el = OxmlElement(f'w:{edge}')
        el.set(qn('w:val'), 'none')
        borders.append(el)
    tblpr.append(borders)

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(60)
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    set_run_font(p.add_run(meta.get('scope', '')), '楷体', EN_FONT, 10.5, color=GRAY)


def enable_update_fields(doc):
    """让 Word/WPS 打开文档时自动重算 TOC 等域。

    生成器只写入 TOC 域代码，没有缓存的目录条目与页码（`PAGEREF` 数为 0），
    不置该标志则目录一直显示「可按 F9 更新」占位文本。
    """
    settings = doc.settings.element
    if settings.find(qn('w:updateFields')) is not None:
        return
    el = OxmlElement('w:updateFields')
    el.set(qn('w:val'), 'true')
    compat = settings.find(qn('w:compat'))
    if compat is not None:
        compat.addprevious(el)
    else:
        settings.append(el)


def add_toc(doc):
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(14)
    set_run_font(p.add_run('目　　录'), CN_HEAD, EN_FONT, 16, bold=True)

    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    add_field(p, r'TOC \o "1-2" \h \z \u', '（目录域，可按 F9 更新）')


def add_code_block(doc, lines):
    for line in lines:
        p = doc.add_paragraph(style='CodeBlock')
        shade(p._p, 'F2F2F2')
        run = p.add_run(line if line.strip() else ' ')
        set_run_font(run, CN_BODY, CODE_FONT, 9)


def _disp_len(s):
    """按全角/半角估算显示宽度。"""
    return sum(2 if ord(ch) > 127 else 1 for ch in s)


def _col_widths(rows, n_cols, total_cm=16.0):
    """按内容长度分配列宽，避免长表被均分挤成竖排文字。"""
    if n_cols == 1:
        return [Cm(total_cm)]
    weights = []
    for c in range(n_cols):
        lens = [_disp_len(r[c]) if c < len(r) else 0 for r in rows]
        body_max = sorted(lens[1:])[int(len(lens[1:]) * 0.9)] if len(lens) > 1 else 0
        w = max(4, min(40, max(body_max, lens[0] if lens else 0)))
        if c == 0:
            w = max(4, w)
        weights.append(w)
    s = sum(weights)
    out, used = [], 0.0
    for i, w in enumerate(weights):
        cm = max(1.3, total_cm * w / s)
        out.append(cm)
        used += cm
    if used > total_cm:
        k = total_cm / used
        out = [max(1.2, c * k) for c in out]
    return [Cm(c) for c in out]


def add_table(doc, rows):
    header, body = rows[0], rows[1:]
    n_cols = len(header)
    widths = _col_widths(rows, n_cols)
    fs = 10.5 if n_cols <= 5 else (9.5 if n_cols == 6 else 9)
    table = doc.add_table(rows=len(rows), cols=n_cols)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    tblpr = table._tbl.tblPr
    layout = OxmlElement('w:tblLayout')
    layout.set(qn('w:type'), 'fixed')
    tblpr.append(layout)

    for r_idx, row_vals in enumerate([header] + body):
        row = table.rows[r_idx]
        trpr = row._tr.get_or_add_trPr()
        cant = OxmlElement('w:cantSplit')
        trpr.append(cant)
        if r_idx == 0:
            th = OxmlElement('w:tblHeader')
            trpr.append(th)
        for c_idx, val in enumerate(row_vals):
            cell = row.cells[c_idx]
            cell.width = widths[c_idx] if c_idx < len(widths) else widths[-1]
            para = cell.paragraphs[0]
            para.style = doc.styles['TableText']
            para.paragraph_format.alignment = (WD_ALIGN_PARAGRAPH.CENTER
                                               if c_idx == 0 else WD_ALIGN_PARAGRAPH.LEFT)
            add_inline(para, val, size=fs, bold=(r_idx == 0))
            if r_idx == 0:
                shade_cell(cell, 'D9D9D9')
            cell.vertical_alignment = 1  # center
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def add_image(doc, path, caption, width_cm=15.0):
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    run = p.add_run()
    run.add_picture(str(path), width=Cm(width_cm))
    cp = doc.add_paragraph(style='DocCaption')
    add_inline(cp, caption, size=10.5)


# ---------------------------------------------------------------- 解析主循环
def parse_front_matter(text):
    meta = {}
    body = text
    if text.startswith('---'):
        end = text.find('\n---', 3)
        if end != -1:
            block = text[3:end].strip()
            body = text[end + 4:]
            for line in block.splitlines():
                if ':' in line:
                    k, v = line.split(':', 1)
                    meta[k.strip()] = v.strip()
    return meta, body


def is_table_start(lines, idx):
    if not lines[idx].lstrip().startswith('|'):
        return False
    if idx + 1 >= len(lines):
        return False
    nxt = lines[idx + 1]
    if SEP_RE.match(nxt):
        return True
    return nxt.lstrip().startswith('|')


def split_row(line):
    line = line.strip()
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|'):
        line = line[:-1]
    return [c.strip() for c in line.split('|')]


def build(md_path, out_path):
    text = md_path.read_text(encoding='utf-8')
    meta, body = parse_front_matter(text)
    doc = Document()
    build_styles(doc)
    page_setup(doc.sections[0])

    add_cover(doc, meta)
    doc.add_page_break()
    add_toc(doc)

    body_sec = doc.add_section(WD_SECTION.NEW_PAGE)
    page_setup(body_sec)
    body_sec.footer.is_linked_to_previous = False
    fp = body_sec.footer.paragraphs[0]
    fp.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.paragraph_format.first_line_indent = Pt(0)
    run = add_field(fp, 'PAGE', '1')
    set_run_font(run, CN_BODY, EN_FONT, 10.5)
    sectpr = body_sec._sectPr
    pg = OxmlElement('w:pgNumType')
    pg.set(qn('w:start'), '1')
    sectpr.append(pg)

    first_section = doc.sections[0]
    first_section.footer.is_linked_to_previous = False

    lines = body.splitlines()
    in_code = False
    code_buf = []
    first_h1 = True
    i = 0

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.startswith('```'):
            if in_code:
                add_code_block(doc, code_buf)
                code_buf = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_buf.append(raw)
            i += 1
            continue

        if not stripped:
            i += 1
            continue

        # 图片
        m = re.match(r'^!\[(.*?)\]\((.*?)\)\s*$', stripped)
        if m:
            caption, rel = m.group(1), m.group(2)
            img = (md_path.parent / rel).resolve()
            if img.exists():
                add_image(doc, img, caption)
            else:
                p = doc.add_paragraph(style='DocCaption')
                add_inline(p, f'（图片缺失：{caption}）', size=10.5)
            i += 1
            continue

        # 标题
        m = re.match(r'^(#{1,4})\s+(.*)$', stripped)
        if m:
            level = len(m.group(1))
            heading_text = m.group(2).strip()
            p = doc.add_paragraph(style=f'Heading {level}')
            if level == 1:
                if not first_h1:
                    p.paragraph_format.page_break_before = True
                first_h1 = False
            add_inline(p, heading_text, size={1: 16, 2: 14, 3: 12, 4: 12}[level],
                       bold=True, cn=CN_HEAD)
            i += 1
            continue

        # 提示块
        if stripped.startswith('>'):
            buf = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                buf.append(lines[i].strip().lstrip('>').strip())
                i += 1
            p = doc.add_paragraph(style='NoteBlock')
            shade(p._p, 'F2F2F2')
            add_inline(p, ' '.join(buf), size=10.5, cn='楷体', color=GRAY)
            continue

        # 表格
        if is_table_start(lines, i):
            rows = [split_row(lines[i])]
            i += 1
            if i < len(lines) and SEP_RE.match(lines[i]):
                i += 1
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append(split_row(lines[i]))
                i += 1
            n_cols = len(rows[0])
            rows = [r + [''] * (n_cols - len(r)) if len(r) < n_cols else r[:n_cols] for r in rows]
            add_table(doc, rows)
            continue

        # 列表
        m = re.match(r'^(\s*)[-*]\s+(.*)$', line)
        if m:
            indent = len(m.group(1))
            style = 'List Bullet' if indent < 2 else 'List Bullet 2'
            p = doc.add_paragraph(style=style)
            p.paragraph_format.first_line_indent = Pt(0)
            p.paragraph_format.line_spacing = 1.5
            add_inline(p, m.group(2).strip())
            i += 1
            continue

        m = re.match(r'^(\s*)(\d+)[.、]\s+(.*)$', line)
        if m:
            p = doc.add_paragraph(style='List Number')
            p.paragraph_format.first_line_indent = Pt(0)
            p.paragraph_format.line_spacing = 1.5
            add_inline(p, m.group(3).strip())
            i += 1
            continue

        # 表题（以“表”开头的独立行，可带加粗）
        if re.match(r'^(\*\*)?表\s*\d+', stripped):
            p = doc.add_paragraph(style='DocCaption')
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
            add_inline(p, stripped, size=10.5)
            i += 1
            continue

        # 普通段落
        p = doc.add_paragraph()
        add_inline(p, stripped)
        i += 1

    if in_code and code_buf:
        add_code_block(doc, code_buf)

    props = doc.core_properties
    props.title = meta.get('title', '')
    props.subject = '无纸化会议系统企业级软件工程文档'
    props.author = meta.get('org', '无纸化系统项目组')
    props.category = meta.get('code', '')
    props.comments = meta.get('version', 'V1.0')

    enable_update_fields(doc)

    doc.save(str(out_path))
    return meta


def main():
    src_dir = Path(__file__).resolve().parent
    doc_dir = src_dir / 'docs'
    out_dir = src_dir.parent
    files = sorted(doc_dir.glob('*.md'))
    index = []
    for md in files:
        meta = parse_front_matter(md.read_text(encoding='utf-8'))[0]
        out_name = meta.get('output') or (md.stem + '.docx')
        out_path = out_dir / out_name
        build(md, out_path)
        index.append((out_name, meta.get('title', ''), out_path.stat().st_size))
        print(f'OK  {out_name}  {out_path.stat().st_size/1024:.0f} KB')
    for name, title, size in index:
        print(f'  - {name} | {title}')


if __name__ == '__main__':
    sys.exit(main())

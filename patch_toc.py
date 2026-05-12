"""
patch_toc.py - 生成带 TOC 域代码的格式化目录（样式写死在 styles.xml 中）

核心策略：
  1. 将 toc 1/2/3 样式写入 styles.xml（宋体+TNR 小四，加粗，点前导符）
  2. 为每个标题添加书签
  3. 生成 TOC 域代码段落
  4. Word 按 F9→更新整个目录，使用样式中定义的格式，生成真实页码

用法：python patch_toc.py <输入文件> [输出文件]

依赖：python-docx, lxml
"""

from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from lxml import etree
import zipfile
import os
import sys
import re

NS_W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
_H1_KEYS = ('heading 1', '标题 1', 'heading1')
_H2_KEYS = ('heading 2', '标题 2', 'heading2')
_H3_KEYS = ('heading 3', '标题 3', 'heading3')
_FRONT_MATTER = ('摘要', 'abstract')


def _W(tag):
    return f'{{{NS_W}}}{tag}'


def _clean_text(raw):
    return raw.replace('\r', '').replace('\x07', '').replace('\x0b', '').strip()


def _is_toc_heading(text):
    return bool(re.match(r'^\s*目\s*录', text))


def _is_front_matter(text):
    return re.sub(r'[\s　 ]', '', text).lower() in _FRONT_MATTER


def _to_roman(n):
    vals = [(1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'),
            (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'),
            (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]
    res = ''
    for v, s in vals:
        while n >= v:
            res += s
            n -= v
    return res


def _get_para_text(p):
    return _clean_text(''.join(t.text or '' for t in p.iter(_W('t'))))


def _get_heading_level_from_style_id(sid):
    if sid in ('1', 'Heading1', 'heading1'): return 1
    if sid in ('2', 'Heading2', 'heading2'): return 2
    if sid in ('3', 'Heading3', 'heading3'): return 3
    return None


def _find_or_create_bookmark(p, label):
    ids = set()
    for bm in p.iter(_W('bookmarkStart')):
        ids.add(int(bm.get(_W('id'), '0')))
        name = bm.get(_W('name'))
        if name == label:
            return bm.get(_W('id'))

    max_id = max(ids) if ids else 0
    new_id = str(max_id + 1)

    bm_start = OxmlElement('w:bookmarkStart')
    bm_start.set(_W('id'), new_id)
    bm_start.set(_W('name'), label)

    bm_end = OxmlElement('w:bookmarkEnd')
    bm_end.set(_W('id'), new_id)

    first = p.find(_W('pPr'))
    if first is not None:
        first.addnext(bm_start)
    else:
        p.insert(0, bm_start)
    p.append(bm_end)

    return new_id


def _clear_toc_area(doc, toc_para):
    """删除"目  录"到第一个 H1 之间的所有旧内容"""
    body = doc.element.body
    paras = list(body.iterchildren(_W('p')))

    idx = next((i for i, p in enumerate(paras) if p is toc_para), None)
    if idx is None:
        return 0

    removed = 0
    for p in list(paras[idx + 1:]):
        text = _get_para_text(p)
        pPr = p.find(_W('pPr'))
        if pPr is not None:
            ps = pPr.find(_W('pStyle'))
            if ps is not None:
                sid = ps.get(_W('val'))
                if _get_heading_level_from_style_id(sid) == 1:
                    break
        body.remove(p)
        removed += 1

    return removed


def _create_toc_field_para():
    """创建包含 TOC 域代码的段落"""
    p = OxmlElement('w:p')
    pPr = OxmlElement('w:pPr')
    jc = OxmlElement('w:jc')
    jc.set(qn('w:val'), 'left')
    pPr.append(jc)
    p.append(pPr)

    # begin
    r1 = OxmlElement('w:r')
    fld_begin = OxmlElement('w:fldChar')
    fld_begin.set(qn('w:fldCharType'), 'begin')
    r1.append(fld_begin)
    p.append(r1)

    # instrText
    r2 = OxmlElement('w:r')
    instr = OxmlElement('w:instrText')
    instr.set(qn('w:space'), 'preserve')
    instr.text = r' TOC \o "1-3" \h \z \u '
    r2.append(instr)
    p.append(r2)

    # separate
    r3 = OxmlElement('w:r')
    fld_sep = OxmlElement('w:fldChar')
    fld_sep.set(qn('w:fldCharType'), 'separate')
    r3.append(fld_sep)
    p.append(r3)

    # 提示文字（separate 和 end 之间）
    r_placeholder = OxmlElement('w:r')
    rpr_ph = OxmlElement('w:rPr')
    rf_ph = OxmlElement('w:rFonts')
    rf_ph.set(qn('w:ascii'), 'Times New Roman')
    rf_ph.set(qn('w:hAnsi'), 'Times New Roman')
    rf_ph.set(qn('w:eastAsia'), '宋体')
    rpr_ph.append(rf_ph)
    for t in ('w:sz', 'w:szCs'):
        el = OxmlElement(t)
        el.set(qn('w:val'), '24')
        rpr_ph.append(el)
    r_placeholder.append(rpr_ph)
    t_ph = OxmlElement('w:t')
    t_ph.text = '【按 Ctrl+A → F9 → "更新整个目录" 生成目录】'
    r_placeholder.append(t_ph)
    p.append(r_placeholder)

    # end
    r4 = OxmlElement('w:r')
    fld_end = OxmlElement('w:fldChar')
    fld_end.set(qn('w:fldCharType'), 'end')
    r4.append(fld_end)
    p.append(r4)

    return p


def _patch_toc_styles(zip_content):
    """
    修改 styles.xml 中的 TOC1/TOC2/TOC3 样式。
    设置：宋体+TNR 小四(12pt)，TOC1/TOC2 加粗，点前导符，1.5 倍行距。
    """
    if 'word/styles.xml' not in zip_content:
        print('  [警告] styles.xml 不存在')
        return

    root = etree.fromstring(zip_content['word/styles.xml'])

    # TOC 样式定义
    style_defs = {
        'TOC1': {'name': 'toc 1', 'indent': '0', 'bold': True, 'basedOn': 'a'},
        'TOC2': {'name': 'toc 2', 'indent': '420', 'bold': True, 'basedOn': 'a'},
        'TOC3': {'name': 'toc 3', 'indent': '840', 'bold': False, 'basedOn': 'a'},
    }

    for sid, cfg in style_defs.items():
        style = root.find(f'.//{{{NS_W}}}style[@{_W("styleId")}="{sid}"]')
        if style is not None:
            # 清除旧内容重新构建
            for child in list(style):
                style.remove(child)
        else:
            # 创建新样式
            style = etree.SubElement(root, f'{{{NS_W}}}style')
            style.set(f'{{{NS_W}}}type', 'paragraph')
            style.set(f'{{{NS_W}}}styleId', sid)

        # name
        name_el = etree.SubElement(style, f'{{{NS_W}}}name')
        name_el.set(f'{{{NS_W}}}val', cfg['name'])

        # basedOn
        based = etree.SubElement(style, f'{{{NS_W}}}basedOn')
        based.set(f'{{{NS_W}}}val', cfg['basedOn'])

        # next
        nxt = etree.SubElement(style, f'{{{NS_W}}}next')
        nxt.set(f'{{{NS_W}}}val', 'a')

        # uiPriority
        pri = etree.SubElement(style, f'{{{NS_W}}}uiPriority')
        pri.set(f'{{{NS_W}}}val', '39')

        # pPr
        ppr = etree.SubElement(style, f'{{{NS_W}}}pPr')

        # spacing: 1.5 倍行距
        sp = etree.SubElement(ppr, f'{{{NS_W}}}spacing')
        sp.set(f'{{{NS_W}}}line', '360')
        sp.set(f'{{{NS_W}}}lineRule', 'auto')
        sp.set(f'{{{NS_W}}}before', '0')
        sp.set(f'{{{NS_W}}}after', '0')

        # indent
        ind = etree.SubElement(ppr, f'{{{NS_W}}}ind')
        ind.set(f'{{{NS_W}}}left', cfg['indent'])

        # tabs: right-aligned dot leader
        tabs = etree.SubElement(ppr, f'{{{NS_W}}}tabs')
        tab = etree.SubElement(tabs, f'{{{NS_W}}}tab')
        tab.set(f'{{{NS_W}}}val', 'right')
        tab.set(f'{{{NS_W}}}leader', 'dot')
        tab.set(f'{{{NS_W}}}pos', '9072')

        # rPr
        rpr = etree.SubElement(style, f'{{{NS_W}}}rPr')

        # rFonts
        rf = etree.SubElement(rpr, f'{{{NS_W}}}rFonts')
        rf.set(f'{{{NS_W}}}ascii', 'Times New Roman')
        rf.set(f'{{{NS_W}}}hAnsi', 'Times New Roman')
        rf.set(f'{{{NS_W}}}eastAsia', '宋体')
        rf.set(f'{{{NS_W}}}cs', 'Times New Roman')

        # sz/szCs: 24 = 12pt = 小四
        for stag in ('sz', 'szCs'):
            el = etree.SubElement(rpr, f'{{{NS_W}}}{stag}')
            el.set(f'{{{NS_W}}}val', '24')

        # bold
        if cfg['bold']:
            for btag in ('b', 'bCs'):
                etree.SubElement(rpr, f'{{{NS_W}}}{btag}')

    zip_content['word/styles.xml'] = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
    print('  已修补 toc 1/2/3 样式（宋体小四、加粗、点前导符、1.5倍行距）')


def add_toc(doc_path, output_path=None):
    doc_path = os.path.abspath(doc_path)
    if not os.path.exists(doc_path):
        raise FileNotFoundError(f"文件不存在: {doc_path}")
    out_path = os.path.abspath(output_path) if output_path else doc_path

    print("处理文件:", doc_path)

    # ── 阶段一：python-docx 操作（书签 + TOC 域） ──
    doc = Document(doc_path)
    body = doc.element.body

    # 1. 找"目  录"
    toc_para = None
    paras_list = list(body.iterchildren(_W('p')))
    for i, p in enumerate(paras_list):
        if _is_toc_heading(_get_para_text(p)):
            toc_para = p
            break

    if toc_para is None:
        print('  未找到 "目  录"，在开头新建')
        first_p = body.find(_W('p'))
        heading = OxmlElement('w:p')
        pPr = OxmlElement('w:pPr')
        jc = OxmlElement('w:jc')
        jc.set(qn('w:val'), 'center')
        pPr.append(jc)
        heading.append(pPr)
        r = OxmlElement('w:r')
        t = OxmlElement('w:t')
        t.text = '目　　录'
        r.append(t)
        heading.append(r)
        if first_p is not None:
            body.insert(list(body).index(first_p), heading)
        else:
            body.append(heading)
        toc_para = heading

    # 2. 清除旧目录条目
    cleared = _clear_toc_area(doc, toc_para)
    if cleared:
        print(f"  清除 {cleared} 个旧段落")

    # 3. 扫描标题，添加书签
    headings = []
    for p in body.iterchildren(_W('p')):
        text = _get_para_text(p)
        if not text:
            continue
        pPr = p.find(_W('pPr'))
        if pPr is None:
            continue
        ps = pPr.find(_W('pStyle'))
        if ps is None:
            continue
        sid = ps.get(_W('val'))
        level = _get_heading_level_from_style_id(sid)
        if level is None:
            continue
        if _is_toc_heading(text):
            continue
        headings.append((p, text, level))

    # 为每个标题创建唯一书签
    seen_labels = set()
    for p, text, level in headings:
        base = re.sub(r'[\s　]', '', text)[:20]
        base = re.sub(r'[^a-zA-Z0-9一-鿿_]', '', base)
        label = f'_Toc_{base}'
        while label in seen_labels:
            label += '_'
        seen_labels.add(label)
        _find_or_create_bookmark(p, label)

    # 4. 在"目  录"后插入 TOC 域代码段落
    toc_field_para = _create_toc_field_para()
    toc_para.addnext(toc_field_para)

    doc.save(out_path)
    print(f"  添加了 {len(headings)} 个书签和 TOC 域代码")

    # ── 阶段二：zipfile 修补 styles.xml ──
    with zipfile.ZipFile(out_path, 'r') as z:
        zip_content = {n: z.read(n) for n in z.namelist()}

    _patch_toc_styles(zip_content)

    temp_out = out_path + '.tmp'
    with zipfile.ZipFile(temp_out, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in sorted(zip_content):
            z.writestr(name, zip_content[name])

    os.replace(temp_out, out_path)
    print(f"完成: {out_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    add_toc(input_file, output_file)

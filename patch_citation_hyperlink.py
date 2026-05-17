"""
patch_citation_hyperlink.py - 将参考文献引用标记 [N] 转换为可点击超链接

功能：
  1. 为参考文献列表中每条 [N] 条目添加书签 _CiteRef_N
  2. 扫描正文段落，将 [N] 样式引用标记转为指向该书签的超链接

依赖：python-docx
用法：python patch_citation_hyperlink.py <输入文件> [输出文件]
"""

import sys
import os
import re
import copy
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

W = qn
CITE_PAT = re.compile(r'\[(\d+(?:\s*[, \-]\s*\d+)*)\]')


def _add_bookmark(p, name):
    """为段落添加书签"""
    ids = set()
    for bs in p.iter(W('w:bookmarkStart')):
        try:
            ids.add(int(bs.get(W('w:id'), '0')))
        except ValueError:
            pass
    bid = str(max(ids) + 1 if ids else 0)

    bms = OxmlElement('w:bookmarkStart')
    bms.set(W('w:id'), bid)
    bms.set(W('w:name'), name)
    bme = OxmlElement('w:bookmarkEnd')
    bme.set(W('w:id'), bid)

    fr = p.find(W('w:r'))
    if fr is not None:
        fr.addprevious(bms)
    else:
        pPr = p.find(W('w:pPr'))
        if pPr is not None:
            pPr.addnext(bms)
        else:
            p.insert(0, bms)
    p.append(bme)


def _make_hyperlink(anchor, text, rpr=None):
    """创建 w:hyperlink > w:r > w:t（自动清除蓝色+下划线格式）"""
    hl = OxmlElement('w:hyperlink')
    hl.set(W('w:anchor'), anchor)
    hl.set(W('w:history'), '1')
    r = OxmlElement('w:r')

    # 从原始 rPr 复制字体属性，但剔除 color/underline → 超链接文字继承正文字体
    if rpr is not None:
        clean_rpr = copy.deepcopy(rpr)
        for tag in ('w:color', 'w:u', 'w:uColor'):
            for el in clean_rpr.findall(W(tag)):
                clean_rpr.remove(el)
        color = OxmlElement('w:color')
        color.set(W('w:val'), 'auto')
        clean_rpr.append(color)
        r.append(clean_rpr)

    t = OxmlElement('w:t')
    t.set(qn('xml:space'), 'preserve')
    t.text = text
    r.append(t)
    hl.append(r)
    return hl


def _make_run(text, rpr=None):
    """创建 w:r > w:t"""
    r = OxmlElement('w:r')
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    t = OxmlElement('w:t')
    t.set(qn('xml:space'), 'preserve')
    t.text = text
    r.append(t)
    return r


def add_entry_bookmarks(doc):
    """为参考文献列表中的每条 [N] 条目添加书签"""
    in_bib = False
    n = 0
    for para in doc.paragraphs:
        text = para.text.strip()
        if text == '参考文献':
            in_bib = True
            continue
        if not in_bib or not text:
            continue
        m = re.match(r'^\[(\d+)\]', text)
        if m:
            _add_bookmark(para._element, f'_CiteRef_{m.group(1)}')
            n += 1
    return n


def _convert_para(p):
    """将单个段落中的引用标记转为超链接，返回 True 表示有修改"""
    children = list(p.iterchildren())

    runs_info = []
    pos = 0
    for ci, child in enumerate(children):
        if child.tag == W('w:r'):
            t = child.find(W('w:t'))
            if t is not None and t.text:
                runs_info.append((ci, child, t.text, pos))
                pos += len(t.text)

    if not runs_info:
        return False

    full = ''.join(t for _, _, t, _ in runs_info)
    matches = list(CITE_PAT.finditer(full))
    if not matches:
        return False

    cite_of = {}
    for m in matches:
        first_num = int(re.search(r'\d+', m.group(1)).group())
        for ppos in range(m.start(), m.end()):
            cite_of[ppos] = first_num

    new_children = []
    for ci, child in enumerate(children):
        rinfo = next((ri for ri in runs_info if ri[0] == ci), None)
        if rinfo is None:
            new_children.append(child)
            continue

        _, elem, text, gs = rinfo
        rpr = elem.find(W('w:rPr'))

        has_cite = any((gs + local_ci) in cite_of for local_ci in range(len(text)))
        if not has_cite:
            new_children.append(elem)
            continue

        segs = []
        cur_type = None
        cur_chars = []
        cur_num = None

        for local_ci, ch in enumerate(text):
            gpos = gs + local_ci
            in_cite = gpos in cite_of
            this_type = ('cite', cite_of[gpos]) if in_cite else ('text', None)

            if this_type != cur_type and cur_chars:
                segs.append((cur_type, ''.join(cur_chars), cur_num))
                cur_chars = []

            cur_type = this_type
            cur_chars.append(ch)
            if in_cite:
                cur_num = cite_of[gpos]

        if cur_chars:
            segs.append((cur_type, ''.join(cur_chars), cur_num))

        for seg_type, seg_text, num in segs:
            if not seg_text:
                continue
            if seg_type[0] == 'text':
                new_children.append(_make_run(seg_text, rpr))
            else:
                new_children.append(_make_hyperlink(f'_CiteRef_{num}', seg_text, rpr))

    for child in list(p):
        p.remove(child)
    for child in new_children:
        p.append(child)

    return True


def convert_para_citations(doc):
    """将正文段落中引用标记转为超链接"""
    in_bib = False
    n = 0
    for para in doc.paragraphs:
        text = para.text.strip()
        if text == '参考文献':
            in_bib = True
        if in_bib or not text:
            continue
        if not CITE_PAT.search(para.text):
            continue
        if _convert_para(para._element):
            n += 1
    return n


def patch_citation_hyperlink(input_path, output_path):
    """主函数"""
    doc = Document(input_path)
    bm = add_entry_bookmarks(doc)
    print(f'  已为 {bm} 个参考文献条目添加书签')
    cn = convert_para_citations(doc)
    print(f'  已转换 {cn} 个段落中的引用标记为超链接')
    doc.save(output_path)
    if bm or cn:
        print(f'  已保存: {output_path}')
    else:
        print(f'  无需修改，已保存: {output_path}')
    return bm + cn


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    inp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else inp
    if not os.path.exists(inp):
        print(f'错误: 文件不存在 {inp}')
        sys.exit(1)
    patch_citation_hyperlink(inp, out)

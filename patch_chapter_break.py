"""
patch_chapter_break.py - 为所有章级标题添加分页符

每一章（包括致谢、参考文献等）在新的一页开始。
跳过：摘要/Abstract/目录（已由 patch_thanks.py 处理），
以及第一章（已由 patch_pagenum.py 的分节符处理）。
其余所有 Heading 1 标题均添加 pageBreakBefore。

用法：python patch_chapter_break.py <输入文件> [输出文件]
"""

import sys
import os
import re
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

W = qn

# 前置部分标题（已有其他补丁处理分页）
_FRONT_MATTER = frozenset(k.lower() for k in ('摘要', 'abstract', '目录'))


def _normalise(text: str) -> str:
    """移除所有空白类字符（含全角空格）用于比较"""
    return re.sub(r'[\s　]', '', text).lower()


def add_chapter_breaks(doc: Document) -> int:
    """为所有非前置/非首章的 Heading 1 添加 pageBreakBefore"""
    found_first = False
    n = 0

    for para in doc.paragraphs:
        pPr = para._element.find(W('w:pPr'))
        if pPr is None:
            continue
        pStyle = pPr.find(W('w:pStyle'))
        if pStyle is None:
            continue
        sid = pStyle.get(W('w:val'))
        if sid not in ('1', 'Heading1', 'heading1'):
            continue

        # 跳过前置部分（摘要、Abstract、目录）
        if _normalise(para.text) in _FRONT_MATTER:
            continue

        # 跳过第一个非前置章标题（绪论）——patch_pagenum 用分节符处理了分页
        if not found_first:
            found_first = True
            continue

        pb = pPr.find(W('w:pageBreakBefore'))
        if pb is None:
            pPr.append(OxmlElement('w:pageBreakBefore'))
            n += 1

    return n


def patch_chapter_break(input_path: str, output_path: str) -> int:
    doc = Document(input_path)
    n = add_chapter_breaks(doc)
    doc.save(output_path)
    if n:
        print(f'  已为 {n} 个章标题添加分页符')
    else:
        print('  无需添加分页符')
    return n


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    inp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else inp
    if not os.path.exists(inp):
        print(f'错误: 文件不存在 {inp}')
        sys.exit(1)
    patch_chapter_break(inp, out)

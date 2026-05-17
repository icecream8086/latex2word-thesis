"""
patch_justify.py - 将正文段落全部设为两端对齐（JUSTIFY）

跳过标题、目录、题注、源代码等非正文样式。
"""

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
import sys
import os

# 两端对齐 enum 值
JUSTIFY = WD_ALIGN_PARAGRAPH.JUSTIFY  # 3

# 跳过以下样式的段落（全部小写，比较时忽略大小写）
# 标题、目录、题注、代码块维持原有对齐方式
SKIP_STYLES = {
    'heading 1', 'heading 2', 'heading 3', 'heading 4',
    'toc 1', 'toc 2', 'toc 3',
    'image caption', 'table caption',
    'source code',
}

# 跳过样式名前缀
SKIP_PREFIXES = ('heading ', 'toc ')


def _has_image(paragraph):
    """检查段落是否包含图片（含 <w:drawing> 或 <w:pict>）"""
    from docx.oxml.ns import qn
    p = paragraph._element
    return p.find(f'.//{qn("w:drawing")}') is not None


def _should_skip(paragraph):
    style = paragraph.style
    if style is None:
        return False
    name = style.name.lower() if style.name else ''
    if not name:
        return False
    if name in SKIP_STYLES:
        return True
    for prefix in SKIP_PREFIXES:
        if name.startswith(prefix):
            return True
    if _has_image(paragraph):
        return True
    return False


def patch_justify(input_path, output_path):
    doc = Document(input_path)
    modified = 0
    skipped = 0

    for para in doc.paragraphs:
        if _should_skip(para):
            skipped += 1
            continue
        if para.alignment != JUSTIFY:
            para.alignment = JUSTIFY
            modified += 1

    doc.save(output_path)
    print(f'已设置 {modified} 个段落为两端对齐（跳过 {skipped} 个非正文段落）')
    if modified == 0:
        print('（所有段落已经是两端对齐）')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: python patch_justify.py <输入文件> [输出文件]')
        sys.exit(1)

    input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        base, ext = os.path.splitext(input_file)
        output_file = f'{base}_justify{ext}'

    if not os.path.exists(input_file):
        print(f'错误: 输入文件不存在 - {input_file}')
        sys.exit(1)

    patch_justify(input_file, output_file)

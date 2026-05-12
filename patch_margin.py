"""
patch_margin.py - 使用 python-docx 统一设置页边距（仿 99.docx 模板）

用法：python patch_margin.py <输入文件> [输出文件]

依赖：python-docx (pip install python-docx)
"""

from docx import Document
from docx.shared import Cm
import os
import sys


# ==================== 控制变量（基于 99.docx 模板） ====================
MARGIN_TOP = Cm(2.20)      # 上边距 2.20cm
MARGIN_BOTTOM = Cm(2.20)   # 下边距 2.20cm
MARGIN_LEFT = Cm(2.50)     # 左边距 2.50cm
MARGIN_RIGHT = Cm(2.50)    # 右边距 2.50cm
HEADER_DIST = Cm(1.20)     # 页眉顶端距离 1.20cm
FOOTER_DIST = Cm(1.50)     # 页脚底端距离 1.50cm
# =====================================================================


def set_margins(doc_path, output_path=None):
    doc_path = os.path.abspath(doc_path)
    if not os.path.exists(doc_path):
        raise FileNotFoundError(f"文件不存在: {doc_path}")

    out_path = os.path.abspath(output_path) if output_path else doc_path

    print("处理文件:", doc_path)
    print(f"页边距: 上{2.20}cm 下{2.20}cm 左{2.50}cm 右{2.50}cm")
    print(f"页眉距离: 1.20cm  页脚距离: 1.50cm")

    doc = Document(doc_path)

    for i, section in enumerate(doc.sections):
        section.top_margin = MARGIN_TOP
        section.bottom_margin = MARGIN_BOTTOM
        section.left_margin = MARGIN_LEFT
        section.right_margin = MARGIN_RIGHT
        section.header_distance = HEADER_DIST
        section.footer_distance = FOOTER_DIST
        print(f"  第 {i + 1} 节页边距已设置")

    doc.save(out_path)
    print(f"完成: {out_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    set_margins(input_file, output_file)

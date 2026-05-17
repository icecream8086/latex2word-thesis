"""
patch_figure_caption.py - 图片标题加粗 + 表格自适应（非破坏性）

用与 patch_table_caption.py 相同的非破坏方式加粗图片标题，
保留所有 run 结构、超链接和书签，实现 caption ↔ 正文双向跳转。

操作：
  1. 表格宽度自适应页面
  2. 图片标题：加粗 + 移除编号后冒号（非破坏性）
"""

import sys
import os
import re
import zipfile
import shutil
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


def auto_fit_tables(input_path, output_path):
    """
    通过直接操作 XML 将所有表格宽度设置为页面宽度（自动适应窗口）。
    替换原来 autoexec.py 中 Win32 COM 的 AutoFitBehavior(2) 调用。
    """
    tmp_dir = os.path.join(os.path.dirname(output_path) or ".", "~tmp_docx_fix")
    os.makedirs(tmp_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(input_path, 'r') as zip_in:
            zip_in.extractall(tmp_dir)

        doc_path = os.path.join(tmp_dir, "word", "document.xml")
        with open(doc_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()

        xml_content = re.sub(
            r'<w:tblW\s+w:type="auto"\s+w:w="0"\s*/>',
            '<w:tblW w:w="5000" w:type="pct"/>',
            xml_content
        )

        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)

        if os.path.exists(output_path):
            os.remove(output_path)
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
            for root, dirs, files in os.walk(tmp_dir):
                for fn in files:
                    file_path = os.path.join(root, fn)
                    arcname = os.path.relpath(file_path, tmp_dir)
                    zip_out.write(file_path, arcname)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print(f"表格自动适应窗口完成，已保存至: {output_path}")


def fix_figure_caption_bold(input_path, output_path):
    """
    非破坏性地将图片标题设为加粗 + 移除编号后冒号。
    保留 run 结构、超链接、书签等 → 双向交叉引用正常工作。
    """
    doc = Document(input_path)

    figure_caption_styles = ["Figure Caption", "图片标题", "Caption", "Image Caption"]

    modified_count = 0

    for paragraph in doc.paragraphs:
        style_name = paragraph.style.name

        is_figure_caption = any(style_name == s for s in figure_caption_styles)

        if not is_figure_caption:
            text = paragraph.text.lower().strip()
            if text and (text.startswith("图") or text.startswith("figure") or text.startswith("fig.")):
                is_figure_caption = True

        if not is_figure_caption:
            continue

        # 非破坏性加粗：遍历所有 w:r（含超链接内部的 run）
        p = paragraph._element
        for r_elem in p.iter(qn("w:r")):
            rPr = r_elem.find(qn("w:rPr"))
            if rPr is None:
                rPr = OxmlElement("w:rPr")
                r_elem.insert(0, rPr)
            if rPr.find(qn("w:b")) is None:
                rPr.append(OxmlElement("w:b"))

        # 非破坏性冒号移除：将冒号 run 替换为空格（保留图文间距）
        for run in paragraph.runs:
            if run.text and re.fullmatch(r'\s*[：:]\s*', run.text):
                run.text = " "

        modified_count += 1

    doc.save(output_path)
    print(f"处理完成，共修改了 {modified_count} 个图片标题")
    print(f"已保存至: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python fix_figure_caption.py <输入文件> [输出文件]")
        print("示例: python patch_figure_caption.py input.docx output.docx")
        sys.exit(1)

    input_file = sys.argv[1]

    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}_fixed{ext}"

    if not os.path.exists(input_file):
        print(f"错误: 输入文件不存在 - {input_file}")
        sys.exit(1)

    auto_fit_tables(input_file, output_file)
    fix_figure_caption_bold(output_file, output_file)

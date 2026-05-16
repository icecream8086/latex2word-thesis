"""
patch_crossref_font.py - 清除交叉引用超链接内 run 的格式，继承正文段落字体

LaTeX 中的 \ref{fig:xxx} 经过 pandoc-tex-numbering 生成超链接。
Word 默认对其应用 "Hyperlink" 样式（蓝色+下划线），或保留 run 级字体设置。

本脚本扫描 document.xml 中所有内部书签超链接（w:hyperlink[w:anchor]），
**彻底删除子 run 上的 w:rPr**，让文字完全继承段落的正文字体。

用法：python patch_crossref_font.py <输入文件> [输出文件]
"""

import sys
import os
import re
import zipfile
import shutil


def strip_hyperlink_font(input_path, output_path):
    tmp_dir = os.path.join(os.path.dirname(output_path) or ".", "~tmp_docx_crossref")
    os.makedirs(tmp_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(input_path, 'r') as z:
            z.extractall(tmp_dir)

        doc_path = os.path.join(tmp_dir, "word", "document.xml")
        with open(doc_path, 'r', encoding='utf-8') as f:
            xml = f.read()

        modified = False

        # 匹配 w:hyperlink 整个元素（含 w:anchor 的内部书签链接）
        def _remove_rpr_in_hyperlink(m):
            tag = m.group(0)
            # 删除超链接内所有 <w:rPr>...</w:rPr> 或自闭合的 <w:rPr/>
            new_tag = re.sub(
                r'<w:rPr\b[^>]*>.*?</w:rPr\s*>',
                '',
                tag,
                flags=re.DOTALL
            )
            new_tag = re.sub(
                r'<w:rPr\s*/>',
                '',
                new_tag
            )
            return new_tag

        old_xml = xml
        xml = re.sub(
            r'<w:hyperlink\b[^>]*>.*?</w:hyperlink>',
            _remove_rpr_in_hyperlink,
            xml,
            flags=re.DOTALL
        )

        if xml != old_xml:
            modified = True
            print("  已清除交叉引用超链接内 run 的所有格式，完全继承正文字体")

        if not modified:
            print("  未找到需要处理的交叉引用超链接")
        else:
            with open(doc_path, 'w', encoding='utf-8') as f:
                f.write(xml)

            # 重新打包
            if os.path.exists(output_path):
                os.remove(output_path)
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:
                for root, dirs, files in os.walk(tmp_dir):
                    for fn in files:
                        fpath = os.path.join(root, fn)
                        arcn = os.path.relpath(fpath, tmp_dir)
                        zout.write(fpath, arcn)

            print(f"已保存至: {output_path}")

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}_nohyper{ext}"

    if not os.path.exists(input_file):
        print(f"错误: 输入文件不存在 - {input_file}")
        sys.exit(1)

    strip_hyperlink_font(input_file, output_file)

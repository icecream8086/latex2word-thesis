"""
patch_caption_colon.py - 移 chart 图/表题注编号后的冒号

直接在 document.xml 上做文本替换，不经过 python-docx 的 run API，
避免字体/格式被改变。

图题 (ImageCaption):  "图4.1: 标题" → "图4.1 标题"
表题 (TableCaption):  在单独 run 中的 ": " → ""
"""

import sys
import os
import re
import zipfile
import shutil


def remove_caption_colon(input_path, output_path):
    tmp_dir = os.path.join(os.path.dirname(output_path) or ".", "~tmp_docx_colon")
    os.makedirs(tmp_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(input_path, 'r') as z:
            z.extractall(tmp_dir)

        doc_path = os.path.join(tmp_dir, "word", "document.xml")
        with open(doc_path, 'r', encoding='utf-8') as f:
            xml = f.read()

        modified = False

        # 1) 表题：在 TableCaption 段落中，找到内容仅为冒号的 run，替换为空格
        #    匹配 <w:t ...>: </w:t> → <w:t> </w:t>（保留空格）
        new_xml = re.sub(
            r'(<w:p\b[^>]*>\s*<w:pPr\b[^>]*>\s*<w:pStyle\s+w:val="TableCaption"[^>]*/>.*?'
            r'<w:r\b[^>]*>\s*<w:rPr[^>]*>.*?</w:rPr>\s*<w:t[^>]*)'  # 到 <w:t 为止，不含 >
            r'>\s*[：:]\s*</w:t>',
            r'\1> </w:t>',
            xml,
            flags=re.DOTALL
        )
        if new_xml != xml:
            modified = True
            print("  [表题] 已移除冒号 run")
            xml = new_xml

        # 1.5) 表题：补上序号与标题之间的空格（空 run 无 w:t 元素）
        #     <w:r><w:rPr>...</w:rPr></w:r> → <w:r><w:rPr>...</w:rPr><w:t> </w:t></w:r>
        new_xml = re.sub(
            r'(<w:p\b[^>]*>\s*<w:pPr\b[^>]*>\s*<w:pStyle\s+w:val="TableCaption"[^>]*/>.*?'
            r'<w:r\b[^>]*>\s*<w:rPr[^>]*>.*?</w:rPr>)'  # \1 up to </w:rPr>
            r'\s*</w:r>',  # immediately followed by </w:r> (no w:t element)
            r'\1<w:t xml:space="preserve"> </w:t></w:r>',
            xml,
            flags=re.DOTALL
        )
        if new_xml != xml:
            modified = True
            print("  [表题] 已补空格")
            xml = new_xml

        # 2) 图题：在 ImageCaption 段落中，移除 "图X.Y:" 中的冒号
        #    匹配 <w:t ...>图数字:  →  <w:t ...>图数字
        new_xml = re.sub(
            r'(<w:p\b[^>]*>\s*<w:pPr\b[^>]*>\s*<w:pStyle\s+w:val="ImageCaption"[^>]*/>.*?'
            r'<w:t[^>]*>)图([\d.]+)[：:]\s*',
            r'\1图\2 ',
            xml,
            flags=re.DOTALL
        )
        if new_xml != xml:
            modified = True
            print("  [图题] 已移除冒号")
            xml = new_xml

        if not modified:
            print("  未找到需要处理的冒号")
            # 仍然保存（实际上没变化）
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
        print("用法: python patch_caption_colon.py <输入文件> [输出文件]")
        sys.exit(1)

    input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}_nocolon{ext}"

    if not os.path.exists(input_file):
        print(f"错误: 输入文件不存在 - {input_file}")
        sys.exit(1)

    remove_caption_colon(input_file, output_file)

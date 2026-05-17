#!/usr/bin/env python3
"""
patch_list_align.py — 将 DOCX 中列表段落（itemize/enumerate）的对齐方式改为两端对齐

Pandoc 默认将列表渲染为左对齐（jc=left/missing），
Word 中显得右边参差不齐。本脚本将所有带编号/项目符号的段落
（含 w:numPr 的段落）设为 jc="both"（两端对齐）。

用法:
  python patch_list_align.py input.docx [output.docx]
  如果只给一个参数，原地覆盖。
"""

import sys
import zipfile
import shutil
import tempfile
from pathlib import Path
from lxml import etree


NS = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
}


def patch_list_align(input_path: str, output_path: str) -> bool:
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        print(f"错误: 文件不存在: {input_path}", file=sys.stderr)
        return False

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        with zipfile.ZipFile(input_path, 'r') as z:
            z.extractall(tmp)

        doc_path = tmp / 'word' / 'document.xml'
        if not doc_path.exists():
            print("错误: 无效的 DOCX 文件", file=sys.stderr)
            return False

        tree = etree.parse(str(doc_path))
        root = tree.getroot()
        W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

        count = 0
        for p in root.iter(f'{{{W}}}p'):
            pPr = p.find(f'{{{W}}}pPr')
            if pPr is None:
                continue
            numPr = pPr.find(f'{{{W}}}numPr')
            if numPr is None:
                continue

            # 已经有 jc 的，检查并更新；没有的创建
            jc = pPr.find(f'{{{W}}}jc')
            if jc is not None:
                if jc.get(f'{{{W}}}val') != 'both':
                    jc.set(f'{{{W}}}val', 'both')
                    count += 1
            else:
                jc = etree.SubElement(pPr, f'{{{W}}}jc')
                jc.set(f'{{{W}}}val', 'both')
                count += 1

        if count == 0:
            print("未找到需要修改的列表段落。")
            if input_path != output_path:
                shutil.copy2(str(input_path), str(output_path))
            return True

        tree.write(str(doc_path), xml_declaration=True, encoding='UTF-8',
                   standalone=True)

        if output_path.exists():
            output_path.unlink()
        with zipfile.ZipFile(str(output_path), 'w', zipfile.ZIP_DEFLATED) as zout:
            for fpath in sorted(tmp.rglob('*')):
                if fpath.is_file() and fpath.name != '':
                    arcname = str(fpath.relative_to(tmp))
                    zout.write(str(fpath), arcname)

        print(f"完成: {count} 个列表段落已改为两端对齐 -> {output_path}")
        return True


def main():
    argc = len(sys.argv)
    if argc < 2 or argc > 3:
        print("用法: python patch_list_align.py input.docx [output.docx]",
              file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if argc >= 3 else input_path

    success = patch_list_align(input_path, output_path)
    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()

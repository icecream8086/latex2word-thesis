#!/usr/bin/env python3
"""
patch_heading_style.py — 移除 DOCX 中 Heading 1 样式的强制分页

ref.docx 的 Heading 1 定义了 pageBreakBefore，导致每个 section
在 Word 中都强制新页开始。连续短章节时会出现空白页。

本补丁移除 styles.xml 中 Heading 1 的 pageBreakBefore，
同时保留 keepNext（与下一段同页）和 keepLines（段内不分页）。

用法:
  python patch_heading_style.py input.docx [output.docx]
"""

import sys
import zipfile
import shutil
import tempfile
from pathlib import Path
from lxml import etree


NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W = NS['w']


def patch_heading_style(input_path: str, output_path: str) -> bool:
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        print(f"错误: 文件不存在: {input_path}", file=sys.stderr)
        return False

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        with zipfile.ZipFile(input_path, 'r') as z:
            z.extractall(tmp)

        sty_path = tmp / 'word' / 'styles.xml'
        if not sty_path.exists():
            print("错误: 无效的 DOCX 文件（缺少 styles.xml）", file=sys.stderr)
            if input_path != output_path:
                shutil.copy2(str(input_path), str(output_path))
            return True

        tree = etree.parse(str(sty_path))
        root = tree.getroot()

        count = 0
        for style in root:
            if style.tag != f'{{{W}}}style':
                continue
            sid = style.get(f'{{{W}}}styleId')
            if sid not in ('1', 'Heading1'):
                continue
            pPr = style.find(f'{{{W}}}pPr')
            if pPr is not None:
                pb = pPr.find(f'{{{W}}}pageBreakBefore')
                if pb is not None:
                    pPr.remove(pb)
                    count += 1
                    name_el = style.find(f'{{{W}}}name')
                    name = name_el.get(f'{{{W}}}val') if name_el is not None else sid
                    print(f"  已移除 '{name}' 的 pageBreakBefore")

        if count == 0:
            print("未找到需要移除的 pageBreakBefore。")
            if input_path != output_path:
                shutil.copy2(str(input_path), str(output_path))
            return True

        tree.write(str(sty_path), xml_declaration=True, encoding='UTF-8',
                   standalone=True)

        if output_path.exists():
            output_path.unlink()
        with zipfile.ZipFile(str(output_path), 'w', zipfile.ZIP_DEFLATED) as zout:
            for fpath in sorted(tmp.rglob('*')):
                if fpath.is_file():
                    arcname = str(fpath.relative_to(tmp))
                    zout.write(str(fpath), arcname)

        print(f"完成 -> {output_path}")
        return True


def main():
    argc = len(sys.argv)
    if argc < 2 or argc > 3:
        print("用法: python patch_heading_style.py input.docx [output.docx]",
              file=sys.stderr)
        sys.exit(1)
    input_path = sys.argv[1]
    output_path = sys.argv[2] if argc >= 3 else input_path
    if not patch_heading_style(input_path, output_path):
        sys.exit(1)


if __name__ == '__main__':
    main()

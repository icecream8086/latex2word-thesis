"""
patch_strip_spaces.py - 移除正文 XML 中所有 ASCII 空格 (U+0020)

在 LaTeX→pandoc 转换过程中，公式、引用等周围可能残留多余空格。
本补丁遍历 document.xml 的 w:t 文本节点（跳过 w:instrText 域代码），
移除所有 ASCII 空格，使中文排版更紧凑。

用法：python patch_strip_spaces.py <输入文件> [输出文件]
"""

import sys
import os
import zipfile
import shutil
from lxml import etree

NS_W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = f'{{{NS_W}}}'


def _strip_in_xml(xml: bytes) -> tuple[bytes, int]:
    """移除 XML 中 w:t 元素内所有 ASCII 空格，返回 (new_xml, count)"""
    root = etree.fromstring(xml)
    count = 0
    for t in root.iter(f'{NS}t'):
        if not t.text:
            continue
        parent = t.getparent()
        if parent is not None and parent.tag == f'{NS}instrText':
            continue
        stripped = t.text.replace(' ', '')
        if len(stripped) != len(t.text):
            t.text = stripped
            count += 1
    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True), count


def patch_strip_spaces(input_path: str, output_path: str) -> int:
    """解压 docx → 处理 document.xml → 重新打包"""
    tmp = os.path.join(os.path.dirname(output_path) or '.', '~tmp_strip_spaces')
    os.makedirs(tmp, exist_ok=True)
    try:
        with zipfile.ZipFile(input_path, 'r') as z:
            z.extractall(tmp)

        total = 0
        for fname in ('word/document.xml',):
            fpath = os.path.join(tmp, fname)
            if not os.path.exists(fpath):
                continue
            with open(fpath, 'rb') as f:
                xml = f.read()
            new_xml, n = _strip_in_xml(xml)
            if n:
                with open(fpath, 'wb') as f:
                    f.write(new_xml)
                total += n

        if output_path != input_path or not zipfile.is_zipfile(output_path):
            if os.path.exists(output_path):
                os.remove(output_path)
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:
                for root, _dirs, files in os.walk(tmp):
                    for fn in files:
                        fpath = os.path.join(root, fn)
                        arcname = os.path.relpath(fpath, tmp)
                        zout.write(fpath, arcname)
        else:
            # 原地修改：重新打包覆盖
            tmp_out = output_path + '.tmp'
            with zipfile.ZipFile(tmp_out, 'w', zipfile.ZIP_DEFLATED) as zout:
                for root, _dirs, files in os.walk(tmp):
                    for fn in files:
                        fpath = os.path.join(root, fn)
                        arcname = os.path.relpath(fpath, tmp)
                        zout.write(fpath, arcname)
            shutil.move(tmp_out, output_path)

        print(f'  已移除 {total} 个空格')
        return total
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    inp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else inp
    if not os.path.exists(inp):
        print(f'错误: 文件不存在 {inp}')
        sys.exit(1)
    patch_strip_spaces(inp, out)

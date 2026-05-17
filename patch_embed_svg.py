#!/usr/bin/env python3
"""
patch_embed_svg.py — 将 Pandoc 生成的 DOCX 中的光栅化图片替换为原生 SVG

原理：
  1. Pandoc 转 DOCX 时会将 SVG 光栅化为 PNG（通过 rsvg-convert），
     但 <wp:docPr descr="..."> 属性中保留了原始 SVG 路径。
  2. 本脚本扫描 DOCX XML，找到这些 SVG 路径，
     将原始 SVG 文件嵌入 word/media/，并更新引用关系，
     实现 Word 中原生内嵌矢量图。

用法:
  python patch_embed_svg.py input.docx [output.docx]
  如果只给一个参数，原地覆盖。
"""

import sys
import zipfile
import shutil
import tempfile
from pathlib import Path
from lxml import etree

# OOXML 命名空间
NS = {
    'w':   'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'wp':  'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'r':   'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
    'a':   'http://schemas.openxmlformats.org/drawingml/2006/main',
    'rel': 'http://schemas.openxmlformats.org/package/2006/relationships',
}
CONTENT_TYPES_NS = 'http://schemas.openxmlformats.org/package/2006/content-types'


def embed_svg(input_path: str, output_path: str) -> bool:
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        print(f"错误: 文件不存在: {input_path}", file=sys.stderr)
        return False

    # 快速预检：document.xml 中是否含 .svg，不含则跳过
    is_file_mode = not input_path.is_dir()
    if is_file_mode:
        with zipfile.ZipFile(input_path, 'r') as z:
            doc_xml_raw = z.read('word/document.xml')
    else:
        doc_xml_raw = Path(input_path / 'word' / 'document.xml').read_bytes()
    if b'.svg' not in doc_xml_raw:
        print("未找到需要替换的 SVG 图片。")
        if is_file_mode and input_path != output_path:
            shutil.copy2(str(input_path), str(output_path))
        return True

    if is_file_mode:
        tmpdir_obj = tempfile.TemporaryDirectory()
        tmp = Path(tmpdir_obj.name)
        with zipfile.ZipFile(input_path, 'r') as z:
            z.extractall(tmp)
        need_cleanup = True
    else:
        tmp = input_path
        need_cleanup = False

    try:
        doc_path = tmp / 'word' / 'document.xml'
        rels_path = tmp / 'word' / '_rels' / 'document.xml.rels'
        ct_path = tmp / '[Content_Types].xml'

        if not doc_path.exists() or not rels_path.exists():
            print("错误: 无效的 DOCX 文件（缺少 document.xml）", file=sys.stderr)
            return False

        doc_tree = etree.parse(str(doc_path))
        rels_tree = etree.parse(str(rels_path))
        ct_tree = etree.parse(str(ct_path)) if ct_path.exists() else None

        rel_map = {}
        for rel in rels_tree.findall('.//rel:Relationship', NS):
            rid = rel.get('Id')
            target = rel.get('Target', '')
            rel_map[rid] = target

        svg_rels = {}
        for blip in doc_tree.iter(f'{{{NS["a"]}}}blip'):
            rid = blip.get(f'{{{NS["r"]}}}embed')
            if not rid or rid not in rel_map:
                continue
            old_target = rel_map[rid]
            if not old_target.startswith('media/'):
                continue

            # 从 a:blip 向上走到 pic:pic，获取 cNvPr 中的 descr
            # a:blip → pic:blipFill → pic:pic → a:graphicData → a:graphic
            elem = blip
            pic_pic = None
            for _ in range(4):
                parent = elem.getparent()
                if parent is None:
                    break
                elem = parent
            else:
                # elem 现在是 a:graphic，往下找 pic:pic
                for child in elem.iterchildren():
                    tag = child.tag.split('}')[1] if '}' in child.tag else child.tag
                    if tag == 'graphicData':
                        for gchild in child.iterchildren():
                            gtag = gchild.tag.split('}')[1] if '}' in gchild.tag else gchild.tag
                            if gtag == 'pic':
                                pic_pic = gchild
                                break
                        break

            if pic_pic is None:
                continue

            # 在 pic:pic 中找 pic:nvPicPr/pic:cNvPr/@descr
            cnv_pr = pic_pic.find(f'{{{NS["pic"]}}}nvPicPr/{{{NS["pic"]}}}cNvPr')
            if cnv_pr is None:
                continue
            descr = cnv_pr.get('descr', '')
            if not descr.endswith('.svg'):
                continue

            svg_src = Path(descr)
            if not svg_src.exists():
                print(f"  [跳过] SVG 不存在: {descr}", file=sys.stderr)
                continue
            svg_basename = Path(old_target).stem + '.svg'
            svg_dest = tmp / 'word' / 'media' / svg_basename
            try:
                shutil.copy2(str(svg_src), str(svg_dest))
            except Exception as e:
                print(f"  [错误] 复制 SVG 失败: {svg_src} -> {svg_dest}: {e}", file=sys.stderr)
                continue
            svg_rels[rid] = f'media/{svg_basename}'
            print(f"  [SVG] {descr} -> word/media/{svg_basename}")

        if not svg_rels:
            if is_file_mode and input_path != output_path:
                shutil.copy2(str(input_path), str(output_path))
            return True

        for rel in rels_tree.findall('.//rel:Relationship', NS):
            rid = rel.get('Id')
            if rid in svg_rels:
                rel.set('Target', svg_rels[rid])

        if ct_tree is not None:
            root = ct_tree.getroot()
            existing = root.findall(f'{{http://schemas.openxmlformats.org/package/2006/content-types}}Default')
            has_svg_ct = any(e.get('Extension') == 'svg' for e in existing)
            if not has_svg_ct:
                svg_ct = etree.SubElement(root, f'{{{CONTENT_TYPES_NS}}}Default')
                svg_ct.set('Extension', 'svg')
                svg_ct.set('ContentType', 'image/svg+xml')

        doc_tree.write(str(doc_path), xml_declaration=True, encoding='UTF-8', standalone=True)
        rels_tree.write(str(rels_path), xml_declaration=True, encoding='UTF-8', standalone=True)
        if ct_tree is not None:
            ct_tree.write(str(ct_path), xml_declaration=True, encoding='UTF-8', standalone=True)

        if is_file_mode:
            if output_path.exists():
                output_path.unlink()
            with zipfile.ZipFile(str(output_path), 'w', zipfile.ZIP_DEFLATED) as zout:
                for fpath in sorted(tmp.rglob('*')):
                    if fpath.is_file():
                        arcname = str(fpath.relative_to(tmp))
                        zout.write(str(fpath), arcname)

        print(f"完成: {len(svg_rels)} 个 SVG 已嵌入 -> {output_path}")
        return True
    finally:
        if need_cleanup:
            tmpdir_obj.cleanup()


def main():
    argc = len(sys.argv)
    if argc < 2 or argc > 3:
        print("用法: python patch_embed_svg.py input.docx [output.docx]", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if argc >= 3 else input_path

    success = embed_svg(input_path, output_path)
    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()

import sys
import os
import re
import zipfile
import shutil
from docx import Document


def auto_fit_tables(input_path, output_path):
    """
    通过直接操作 XML 将所有表格宽度设置为页面宽度（自动适应窗口）。
    替换原来 autoexec.py 中 Win32 COM 的 AutoFitBehavior(2) 调用。
    """
    tmp_dir = os.path.join(os.path.dirname(output_path) or ".", "~tmp_docx_fix")
    os.makedirs(tmp_dir, exist_ok=True)

    try:
        # 1. 解压 docx
        with zipfile.ZipFile(input_path, 'r') as zip_in:
            zip_in.extractall(tmp_dir)

        # 2. 修改 document.xml 中的表格属性
        doc_path = os.path.join(tmp_dir, "word", "document.xml")
        with open(doc_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()

        # 将 w:tblW 从 auto/0 改为 100% 页面宽度 (5000 pct = 100%)
        xml_content = re.sub(
            r'<w:tblW\s+w:type="auto"\s+w:w="0"\s*/>',
            '<w:tblW w:w="5000" w:type="pct"/>',
            xml_content
        )

        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)

        # 3. 重新打包为 docx
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
    将文档中所有图片标题样式的段落设置为加粗
    
    Args:
        input_path: 输入文档路径
        output_path: 输出文档路径
    """
    # 1. 打开文档
    doc = Document(input_path)

    # 2. 遍历所有段落，找到图片标题
    # 常见的图片标题样式名称: "Figure Caption", "图片标题", "Caption", "Image Caption"
    figure_caption_styles = ["Figure Caption", "图片标题", "Caption", "Image Caption"]
    
    modified_count = 0
    
    for paragraph in doc.paragraphs:
        style_name = paragraph.style.name
        
        # 检查是否为图片标题样式
        is_figure_caption = any(style_name == style for style in figure_caption_styles)
        
        # 或者通过段落文本特征判断（可选，增强兼容性）
        if not is_figure_caption:
            text = paragraph.text.lower().strip()
            # 常见图片标题特征：以"图"、"Figure"、"Fig."等开头
            if text and (text.startswith("图") or text.startswith("figure") or text.startswith("fig.")):
                is_figure_caption = True
        
        if is_figure_caption:
            # 3. 合并段落内的所有runs，然后重新设置整个段落为加粗
            if paragraph.runs:
                # 获取该段落的所有文本
                full_text = paragraph.text
                # 移除编号后的冒号，如 "图4.1: " → "图4.1 "
                full_text = re.sub(r'^(图[\d.]+)[：:]\s*', r'\1 ', full_text)
                # 清除原有内容
                paragraph.clear()
                # 重新添加整个文本，并设置为加粗
                run = paragraph.add_run(full_text)
                run.bold = True
                # 保持原有的段落样式
                if paragraph.style.name != "Normal":
                    paragraph.style = style_name
                modified_count += 1
    
    # 4. 保存修改后的文档
    doc.save(output_path)
    print(f"处理完成，共修改了 {modified_count} 个图片标题")
    print(f"已保存至: {output_path}")

if __name__ == "__main__":
    # 支持命令行参数: python script.py <输入文件> [输出文件]
    if len(sys.argv) < 2:
        print("用法: python fix_figure_caption.py <输入文件> [输出文件]")
        print("示例: python fix_figure_caption.py input.docx output.docx")
        print("      python fix_figure_caption.py input.docx  # 自动生成 input_fixed.docx")
        sys.exit(1)

    input_file = sys.argv[1]

    # 如果未提供输出文件，自动生成：原文件名_fixed.docx
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}_fixed{ext}"

    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"错误: 输入文件不存在 - {input_file}")
        sys.exit(1)

    # 第一步：表格自动适应窗口（替换原来的 autoexec.py）
    auto_fit_tables(input_file, output_file)
    # 第二步：图片标题加粗
    fix_figure_caption_bold(output_file, output_file)
"""
gen_bibl.py - 从 bib 文件自动生成 99.bibl.tex

功能：
1. 扫描所有 .tex 文件，提取所有 \cite{key} 中的 key
2. 从 bibl/fake_ref.bib 中读取对应的 BibTeX 条目
3. 生成 99.bibl.tex 文件（thesisbibl 环境）
4. 只包含被引用的条目，不包含未引用的条目

使用方法：
    python gen_bibl.py
"""

import re
import os
import glob

# 配置
BIB_FILE = "bibl/fake_ref.bib"
OUTPUT_FILE = "99.bibl.tex"
TEX_FILES = glob.glob("*.tex")  # 扫描所有 .tex 文件


def extract_cite_keys(tex_files):
    """从 .tex 文件中提取所有 \cite{key} 中的 key，保持出现顺序"""
    cite_keys = []
    seen = set()
    cite_pattern = re.compile(r'\\cite\{([^}]+)\}')

    for tex_file in tex_files:
        if not os.path.exists(tex_file):
            continue
        with open(tex_file, 'r', encoding='utf-8') as f:
            content = f.read()
            matches = cite_pattern.findall(content)
            for match in matches:
                # 处理多个引用: \cite{key1,key2,key3}
                keys = [k.strip() for k in match.split(',')]
                for key in keys:
                    if key not in seen:
                        cite_keys.append(key)
                        seen.add(key)

    return cite_keys


def parse_bib_file(bib_file):
    """解析 bib 文件，返回 {key: (entry_type, body)} 的字典"""
    if not os.path.exists(bib_file):
        print(f"警告: bib 文件 {bib_file} 不存在")
        return {}

    entries = {}
    with open(bib_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 匹配每个 BibTeX 条目
    entry_pattern = re.compile(r'@(\w+)\{(\w+),\s*(.*?)\n\}', re.DOTALL)
    matches = entry_pattern.findall(content)

    for entry_type, key, body in matches:
        entries[key] = (entry_type, body.strip())

    return entries


def bib_to_bibitem(entry_type, body, key):
    """将 BibTeX 条目转换为 \bibitem 格式"""
    # 解析字段
    fields = {}
    field_pattern = re.compile(r'(\w+)\s*=\s*\{(.*?)\}', re.DOTALL)
    for match in field_pattern.finditer(body):
        field_name = match.group(1).lower()
        field_value = match.group(2).strip()
        fields[field_name] = field_value

    # 根据条目类型生成不同的格式
    title = fields.get('title', '')
    author = fields.get('author', '')
    year = fields.get('year', '')
    journal = fields.get('journal', '')
    publisher = fields.get('publisher', '')
    address = fields.get('address', '')
    volume = fields.get('volume', '')
    number = fields.get('number', '')
    pages = fields.get('pages', '')
    school = fields.get('school', '')
    url = fields.get('url', '')
    doi = fields.get('doi', '')
    urldate = fields.get('urldate', '')

    # URL / DOI 后缀
    url_suffix = ""
    if doi:
        url_suffix = f" \\url{{https://doi.org/{doi}}}"
    elif url:
        url_suffix = f" \\url{{{url}}}"
    if urldate and url_suffix:
        url_suffix += f" (访问日期: {urldate})"

    # 格式化作者
    if ' and ' in author:
        authors = author.replace(' and ', ',')
    else:
        authors = author

    # 根据条目类型生成 bibitem
    if entry_type == 'article':
        # 期刊文章 [J]
        vol_info = f", {volume}({number})" if volume and number else ""
        page_info = f": {pages}" if pages else ""
        return f"        \\bibitem{{{key}}} {authors}. {title}[J]. {journal}, {year}{vol_info}{page_info}.{url_suffix}"
    elif entry_type == 'book':
        # 书籍 [M]
        addr_info = f"{address}: " if address else ""
        page_info = f": {pages}" if pages else ""
        return f"        \\bibitem{{{key}}} {authors}. {title}[M]. {addr_info}{publisher}, {year}{page_info}.{url_suffix}"
    elif entry_type == 'phdthesis':
        # 博士论文 [D]
        addr_info = f"{address}: " if address else ""
        page_info = f": {pages}" if pages else ""
        return f"        \\bibitem{{{key}}} {authors}. {title}[D]. {addr_info}{school}, {year}{page_info}.{url_suffix}"
    elif entry_type == 'techreport':
        # 技术报告 [R]
        addr_info = f"{address}: " if address else ""
        page_info = f": {pages}" if pages else ""
        return f"        \\bibitem{{{key}}} {authors}. {title}[R]. {addr_info}{publisher or school}, {year}{page_info}.{url_suffix}"
    elif entry_type == 'standard':
        # 标准 [S]
        addr_info = f"{address}: " if address else ""
        return f"        \\bibitem{{{key}}} {title}: {number}[S]. {addr_info}{publisher}, {year}.{url_suffix}"
    elif entry_type == 'misc':
        # 其他 [Z]
        page_info = f": {pages}" if pages else ""
        return f"        \\bibitem{{{key}}} {authors}. {title}[Z]. {year}{page_info}.{url_suffix}"
    elif entry_type == 'patent':
        # 专利 [P]
        suffix = url_suffix or ""
        return f"        \\bibitem{{{key}}} {authors}. {title}[P]. {fields.get('country', '')}专利: {fields.get('number', '')}, {fields.get('date', year)}.{suffix}"
    elif entry_type == 'incollection':
        # 论文集中的文章 [A]
        booktitle = fields.get('booktitle', '')
        editor = fields.get('editor', '')
        addr_info = f"{address}: " if address else ""
        page_info = f": {pages}" if pages else ""
        editor_info = f"In {editor}(eds.). " if editor else ""
        return f"        \\bibitem{{{key}}} {authors}. ``{title}''[A]. {editor_info}{booktitle}[C]. {addr_info}{publisher}, {year}{page_info}.{url_suffix}"
    elif entry_type == 'collection':
        # 论文集 [C]
        addr_info = f"{address}: " if address else ""
        page_info = f": {pages}" if pages else ""
        return f"        \\bibitem{{{key}}} {authors}. {title}[C]. {addr_info}{publisher}, {year}{page_info}.{url_suffix}"
    else:
        # 通用格式
        return f"        \\bibitem{{{key}}} {authors}. {title}[J]. {year}.{url_suffix}"


def generate_bibl_tex(cite_keys, bib_entries, output_file):
    """生成 99.bibl.tex 文件

    生成 thesisbibl 环境，包含 \bibitem 命令。
    用于 LaTeX 编译，避免引用未定义的警告。
    在 Word 转换中，使用过滤器移除 citeproc 生成的参考文献列表，
    只保留 99.bibl.tex 中的参考文献。
    """
    lines = []
    lines.append("% 99.bibl.tex - 参考文献 (由 gen_bibl.py 自动生成)")
    lines.append("% 此文件包含 \bibitem 命令，用于 LaTeX 编译")
    lines.append("% 在 Word 转换中，使用过滤器移除 citeproc 生成的参考文献列表")
    lines.append("")
    
    lines.append("\\begin{thesisbibl}")
    
    # 只包含被引用的条目
    # 编号从 1 开始
    for idx, key in enumerate(cite_keys, 1):
        if key in bib_entries:
            entry_type, body = bib_entries[key]
            # 生成带 \bibitem 的内容
            content = bib_to_bibitem(entry_type, body, key)
            # 只生成 \bibitem{key}，不添加 [idx]，因为 LaTeX 的 thebibliography 环境会自动生成编号
            lines.append(f"    {content}")
            lines.append("")  # 空行
        else:
            print(f"警告: 引用 {key} 在 bib 文件中未找到")

    lines.append("\\end{thesisbibl}")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
        f.write('\n')

    print(f"已生成 {output_file}")


def main():
    print("正在扫描 .tex 文件中的引用...")
    cite_keys = extract_cite_keys(TEX_FILES)
    print(f"找到 {len(cite_keys)} 个引用: {', '.join(cite_keys)}")

    print(f"正在解析 {BIB_FILE}...")
    bib_entries = parse_bib_file(BIB_FILE)
    print(f"找到 {len(bib_entries)} 个 bib 条目")

    print(f"正在生成 {OUTPUT_FILE}...")
    generate_bibl_tex(cite_keys, bib_entries, OUTPUT_FILE)
    print("完成!")


if __name__ == "__main__":
    main()

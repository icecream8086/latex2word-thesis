# 补丁包控制流图

## 整体调用关系（out.ps1 → patch 链）

```mermaid
flowchart LR
    subgraph Stage2["阶段5: Pandoc 生成 DOCX"]
        PANDOC["pandoc → out.docx"]
    end

    subgraph PatchChain["阶段6: 9个补丁顺序执行"]
        direction TB
        P1["patch_figure_caption.py"]
        P2["patch_table_caption.py"]
        P3["patch_thanks.py"]
        P4["patch_abstract.py"]
        P5["patch_bibliography.py"]
        P6["patch_pagenum.py"]
        P7["patch_toc.py"]
        P8["patch_margin.py"]
        P9["patch_header.py"]
    end

    subgraph Finish["打开文档"]
        OPEN["Start-Process out.docx"]
    end

    PANDOC --> P1 --> P2 --> P3 --> P4 --> P5 --> P6 --> P7 --> P8 --> P9
    
    P1 -->|失败| E1["exit 1"]
    P2 -->|失败| E1
    P3 -->|失败| E1
    P4 -->|失败| E1
    P5 -->|失败| E1
    P6 -->|失败| E1
    P7 -->|失败| E1
    P8 -->|失败| E1
    P9 -->|失败| E1
    P9 -->|成功| OPEN

    classDef fail fill:#ffebee,stroke:#c62828
    classDef patch fill:#e1f5fe,stroke:#0288d1
    class E1 fail
```

## 每个补丁的内部控制流

### 1. patch_figure_caption.py — 图片标题加粗 & 表格自适应

```mermaid
flowchart TB
    A(["patch_figure_caption.py in.docx out.docx"])
    A --> B["auto_fit_tables()"]
    
    subgraph Fit["表格自适应窗口"]
        B1["解压 docx → ~tmp_docx_fix/"]
        B1 --> B2["读取 word/document.xml"]
        B2 --> B3["正则替换 tblW\nw:type='auto' → w:type='pct'\nw:w='0' → w:w='5000'"]
        B3 --> B4["重新打包为 docx"]
    end

    B --> Fit
    Fit --> C["fix_figure_caption_bold()"]

    subgraph Bold["图片标题加粗"]
        C1["用 python-docx 遍历所有段落"]
        C1 --> C2{"样式匹配 ?\nFigure Caption / 图片标题\n/ Caption / Image Caption"}
        C2 -->|是| C3["加粗"]
        C2 -->|否| C4{"文本匹配 ?\n以'图'/'Figure'/'Fig.'开头"}
        C4 -->|是| C3
        C4 -->|否| C5["跳过"]
        C3 --> C6["合并所有 runs → 一条 run\n设置 bold=True"]
    end

    C --> Bold
    Bold --> D(["输出 out.docx"])
```

### 2. patch_table_caption.py — 表格标题加粗 & 超链接解析

```mermaid
flowchart TB
    A(["patch_table_caption.py in.docx out.docx"])
    A --> B{控制变量开关}
    
    B -->|RESOLVE_HYPERLINKS=True| C["resolve_hyperlink_fields()"]
    subgraph Hyp["超链接域代码 → w:hyperlink"]
        C1["遍历段落\n找 fldChar begin/separate/end 三元组"]
        C1 --> C2["提取 instrText 中的 HYPERLINK 参数\n如 \\l 'bookmark_name'"]
        C2 --> C3["取 separate~end 间的 run 作为链接文本"]
        C3 --> C4["创建 w:hyperlink 元素\n设置 w:anchor=bookmark"]
        C4 --> C5["替换：在 begin 位置插入 hyperlink\n删除 begin~end 域代码元素"]
    end
    C --> Hyp

    B -->|BOLD_CAPTION=True| D["fix_caption_bold()"]
    subgraph TblBold["表格标题加粗（非破坏性）"]
        D1["遍历段落\nstyle='Table Caption'"]
        D1 --> D2["对段落内每个 w:r\n直接在 rPr 中添加 w:b 元素"]
    end
    D --> TblBold

    B -->|AUTO_FIT_TABLES=False| E["（跳过表格自适应）"]

    Hyp --> TblBold --> E
    E --> F["doc.save() → out.docx"]
```

### 3. patch_thanks.py — 致谢/摘要/目录标题格式化

```mermaid
flowchart TB
    A(["patch_thanks.py in.docx out.docx"])
    A --> B["python-docx 遍历所有段落"]
    
    B --> C{"_strip_spaces(text)"}
    C -->|"'致谢'"| D["_format_as_chapter_title()"]
    C -->|"'摘要'"| E["_format_as_chapter_title()"]
    C -->|"'目录'"| F["_format_as_chapter_title()"]
    C -->|其他| G["跳过"]

    subgraph Format["_format_as_chapter_title(display_text)"]
        D1["clear() 清空段落"]
        D1 --> D2["add_run('致　　谢')\n间距=TITLE_SPACING='    '"]
        D2 --> D3["设置字体: SimHei（黑体）"]
        D3 --> D4["设置字号: 18pt（小二）"]
        D4 --> D5["bold=True, 居中"]
        D5 --> D6["首行缩进=0"]
        D6 --> D7["添加 pageBreakBefore 分页"]
        D7 --> D8["删除 outlineLvl 和 numPr\n（避免编号，保留 Heading 1 样式）"]
        D8 --> D9["style = 'heading 1'"]
    end

    D --> Format
    E --> Format
    F --> Format

    Format --> H["doc.save() → out.docx"]
```

### 4. patch_abstract.py — 中英文关键词格式化

```mermaid
flowchart TB
    A(["patch_abstract.py in.docx out.docx"])
    A --> B["python-docx 遍历段落，追踪区域状态"]
    
    B --> C{cleaned text}
    C -->|"'摘要'"| D["进入中文摘要区域\nin_cn=True, in_en=False"]
    C -->|"'Abstract'"| E["进入英文摘要区域\nin_cn=False, in_en=True"]
    C -->|"Heading 样式且 in_en"| F["退出英文摘要"]
    C -->|"非空文本且 in_cn"| G["cn_kw_para = 当前段落"]
    C -->|"非空文本且 in_en"| H["en_kw_para = 当前段落"]

    D --> I{"cn_kw_para 含'；'?"}
    I -->|是| J["_format_cn_keywords()"]
    J --> J1["clear() 清空 runs"]
    J1 --> J2["add_run('关键词：')\nSimHei, 12pt, bold"]
    J2 --> J3["add_run(原文内容)\nSimSun, 12pt, normal"]
    J3 --> J4["首行缩进 24pt"]

    E --> K["_format_en_keywords()"]
    K --> K1["clear() 清空 runs"]
    K1 --> K2["add_run('Key words: ')\nTimes New Roman, 12pt, bold"]
    K2 --> K3["add_run(原文内容)\nTimes New Roman, 12pt, bold"]
    K3 --> K4["首行缩进 24pt"]

    I -->|否| L["跳过（无法确认是关键词）"]
    J --> M["doc.save() → out.docx"]
    K --> M
```

### 5. patch_bibliography.py — 参考文献编号/字体/超链接

```mermaid
flowchart TB
    A(["patch_bibliography.py in.docx out.docx"])
    A --> B["python-docx 遍历段落"]
    
    B --> C{text}
    C -->|"'Abstract'"| D["_format_as_chapter_title()\n黑体小二居中分页"]
    C -->|"'参考文献'"| E["_format_as_chapter_title()\n黑体小二居中分页"]

    E --> F{FORMAT_BIBLIOGRAPHY}
    F -->|是| G{"段落以 '[' 开头?"}
    G -->|否| H["添加编号 [1] [2] ...\nclear() → add_run('[n] 原文')\n字体 SimSun, 12pt"]
    G -->|是| I["保持现有编号\n各 run 设 SimSun, 12pt"]
    H --> J["set_indent_zero()\nfirstLine=0"]
    I --> J

    F -->|是| K{URL_HYPERLINK}
    K -->|是| L["make_urls_clickable()"]

    subgraph URL["URL → 超链接"]
        L1["正则 URL_PATTERN 匹配 https?://..."]
        L1 --> L2["URL_PATTERN.split() 分段"]
        L2 --> L3["偶数索引 → 普通 run 文本\n奇数索引 → w:hyperlink 元素\n蓝色 #0563C1 + 下划线"]
    end

    L --> URL
    URL --> M["doc.save() → out.docx"]
```

### 6. patch_pagenum.py — 复合页码（罗马/阿拉伯 + 分节页脚）

```mermaid
flowchart TB
    A(["patch_pagenum.py in.docx out.docx"])
    A --> B["阶段一: 读 docx 为 ZIP dict\ncontent[name] = bytes"]

    B --> C["_clean_old_footers()\n清除所有旧页脚文件/引用/CT"]
    C --> D["_find_ch1_start_index()\npython-docx 找第一个非正文前\nHeading 1 的段落索引"]

    D --> E["_fix_sections_in_package()"]
    subgraph FixSec["修复分节符"]
        E1["移除所有段落级 sectPr"]
        E1 --> E2["保留最后一个 body sectPr"]
        E2 --> E3["在 ch1_index 前插入分节符段落\nsectPr type=oddPage\n复制 pgSz/pgMar/cols"]
        E3 --> E4["移除 ch1_index 段落的 pageBreakBefore"]
    end

    E --> FixSec
    E --> F["写回 → 重新读取 → 统计节数\n（需通过 python-docx 读 sections）"]

    F --> G["_set_pg_num_type()"]
    subgraph Num["设置页码格式"]
        G --> G1{"第 i 节是正文前?"}
        G1 -->|是| G2["pgNumType fmt=upperRoman\nstart=1 → Ⅰ,Ⅱ,Ⅲ"]
        G1 -->|否| G3["pgNumType fmt=decimal\nstart=1 → 1,2,3"]
    end

    G --> Num
    G --> H["_set_footer_distance(851 twips = 1.5cm)"]

    H --> I["_inject_footer() × N 次"]
    subgraph Inj["注入页脚"]
        I1{"正文前节?"}
        I1 -->|是| I2["default: PAGE 域（居中）\nfirst: 空\n even: PAGE 域"]
        I1 -->|否| I3["default: PAGE 域（居中）\neven: PAGE 域"]
        I2 --> I4["为每个页脚:\n    ① 创建 footer{num}.xml\n    (PAGE 域代码/fldChar)\n    ② 更新 Content_Types\n    ③ 添加 rel 关系\n    ④ 添加 footerReference"]
        I3 --> I4
    end

    I --> Inj
    I --> J["写回 ZIP → out.docx"]

    subgraph FooterXML["页脚 XML 结构"]
        K1["<w:ftr>"]
        K1 --> K2["<w:p>"]
        K2 --> K3["<w:fldChar w:fldCharType='begin'/>"]
        K3 --> K4["<w:instrText> PAGE </w:instrText>"]
        K4 --> K5["<w:fldChar w:fldCharType='separate'/>"]
        K5 --> K6["<w:fldChar w:fldCharType='end'/>"]
        K6 --> K7["</w:p>"]
    end
```

### 7. patch_toc.py — 目录生成（书签 + TOC 域 + 样式修补）

```mermaid
flowchart TB
    A(["patch_toc.py in.docx out.docx"])

    subgraph Ph1["阶段一: python-docx"]
        B["在段落中找 '目　录'"]
        B --> C{"找到?"}
        C -->|否| D["在文档开头新建 '目　　录' 段落"]
        C -->|是| E["_clear_toc_area()\n删除 目　录 → 首个 H1 之间的旧段落"]
        D --> F
        E --> F

        F["扫描标题目录"]
        F --> G["对每个标题\n（排除 目　录 和 摘要/Abstract 等正文前）"]
        G --> H["_find_or_create_bookmark()\n创建 bookmarStart/End\n标签: _Toc_{clean_text}"]
        H --> I["_create_toc_field_para()"]
        I --> J["TOC 域代码段落:\nTOC \\o '1-3' \\h \\z \\u"]
        J --> K["插入到 目　录 段落之后"]
        K --> L["doc.save()"]
    end

    subgraph Ph2["阶段二: zipfile 修补 styles.xml"]
        M["读 docx 为 ZIP dict"]
        M --> N["_patch_toc_styles()"]
        N --> O["TOC1: indent=0, bold\nTOC2: indent=420, bold\nTOC3: indent=840, not bold"]
        O --> P["通用样式:\n  宋体 + Times New Roman\n  小四 12pt\n  点前导符右对齐 tab\n  1.5 倍行距"]
        P --> Q["写回 styles.xml → 重新打包"]
    end

    Ph1 --> Ph2
    Q --> R(["out.docx"])
```

### 8. patch_margin.py — 页边距设置

```mermaid
flowchart TB
    A(["patch_margin.py in.docx out.docx"])
    A --> B["python-docx 遍历所有 section"]
    
    B --> C["section.top_margin = Cm(2.20)"]
    C --> D["section.bottom_margin = Cm(2.20)"]
    D --> E["section.left_margin = Cm(2.50)"]
    E --> F["section.right_margin = Cm(2.50)"]
    F --> G["section.header_distance = Cm(1.20)"]
    G --> H["section.footer_distance = Cm(1.50)"]

    H --> I["doc.save() → out.docx"]
```

### 9. patch_header.py — 页眉文字 + LOGO

```mermaid
flowchart TB
    A(["patch_header.py in.docx out.docx"])
    A --> B["python-docx 遍历所有 section"]

    B --> C["检测页眉类型"]
    C --> D["header: 默认页眉"]
    D --> E{_has_title_pg?}
    E -->|是| F["first_page_header: 首页页眉"]
    E -->|否| G["跳过首页"]
    D --> H{_has_even_header?}
    H -->|是| I["even_page_header: 偶页页眉"]
    H -->|否| J["跳过偶页"]

    subgraph Write["_write_header(header)"]
        W1["_setup_header()\n清空 → is_linked_to_previous=True\n保留一个空段落"]
        W1 --> W2["居中"]
        W2 --> W3["add_run(HEADER_TEXT)"]
        W3 --> W4["字体: 宋体, 小五(9pt)"]
        W4 --> W5["_add_bottom_border()\n段落底部边框 single 0.75pt"]
        W5 --> W6{LOGO.png 存在?}
        W6 -->|是| W7["_add_floating_picture()\n绝对定位(相对页边距)\n四周型环绕\n大小 2cm×2cm"]
        W6 -->|否| W8["打印警告"]
    end

    D --> Write
    F --> Write
    I --> Write

    Write --> Y["doc.save() → out.docx"]
```

## 补丁链执行流水线

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 输入: out.docx（Pandoc 生成）                                            │
├──────────────────────────────────────────────────────────────────────────┤
│  1. patch_figure_caption.py                                              │
│     ├─ auto_fit_tables()        — 表格宽度 100% 页面（解压→XML→打包）   │
│     └─ fix_figure_caption_bold()— 图片标题加粗                           │
├──────────────────────────────────────────────────────────────────────────┤
│  2. patch_table_caption.py                                               │
│     ├─ resolve_hyperlink_fields()— HYPERLINK 域→w:hyperlink              │
│     └─ fix_caption_bold()       — Table Caption 加粗（非破坏性）         │
├──────────────────────────────────────────────────────────────────────────┤
│  3. patch_thanks.py                                                     │
│     └─ 致谢/摘要/目录 → Heading 1 + 黑体小二居中分页                     │
├──────────────────────────────────────────────────────────────────────────┤
│  4. patch_abstract.py                                                   │
│     └─ 中文"关键词："黑体加粗 + 英文"Key words:" TNR 加粗               │
├──────────────────────────────────────────────────────────────────────────┤
│  5. patch_bibliography.py                                               │
│     ├─ 参考文献 → Heading 1 标题                                        │
│     ├─ 条目编号 [1][2]... + 宋体12pt + 去缩进                           │
│     └─ URL 文本 → 可点击超链接（蓝色+下划线）                           │
├──────────────────────────────────────────────────────────────────────────┤
│  6. patch_pagenum.py                                                    │
│     ├─ 清除旧页脚                                                       │
│     ├─ 修复分节符（oddPage 分节）                                       │
│     ├─ 正文前: 大写罗马数字 ⅠⅡⅢ（第1节）                               │
│     ├─ 正文: 阿拉伯数字 1 2 3（第2节起）                                │
│     └─ 注入页脚 XML（PAGE 域代码）                                      │
├──────────────────────────────────────────────────────────────────────────┤
│  7. patch_toc.py                                                        │
│     ├─ 阶段一: 扫描标题→加书签→插入TOC域代码                            │
│     └─ 阶段二: 修补 styles.xml 中 TOC1/2/3 样式                         │
├──────────────────────────────────────────────────────────────────────────┤
│  8. patch_margin.py                                                     │
│     └─ 各节: 上2.20 下2.20 左2.50 右2.50 (cm)                          │
├──────────────────────────────────────────────────────────────────────────┤
│  9. patch_header.py                                                     │
│     └─ 各节页眉: 文字(宋体小五居中) + 底部边框 + LOGO(浮动绝对定位)    │
├──────────────────────────────────────────────────────────────────────────┤
│ 输出: out.docx（最终产物，自动打开）                                     │
└──────────────────────────────────────────────────────────────────────────┘
```

## 错误处理规则

```
┌──────────────────────────────────────────────────┐
│ 每个补丁通过 $LASTEXITCODE 传递状态               │
│                                                  │
│ out.ps1 中的调用模式:                             │
│   if ($LASTEXITCODE -eq 0) {                     │
│       python patch_xxx.py ...                     │
│   }                                               │
│   if ($LASTEXITCODE -eq 0) {                     │
│       python patch_yyy.py ...                     │
│   }                                               │
│                                                  │
│ → 任一补丁返回非零退出码，后续所有补丁全部跳过     │
│ → out.docx 停留在最后一个成功补丁的状态            │
│ → 不会自动打开文档                                │
└──────────────────────────────────────────────────┘
```

## 补丁类型分类

| 类型 | 脚本 | 操作模式 |
|------|------|----------|
| XML 直接操作 | patch_figure_caption (auto_fit), patch_pagenum, patch_toc (阶段二) | 解压 ZIP → 修改 XML → 重打包 |
| python-docx 高级 API | patch_figure_caption (bold), patch_table_caption, patch_thanks, patch_abstract, patch_bibliography, patch_margin, patch_header | Document() → 遍历段落/样式 → save() |
| 混合模式 | patch_toc | 阶段一 python-docx + 阶段二 ZIP/XML |

---

# 内联函数行为分析

## python-docx 内部函数对 OOXML 结构的副作用

### 1. `clear()` / `clear_runs()` — 段落 / run 重建

用于 `patch_figure_caption`(合并)、`patch_thanks`、`patch_abstract`、`patch_bibliography`、`patch_header`。

```python
paragraph.clear()          # 删除所有 w:r 子元素，保留 w:pPr
paragraph.add_run(text)    # 新建 w:r + w:t，pPr 中原有的 run 级属性丢失
```

**副作用**：
- 原段落中的 `w:rPr`（字体、字号、颜色、超链接样式）全部丢失
- `w:r` 中的 `w:rPr` 被完全重建，仅保留新设的属性
- 对 `patch_figure_caption`：合并 run → 丢失了不同 run 的独立格式（如一个加粗词变成整段加粗）
- `patch_header` 在段落级做了 `is_linked_to_previous = True`，这会清空页眉内容

### 2. `OxmlElement` + `append()` — 原生 XML 插入

用于 `patch_table_caption`、`patch_bibliography`(URL 超链接)、`patch_pagenum`、`patch_toc`、`patch_header`。

```python
rPr = OxmlElement("w:rPr")
bold = OxmlElement("w:b")
rPr.append(bold)
r_elem.insert(0, rPr)
```

**副作用**：
- 直接操作 `lxml` 树，绕过 python-docx 的验证层
- 如果某元素已有同名子元素，会创建重复（需要手动检查是否存在再添加）
- `patch_table_caption` 的 `_bold_run_element` 内置了查重逻辑；其它脚本需自行保证

### 3. `zipfile` 直接修改 — 二进制级替换

用于 `patch_figure_caption.auto_fit_tables()`、`patch_pagenum`、`patch_toc`(阶段二)。

```python
with zipfile.ZipFile(input_path, 'r') as z:
    content = {n: z.read(n) for n in z.namelist()}
# 修改 content['word/document.xml'] 等为字节串
with zipfile.ZipFile(output_path, 'w', ZIP_DEFLATED) as z:
    for name, data in content.items():
        z.writestr(name, data)
```

**副作用**：
- `ZIP_DEFLATED` 压缩级别不同 → 文件大小可能变化
- `writestr` 按文件名排序写入 → 包内文件顺序可能改变（OOXML 规范不要求顺序，但某些旧版 Word 敏感）
- `patch_pagenum` 会写回后立即用 `_read_zip` 重读，中间状态暴露在磁盘上

### 4. `xml.etree` / `lxml.etree` 解析 — XML 树修改

用于 `patch_figure_caption.auto_fit_tables()`（xml.etree + 正则）、`patch_pagenum`（lxml）、`patch_toc` 阶段二（lxml）。

```python
# patch_figure_caption 使用正则（非解析器）
xml_content = re.sub(r'<w:tblW\s+w:type="auto"\s+w:w="0"\s*/>', ...)
# patch_pagenum 使用 lxml 完整解析
root = etree.fromstring(content['word/document.xml'])
```

**正则方式的风险**（`patch_figure_caption.auto_fit_tables`）：
- 属性顺序变化导致匹配失败：`w:w="0" w:type="auto"` → 不匹配
- 命名空间前缀变化：如果 Pandoc 用不同前缀（如 `w:` → `w10:`），正则失效
- 注释或 CDATA 干扰匹配

### 5. 幂等性（Idempotency）分析

| 脚本 | 幂等 | 原因 |
|------|------|------|
| patch_figure_caption | 否 | 第一次合并 run，第二次找不到独立 run 但不会加重（safe） |
| patch_table_caption | 是 | `_bold_run_element` 检查 `w:b` 已存在则跳过；域代码转换后不再有域元素 |
| patch_thanks | 否 | `clear()` 后第二次匹配时段落已为空文本，`_strip_spaces` 返回空 → 跳过 |
| patch_abstract | 否 | 第一次 clear 后段落内容为空，第二次 `text.strip()` 为空 → 跳过 |
| patch_bibliography | 是 | 已以 `[` 开头的段落不再加编号；URL 已替换则正则不匹配 |
| patch_pagenum | 是 | `_clean_old_footers` 先清除所有旧页脚，再重建 |
| patch_toc | 是 | `_clear_toc_area` 先清空旧目录区域，再加新书签和 TOC 域 |
| patch_margin | 是 | 每次覆盖设置边距，无状态残留 |
| patch_header | 是 | `_setup_header` 清空页眉后再写入 |

---

# 对象生命周期分析

## 单次调用内部生命周期

```mermaid
flowchart LR
    subgraph Docx["OOXML 包 (ZIP) 生命周期"]
        IN["out.docx\n（磁盘上的 ZIP 文件）"]

        subgraph Read["读取阶段"]
            R1["python-docx: Document(path)\n→ 解压到内存 XML 树\n→ 构建 lxml ElementTree"]
            R2["zipfile: ZipFile(path, 'r')\n→ 全体解压为 dict[name]=bytes\n→ content 字典"]
        end

        subgraph Modify["修改阶段"]
            M1["python-docx: 遍历段落/表格\n修改 Element 属性\n插入/删除 XML 节点"]
            M2["zipfile: 修改 content dict\n中对应 XML 的 bytes"]
            M3["正则替换: 在 XML 字符串\n中做 re.sub"]
        end

        subgraph Write["写出阶段"]
            W1["python-docx: doc.save(path)\n→ 整个 ZIP 重建\n→ 丢失部分 OOXML 结构"]
            W2["zipfile: ZipFile(path, 'w')\n→ 遍历 dict writestr\n→ 完全重打包"]
        end

        subgraph Temp["临时资源"]
            T1["~tmp_docx_fix/\n（patch_figure_caption 的\nauto_fit_tables）"]
            T2["tempfile.NamedTemporaryFile\n（patch_pagenum 的\n_find_ch1_start_index）"]
        end

        IN --> Read
        Read --> Modify
        Modify --> Write
        Write --> IN

        R1 -.->|"中间保存"| W1
        W1 -.->|"重新读取"| R2
        R2 -.->|"多次修改"| M2
        M2 -.->|"中间写回"| W2
        W2 -.->|"重新读取"| R1

        Read -.-> T1
        Read -.-> T2
    end
```

## 每补丁对象生命周期详情

### 1. patch_figure_caption — 双引擎混合

```
时间轴:
  auto_fit_tables():
    ZipFile(in, 'r')              → content dict (内存)
    regex sub on document.xml     → bytes (内存)
    ZipFile(out, 'w')             → 文件重写 (磁盘)
    shutil.rmtree(~tmp_docx_fix)  → 临时目录清理
  fix_figure_caption_bold():
    Document(out)                 → 从磁盘重读 (内存)
    iterate paragraphs → clear + add_run → 修改 (内存)
    doc.save(out)                 → 文件重写 (磁盘)
```

**生命周期计数**: 2 次完整读 + 2 次完整写，1 次临时目录创建/删除

### 2-5. patch_table_caption / patch_thanks / patch_abstract / patch_bibliography — 单引擎

```
  Document(path) → 读入 (内存)
  iterate / modify → 修改 (内存)
  doc.save(path) → 文件重写 (磁盘)
  # Document 对象超出作用域 → GC 回收
```

**生命周期计数**: 各 1 次读 + 1 次写，无临时文件

### 6. patch_pagenum — 多阶段 ZIP 引擎（最复杂）

```
阶段1:
  _read_zip(in)             → content dict (内存)
  _clean_old_footers()      → 修改 (内存)

  _fix_sections_in_package() → 修改 (内存)
  _write_zip(out)           → 文件重写 (磁盘)

阶段2:
  _read_zip(out)            → content2 dict (内存)
  Document(tmpfile)         → 临时文件 (磁盘)
  → 统计节数后删除

  _set_pg_num_type()       → 修改 (内存)
  _set_footer_distance()    → 修改 (内存)

  for N节:
    _build_footer_xml()     → 创建 XML ElementTree (内存)
    _inject_footer()        → 修改 content → 更新 CT/rels (内存)

  _write_zip(out)           → 文件重写 (磁盘)
```

**生命周期计数**: 2 次 zipfile 读 + 2 次 zipfile 写，额外 python-docx 临时文件

**关键中间状态**: 阶段1写回后，out.docx 处于"无页脚"状态约几十毫秒，才被阶段2补回。

### 7. patch_toc — 双阶段串行引擎

```
阶段一 (python-docx):
  Document(path) → 读入 (内存)
  找"目录" → 清除旧条目 → 加书签 → 插入 TOC 域 (内存)
  doc.save() → 文件重写 (磁盘)

阶段二 (zipfile):
  ZipFile(path, 'r') → content dict (内存)
  _patch_toc_styles() → 修改 styles.xml (内存)
  ZipFile(temp_out, 'w') → 写入临时文件 (磁盘)
  os.replace(temp_out, path) → 原子替换 (磁盘)
```

**生命周期计数**: 2 次读 + 2 次写，使用临时文件 + 原子替换

### 8-9. patch_margin / patch_header — 单引擎，同 2-5

## 跨补丁链文档状态变化

```mermaid
flowchart LR
    subgraph S0["初始"]
        DOC0["out.docx\nPandoc 生成"]
    end

    subgraph S1["patch_figure_caption"]
        NOTE1["tblW: auto→pct\n图片标题 run 合并"]
    end

    subgraph S2["patch_table_caption"]
        NOTE2["域→hyperlink\nTable Caption 加粗"]
    end

    subgraph S3["patch_thanks"]
        NOTE3["致谢/摘要/目录\n→ Heading 1"]
    end

    subgraph S4["patch_abstract"]
        NOTE4["关键词格式化"]
    end

    subgraph S5["patch_bibliography"]
        NOTE5["参考文献\n编号+字体+URL"]
    end

    subgraph S6["patch_pagenum"]
        NOTE6["分节符重写\n页脚注入\n页码格式"]
    end

    subgraph S7["patch_toc"]
        NOTE7["书签+TOC域\nTOC样式修补"]
    end

    subgraph S8["patch_margin"]
        NOTE8["页边距 2.20/2.20/2.50/2.50"]
    end

    subgraph S9["patch_header"]
        NOTE9["页眉+底部边框+LOGO"]
    end

    DOC0 -->|"读→写"| S1
    S1 -->|"重读→重写"| S2
    S2 -->|"重读→重写"| S3
    S3 -->|"重读→重写"| S4
    S4 -->|"重读→重写"| S5
    S5 -->|"重读→重写"| S6
    S6 -->|"重读→重写"| S7
    S7 -->|"重读→重写"| S8
    S8 -->|"重读→重写"| S9
```

## 累计读写放大

整个补丁链对 `out.docx` 的读写统计：

| 补丁 | 读次数 | 写次数 | 读方式 | 写方式 | 临时文件 |
|------|--------|--------|--------|--------|----------|
| patch_figure_caption | 2 | 2 | Document + zipfile | save + zipfile | ~tmp_docx_fix/ |
| patch_table_caption | 1 | 1 | Document | save | 无 |
| patch_thanks | 1 | 1 | Document | save | 无 |
| patch_abstract | 1 | 1 | Document | save | 无 |
| patch_bibliography | 1 | 1 | Document | save | 无 |
| patch_pagenum | 2 | 2 | zipfile ×2 + Document(tmp) | zipfile ×2 | NamedTemporaryFile |
| patch_toc | 2 | 2 | Document + zipfile | save + zipfile | *.tmp 临时文件 |
| patch_margin | 1 | 1 | Document | save | 无 |
| patch_header | 1 | 1 | Document | save | 无 |
| **合计** | **12** | **12** | — | — | **3** |

- 文件被完整读入内存 12 次，完整写回磁盘 12 次
- 每次 `doc.save()` 都会重建整个 ZIP，丢失原始 OOXML 的某些非标准结构
- 如果 out.docx 约 5MB，链总 I/O 约 12 × 5MB = 60MB 读取 + 60MB 写入

## 内存泄漏风险

| 风险点 | 说明 | 涉及脚本 |
|--------|------|----------|
| `content = {n: z.read(n) for n in z.namelist()}` | 整个 docx 解压到 dict，小文件无问题，大文件（含嵌入图片）会高内存 | patch_pagenum, patch_toc |
| `~tmp_docx_fix/` 不清理 | `finally` 块保证清理，但异常中断时目录残留 | patch_figure_caption |
| `NamedTemporaryFile(delete=False)` | 需手动 `os.unlink`，已实现 | patch_pagenum |
| Document 对象延迟 GC | python-docx 中 Document 持有整个 XML 树直到 GC | 所有使用 Document 的脚本 |
| lxml ElementTree 循环引用 | lxml 的 C 层面引用回收依赖 GC 运行时机 | patch_pagenum, patch_toc |

## 对象生命周期图例

```mermaid
flowchart TB
    subgraph Legend["图例"]
        L1["(磁盘) 持久化文件"]
        L2["(内存) Python 对象"]
        L3["(内存→磁盘) 序列化"]
        L4{"(逻辑分支) 条件判断"}
    end

    subgraph General["通用生命周期模式"]
        A["out.docx (磁盘)"] --> B["Document(path) (内存)"]
        B --> C["修改 XML 树 (内存)"]
        C --> D["doc.save(path) → 序列化"]
        D --> A

        E["out.docx (磁盘)"] --> F["ZipFile(path, 'r')\ncontent dict (内存)"]
        F --> G["修改 content 中 XML (内存)"]
        G --> H["ZipFile(path, 'w') (磁盘)"]
        H --> A
    end
```

## 跨补丁格式传递依赖

```
patch_figure_caption (合并 run)
       ↓ 丢失 run 级格式差异
patch_table_caption (非破坏性加粗 w:b)
       ↓ w:b 追加到 rPr 尾部
patch_thanks (清空段落重建)
       ↓ Heading 1 + pageBreakBefore
patch_abstract (清空 runs 重建)
       ↓ 仅影响关键词段落
patch_bibliography (清空段落重建)
       ↓ 仅影响参考文献段
patch_pagenum (zipfile 直接操作)
       ↓ lxml 解析 → 修改 → 序列化
       ↓ 破坏 python-docx 在 document.xml 中
         注入的额外命名空间声明
patch_toc -> python-docx 阶段一
       ↓ 受 pagenum 修改后的 XML 影响
patch_toc -> zipfile 阶段二
       ↓ 完全避开 python-docx 层
patch_margin (python-docx section API)
       ↓ 依赖 pagenum 建立的分节结构
patch_header (python-docx section API)
       ↓ 依赖 pagenum 建立的分节结构
```

**关键传递依赖**：
- `patch_margin` 和 `patch_header` **依赖** `patch_pagenum` 建立的分节符结构（`_fix_sections_in_package` 在第一个 H1 前插入 `sectPr type=oddPage`）
- `patch_pagenum` 的 lxml 重序列化可能会改变 document.xml 的命名空间声明，影响 python-docx 后续解析
- python-docx 的 `doc.save()` 会按自己的逻辑重新组织 XML，zipfile 模式则保留原始 XML 结构

## 各补丁

| 补丁 | 主要操作对象 | 对象类型 | 生命周期范围 | 持有时间 |
|------|-------------|----------|-------------|----------|
| patch_figure_caption | Document, ZipFile, tmp_dir | 混合 | 函数级 | auto_fit 期间 |
| patch_table_caption | Document | python-docx | process_document() | 完整调用 |
| patch_thanks | Document | python-docx | patch_thanks() | 完整调用 |
| patch_abstract | Document | python-docx | patch_abstract() | 完整调用 |
| patch_bibliography | Document | python-docx | patch_bibliography() | 完整调用 |
| patch_pagenum | content dict, lxml trees, tmp Document | zipfile + lxml | add_page_numbers() | 完整调用 |
| patch_toc | Document, content dict | 混合 | add_toc() 分两阶段 | 分阶段 |
| patch_margin | Document | python-docx | set_margins() | 完整调用 |
| patch_header | Document | python-docx | add_header() | 完整调用 |

| 脚本 | 读方式 | 写方式 | 破坏性 |
|------|--------|--------|--------|
| patch_figure_caption | Document() + zipfile | save() + zipfile | 合并 run（破坏 run 结构） |
| patch_table_caption | Document() | save() | 非破坏性（直接加 w:b） |
| patch_thanks | Document() | save() | clear() 清空段落 |
| patch_abstract | Document() | save() | clear() 清空 runs |
| patch_bibliography | Document() | save() | clear() 清空段落 |
| patch_pagenum | zipfile | zipfile | 重写页脚/分节结构 |
| patch_toc | Document() + zipfile | save() + zipfile | 插入/删除段落 |
| patch_margin | Document() | save() | 非破坏性（改属性） |
| patch_header | Document() | save() | clear() 清空段落 |

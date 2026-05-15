# out.ps1 控制流图

## 整体调用关系

```mermaid
flowchart TB
    subgraph Pre["前置检查"]
        A(["out.ps1 启动"])
        B{"~$out.docx 存在?"}
        A --> B
        B -->|是| C["报错退出"]
        B -->|否| D["继续执行"]
    end

    subgraph Figures["图片编译阶段"]
        D --> E["convert_plantuml.py --format svg"]
        D --> F["convert_mermaid.py --format png"]
        D --> G["convert_sciplot.py --format svg"]
        E --> H["扫描 figures/puml/*.puml"]
        F --> I["扫描 figures/mermaid/*.mmd"]
        G --> J["扫描 figures/sciplot/*.py"]
    end

    subgraph Bibl["参考文献生成"]
        D --> K["gen_bibl.py"]
        K --> L["扫描 *.tex 中 \\cite{...} 引用"]
        L --> M["从 bibl/fake_ref.bib 提取"]
        M --> N["生成 99.bibl.tex"]
    end

    subgraph Stage1["第一阶段: Pandoc → JSON"]
        O["pandoc main.tex → temp_refs.json\n--filter pandoc-tex-numbering\n--citeproc"]
        N --> O
        H --> O
        I --> O
        J --> O
    end

    subgraph Filter["参考文献去重"]
        P["remove_refs.py"]
        O --> P
        Q["生成 temp_filtered.json"]
        P --> Q
    end

    subgraph Stage2["第二阶段: JSON → DOCX"]
        R["pandoc temp_filtered.json → out.docx\n-f json -t docx --reference-doc=ref.docx"]
        Q --> R
    end

    subgraph Finish["完成"]
        T["Start-Process out.docx\n打开最终文档"]
        R --> T
    end
```

## 文件流关系

```mermaid
flowchart LR
    subgraph Inputs["输入文件"]
        TEX["main.tex + *.tex 章节文件"]
        BIB["bibl/fake_ref.bib"]
        CSL["bibl/gb7714-2015-numeric.csl"]
        REFDOC["ref.docx（样式模板）"]
        PUML["figures/puml/*.puml"]
        MMD["figures/mermaid/*.mmd"]
        SCP["figures/sciplot/*.py"]
    end

    subgraph Intermediate["中间文件"]
        SVGP["figures/puml/*.svg"]
        PNGM["figures/mermaid/*.png"]
        SVG["figures/sciplot/*.svg"]
        BIBTEX["99.bibl.tex"]
        REFS_JSON["temp_refs.json"]
        FILTERED_JSON["temp_filtered.json"]
    end

    subgraph Outputs["最终输出"]
        DOCX["out.docx"]
    end

    PUML -->|convert_plantuml.py| SVGP
    MMD -->|convert_mermaid.py| PNGM
    SCP -->|convert_sciplot.py| SVG
    BIB -->|gen_bibl.py| BIBTEX
    TEX -->|pandoc 阶段1| REFS_JSON
    BIB -->|--citeproc| REFS_JSON
    CSL -->|--csl| REFS_JSON
    REFDOC -->|--reference-doc| REFS_JSON
    REFS_JSON -->|remove_refs.py| FILTERED_JSON
    FILTERED_JSON -->|pandoc 阶段2| DOCX
    REFDOC -->|--reference-doc| DOCX
```

## 执行阶段流水线

```
┌──────────────────────────────────────────────────────────────┐
│  阶段0: 前置检查                                              │
│  └─ 检查 Word 临时文件 ~$out.docx 是否存在                     │
├──────────────────────────────────────────────────────────────┤
│  阶段1: 图片编译（并行）                                       │
│  ├─ convert_plantuml.py → figures/puml/*.puml → *.svg        │
│  ├─ convert_mermaid.py  → figures/mermaid/*.mmd → *.png      │
│  └─ convert_sciplot.py  → figures/sciplot/*.py → *.svg       │
├──────────────────────────────────────────────────────────────┤
│  阶段2: 参考文献生成                                           │
│  └─ gen_bibl.py → 99.bibl.tex                                │
├──────────────────────────────────────────────────────────────┤
│  阶段3: 第一阶段 Pandoc 转换 (LaTeX → JSON)                   │
│  └─ pandoc + citeproc + pandoc-tex-numbering → temp_refs.json│
├──────────────────────────────────────────────────────────────┤
│  阶段4: 参考文献去重                                           │
│  └─ remove_refs.py → temp_filtered.json                      │
├──────────────────────────────────────────────────────────────┤
│  阶段5: 第二阶段 Pandoc 转换 (JSON → DOCX)                    │
│  └─ pandoc -f json -t docx → out.docx                        │
├──────────────────────────────────────────────────────────────┤
│  阶段6: 打开文档                                              │
│  └─ Start-Process out.docx                                   │
└──────────────────────────────────────────────────────────────┘
```


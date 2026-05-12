# latex2word-thesis

LaTeX 写论文，一键转 Word。学校不收 LaTeX？写一份 LaTeX，同时出 PDF 预览 + Word 交稿。

## 快速开始

```bash
.\out.ps1         # 一键：编译 PlantUML/Mermaid → 处理参考文献 → 转 Word → 自动排版
```

输出 `out.docx`，用 `ref.docx` 中的样式。格式不满意？改 `ref.docx` 再跑一遍。

## 前置依赖

- [Pandoc](https://pandoc.org/installing.html)
- Python 3.x（可选，表格/致谢/参考文献自动修复需要）
- LaTeX（可选，仅 PDF 预览需要）
- Java（可选，仅 PlantUML 需要）
- Node.js（可选，仅 Mermaid 需要）

```bash
pip install pywin32
```

## 两步工作流

| 步骤 | 做什么 | 命令 |
|------|--------|------|
| 写 | 在 `.tex` 里写内容，`xelatex main.tex` 实时预览 | `xelatex main.tex` |
| 交 | 跑 `out.ps1` 出 Word 交稿 | `.\out.ps1` |

## 项目布局

```txt
main.tex              # 入口，按顺序引入各章节
preamble.tex          # 样式定义（字体、标题、图表编号等）
0x.*.tex              # 各章节正文
figures/              # 图片
bibl/                 # 参考文献 .bib + .csl
ref.docx              # Word 样式模板
out.ps1               # 一键转换脚本
*.py                  # 后处理脚本（表格、标题、致谢、参考文献修复）
```

## 已知问题

- 目录功能有 bug
- 复杂宏包不兼容，复杂公式/图表建议转图片插入
- 公式字体需在 Word 中手动核对

## 详细文档

见 [docs.md](docs.md)。

# 基于 pandoc-tex-numbering 的过滤器
# 微调空格

$env:PYTHONIOENCODING = "utf-8"

$outputFile = "out.docx"
$tempFile = "~`$"+"$outputFile"

if (Test-Path $tempFile) {
    Write-Host "错误: Word 文件正在被编辑中，请关闭 $outputFile 后再运行！" -ForegroundColor Red
    exit 1
}

# 编译 figures 目录下所有 puml 文件为 svg
Write-Host "正在编译 PlantUML 图片...可能略慢" -ForegroundColor Green
python .\convert_plantuml.py --format svg
if ($LASTEXITCODE -ne 0) {
    Write-Host "警告: PlantUML 编译失败，请检查 Java 环境和 puml 文件语法" -ForegroundColor Yellow
}

# 编译 figures 目录下所有 mmd 文件为 png
# 注：Mermaid SVG 使用 foreignObject 渲染文本，Word 无法识别，故使用 PNG
Write-Host "正在编译 Mermaid 图片..." -ForegroundColor Green
python .\convert_mermaid.py --format png
if ($LASTEXITCODE -ne 0) {
    Write-Host "警告: Mermaid 编译失败，请检查 mmdc 安装和 mmd 文件语法" -ForegroundColor Yellow
}

# 编译 figures/sciplot 目录下所有 Python 绘图脚本
Write-Host "正在编译 sciplot 科研图表..." -ForegroundColor Green
python .\convert_sciplot.py --format svg
if ($LASTEXITCODE -ne 0) {
    Write-Host "警告: sciplot 编译失败，请检查 Python 脚本语法" -ForegroundColor Yellow
}

# 编译 figures/chen_er 目录下所有 Chen 式 E-R 图（ignore.yaml 中列出的除外）
Write-Host "正在编译 Chen 式 E-R 图..." -ForegroundColor Green
python .\convert_chen_er.py --format svg
if ($LASTEXITCODE -ne 0) {
    Write-Host "警告: Chen E-R 图编译失败，请检查 chen_er 脚本语法" -ForegroundColor Yellow
}

# 从 bib 文件自动生成 99.bibl.tex
python .\gen_bibl.py

# 第一阶段：使用 --citeproc 处理引用，输出为 JSON
$jsonTemp = "temp_refs.json"
pandoc main.tex -t json `
  --reference-doc=ref.docx `
  --filter .\pandoc_tex_numbering_filter.cmd `
  --citeproc `
  --bibliography=bibl/fake_ref.bib `
  --csl=bibl/gb7714-2015-numeric.csl `
  -M figure-prefix="图" `
  -M table-prefix="表" `
  -M equation-prefix="公式" `
  -M section-prefix="" `
  -M prefix-space="false" `
  -M number-reset-level=3 `
  -M figure-src-format="{prefix}{parent_num}" `
  -M figure-ref-format="{parent_num}" `
  -M table-src-format="{prefix}{parent_num}" `
  -M table-ref-format="{parent_num}" `
  -M section-src-format-1="{h1} " `
  -M section-src-format-2="{h1}.{h2} " `
  -M section-src-format-3="{h1}.{h2}.{h3} " `
  -M chapters=true `
  -M chapDelim="-" `
  -o $jsonTemp 2>$null

# 保存第一阶段的状态
$stage1Success = ($LASTEXITCODE -eq 0)

if ($stage1Success) {
    # 使用 Python 过滤器移除 citeproc 生成的参考文献列表
    # 注意：使用文件参数而非管道，避免 PowerShell 管道编码损坏中文字符
    $filteredJson = "temp_filtered.json"
    python .\remove_refs.py $jsonTemp $filteredJson
    if ($LASTEXITCODE -eq 0) {
        pandoc -f json -t docx `
          --reference-doc=ref.docx `
          -o $outputFile $filteredJson
        $stage2Success = ($LASTEXITCODE -eq 0)
    } else {
        Write-Host "错误: remove_refs.py 执行失败" -ForegroundColor Red
        exit 1
    }
    Remove-Item $filteredJson -ErrorAction SilentlyContinue
} else {
    Write-Host "错误: 第一阶段 pandoc 转换失败" -ForegroundColor Red
    exit 1
}

# 清理临时文件
Remove-Item $jsonTemp -ErrorAction SilentlyContinue

if ($stage2Success) {
    python '.\patch_figure_caption.py' $outputFile $outputFile
    if ($LASTEXITCODE -eq 0) {
        python '.\patch_table_caption.py' $outputFile $outputFile
    }
    if ($LASTEXITCODE -eq 0) {
        python '.\patch_caption_colon.py' $outputFile $outputFile
    }
    if ($LASTEXITCODE -eq 0) {
        python '.\patch_thanks.py' $outputFile $outputFile
    }
    if ($LASTEXITCODE -eq 0) {
        python '.\patch_abstract.py' $outputFile $outputFile
    }
    if ($LASTEXITCODE -eq 0) {
        python '.\patch_bibliography.py' $outputFile $outputFile
    }
    if ($LASTEXITCODE -eq 0) {
        python '.\patch_pagenum.py' $outputFile $outputFile
    }
    if ($LASTEXITCODE -eq 0) {
        python '.\patch_toc.py' $outputFile $outputFile
    }
    if ($LASTEXITCODE -eq 0) {
        python '.\patch_margin.py' $outputFile $outputFile
    }
    if ($LASTEXITCODE -eq 0) {
        python '.\patch_header.py' $outputFile $outputFile
    }
    if ($LASTEXITCODE -eq 0) {
        Start-Process .\$outputFile
    }
} else {
    Write-Host "错误: 第二阶段 pandoc 转换失败" -ForegroundColor Red
    exit 1
}

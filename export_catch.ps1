param(
    [Parameter(Mandatory=$true)]
    [string]$commit
)

$files = @(
    'out.ps1',
    'patch_chapter_break.py',
    'patch_citation_hyperlink.py',
    'patch_strip_spaces.py'
)

$null = New-Item -ItemType Directory -Force -Path catch

foreach ($f in $files) {
    git show "$commit`:$f" | Out-File -FilePath "catch/$f" -Encoding utf8
    Write-Host "  catch/$f"
}

Write-Host "完成: $($files.Count) 个文件已导出到 catch/"

-- PNG → SVG 路径替换滤镜
-- Pandoc 转 Word 时将 .png 图片路径替换为同名的 .svg，
-- 让 Word 嵌入矢量图，提升输出质量。
-- 仅当 .svg 文件实际存在时才替换。
function Image(img)
    if img.src:match('%.png$') then
        local svg_src = img.src:gsub('%.png$', '.svg')
        local f = io.open(svg_src, 'r')
        if f then
            f:close()
            img.src = svg_src
        end
    end
    return img
end

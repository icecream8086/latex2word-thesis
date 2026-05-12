"""
sciplot — 科研论文级绘图包
============================

Mermaid 和 PlantUML 画不了的死角，交给 sciplot。

适用于 LaTeX → Word 论文转换管线中，需要高质量统计图、数学曲线、
热力图、维恩图等场景。基于 matplotlib，自动适配中文字体。

快速开始:
    import sciplot as sp

    # 折线图
    sp.line([1,2,3], [4,5,6], title="简单折线图")
    sp.savefig("my_line")

    # 柱状图
    sp.bar(["A","B","C"], [23, 45, 78], title="实验结果")
    sp.savefig("my_bar")

    # 热力图
    sp.heatmap([[1,2],[3,4]], xticklabels=["X1","X2"], yticklabels=["Y1","Y2"])
    sp.savefig("my_heatmap")

    # 函数曲线
    sp.curve(lambda x: x**2, x_range=(-3, 3), label="y = x²")
    sp.savefig("my_curve")
"""

from ._config import (
    setup_style,
    detect_chinese_font,
    color,
    COLOR_CYCLE,
    COLORS,
)
from ._charts import (
    bar,
    line,
    scatter,
    histogram,
    boxplot,
    pie,
    radar,
)
from ._special import (
    heatmap,
    confusion_matrix,
    venn,
    curve,
    timeline,
    tree,
    flow,
)
from ._utils import savefig

# ── 导入时自动配置中文环境和论文级样式 ────────────────────────────────────
_chinese_font = setup_style()
if _chinese_font:
    pass  # 静默配置成功
else:
    import warnings
    warnings.warn(
        "sciplot: 未检测到中文字体，中文可能显示为方框。\n"
        "  Windows: 安装 微软雅黑 或 宋体\n"
        "  Linux:   apt install fonts-noto-cjk\n"
        "  macOS:   系统自带苹方/华文字体",
        stacklevel=2,
    )

__all__ = [
    # 配置
    "setup_style",
    "detect_chinese_font",
    "color",
    "COLOR_CYCLE",
    "COLORS",
    # 统计图表
    "bar",
    "line",
    "scatter",
    "histogram",
    "boxplot",
    "pie",
    "radar",
    # 专门图表
    "heatmap",
    "confusion_matrix",
    "venn",
    "curve",
    "timeline",
    "tree",
    "flow",
    # 工具
    "savefig",
]

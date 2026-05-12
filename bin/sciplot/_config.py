"""
科学绘图包 — 配置模块
自动检测中文字体、设置论文风格、定义配色方案。
"""

import matplotlib.pyplot as plt
import matplotlib as mpl
from pathlib import Path
import sys


# ── 论文级配色方案 ──────────────────────────────────────────────────────────

# 高级感配色（兼顾屏幕阅读和灰度打印）
COLORS = {
    "blue":   "#4C72B0",
    "orange": "#DD8452",
    "green":  "#55A868",
    "red":    "#C44E52",
    "purple": "#8172B2",
    "brown":  "#937860",
    "pink":   "#DA8EA5",
    "gray":   "#8C8C8C",
    "teal":   "#64B5CD",
    "lime":   "#9ACD5C",
}

# 按顺序取用的默认配色循环
COLOR_CYCLE = [
    COLORS["blue"],
    COLORS["orange"],
    COLORS["green"],
    COLORS["red"],
    COLORS["purple"],
    COLORS["brown"],
    COLORS["pink"],
    COLORS["teal"],
]

# 灰度安全色（去掉暖色可能会被打印成一片灰的）
GRAYSCALE_CYCLE = [
    "#2C2C2C", "#5C5C5C", "#8C8C8C", "#B0B0B0",
    "#3A3A3A", "#6E6E6E", "#9E9E9E", "#C8C8C8",
]

# 热力图/混淆矩阵专用色图
HEATMAP_CMAP = "Blues"
HEATMAP_DIVERGING_CMAP = "RdBu_r"


# ── 中文字体检测 ────────────────────────────────────────────────────────────

def detect_chinese_font() -> str | None:
    """检测系统可用的中文字体，返回 family name。"""
    import matplotlib.font_manager as fm

    # 按偏好顺序搜索
    preferred = [
        "Microsoft YaHei",        # Windows: 微软雅黑
        "SimSun",                 # Windows: 宋体
        "SimHei",                 # Windows: 黑体
        "DengXian",               # Windows: 等线
        "Noto Sans CJK SC",       # Linux: 思源黑体
        "Noto Serif CJK SC",      # Linux: 思源宋体
        "Source Han Sans CN",     # 思源黑体(备选名)
        "Source Han Serif CN",    # 思源宋体(备选名)
        "WenQuanYi Micro Hei",    # Linux: 文泉驿
        "PingFang SC",            # macOS: 苹方
        "STHeiti",                # macOS: 华文黑体
        "STSong",                 # macOS: 华文宋体
        "AR PL UMing CN",         # Linux: 明朝体
    ]

    # 获取所有已安装字体名
    installed = {f.name for f in fm.fontManager.ttflist}

    for name in preferred:
        if name in installed:
            return name

    # fallback: 找一个支持 CJK 的
    for f in fm.fontManager.ttflist:
        if f.name and ("CJK" in f.name or "Song" in f.name
                       or "Hei" in f.name or "Ming" in f.name):
            return f.name
    return None


def setup_style(*,
                chinese_font: str | None = None,
                latex: bool = False,
                use_tex: bool = False,
                dpi: int = 150,
                font_size: int = 11) -> str | None:
    """
    配置论文级 matplotlib 样式。

    参数:
        chinese_font: 指定中文字体名，None 则自动检测
        latex: 是否使用 LaTeX 数学字体（更美观的公式）
        use_tex: 是否使用系统 LaTeX 渲染（需安装 LaTeX）
        dpi: 默认输出 DPI
        font_size: 正文字号（磅）

    返回:
        检测到的中文字体名（None 表示未找到）
    """
    if chinese_font is None:
        chinese_font = detect_chinese_font()

    # 通用样式
    plt.style.use("seaborn-v0_8-whitegrid")

    # 公式字体
    if use_tex:
        plt.rcParams["text.usetex"] = True
    elif latex:
        plt.rcParams["mathtext.fontset"] = "stix"
        plt.rcParams["font.family"] = "STIXGeneral"
    else:
        plt.rcParams["mathtext.fontset"] = "stix"

    # 如果不使用 LaTeX，设置字体回退链以便支持中文
    if not use_tex:
        if chinese_font:
            # 设置 sans-serif 回退链，让中文使用指定字体
            plt.rcParams["font.sans-serif"] = [chinese_font, "DejaVu Sans"]
        plt.rcParams["font.family"] = "sans-serif"

    # 尺寸与刻度
    plt.rcParams.update({
        "figure.dpi": dpi,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.05,
        "font.size": font_size,
        "axes.titlesize": font_size + 2,
        "axes.labelsize": font_size,
        "xtick.labelsize": font_size - 1,
        "ytick.labelsize": font_size - 1,
        "legend.fontsize": font_size - 1,
        "lines.linewidth": 1.8,
        "lines.markersize": 6,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.max_open_warning": 50,
        "figure.figsize": [5.5, 3.8],
    })

    # 配色循环
    plt.rcParams["axes.prop_cycle"] = mpl.cycler(color=COLOR_CYCLE)

    return chinese_font


def color(idx: int) -> str:
    """按索引取色，循环使用 COLOR_CYCLE。"""
    return COLOR_CYCLE[idx % len(COLOR_CYCLE)]


def get_cmap(name: str = "Blues", n_colors: int = 9):
    """获取论文级 colormap。"""
    return plt.cm.get_cmap(name, n_colors)

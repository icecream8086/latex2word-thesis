"""
科学绘图包 — 专门图表模块（热力图、维恩图、函数曲线、时间线等）
"""

import inspect

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from matplotlib.patches import FancyArrowPatch
from ._config import color, COLOR_CYCLE


def _call_safe(f, x, params=None):
    """调用函数，仅在函数接受额外的关键字参数时传入 params。"""
    if not callable(f):
        return f(x)
    if params:
        sig = inspect.signature(f)
        try:
            sig.bind(x, **params)
            return f(x, **params)
        except (TypeError, TypeError):
            pass
    return f(x)


def heatmap(
    data,
    *,
    xticklabels: list[str] | None = None,
    yticklabels: list[str] | None = None,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    cmap: str = "Blues",
    annot: bool = True,
    annot_format: str = "{:.2f}",
    fmt: str = ".2f",
    vmin: float | None = None,
    vmax: float | None = None,
    square: bool = True,
    cbar: bool = True,
    cbar_label: str = "",
    mask_upper: bool = False,
    figsize: tuple | None = None,
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    热力图 / 混淆矩阵。

    参数:
        mask_upper: 掩码上三角（适合相关性矩阵）
        annot:      是否在格内显示数值
    """
    data = np.asarray(data, dtype=float)

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure

    mask = None
    if mask_upper:
        mask = np.triu(np.ones_like(data, dtype=bool))

    im = ax.imshow(data, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")

    n_rows, n_cols = data.shape

    if xticklabels:
        ax.set_xticks(range(n_cols))
        ax.set_xticklabels(xticklabels, rotation=45, ha="right", fontsize=9)
    if yticklabels:
        ax.set_yticks(range(n_rows))
        ax.set_yticklabels(yticklabels, fontsize=9)

    if annot:
        for i in range(n_rows):
            for j in range(n_cols):
                if mask is not None and mask[i, j]:
                    continue
                val = data[i, j]
                # auto text color based on background brightness
                if cmap in ("Blues", "Reds", "Greens", "Purples", "Oranges"):
                    bg = im.norm(val)
                    text_color = "white" if bg > 0.55 else "black"
                elif cmap in ("RdBu_r", "coolwarm", "seismic"):
                    bg = abs(im.norm(val) - 0.5) * 2
                    text_color = "white" if bg > 0.5 else "black"
                else:
                    text_color = "black"
                ax.text(j, i, annot_format.format(val),
                        ha="center", va="center", fontsize=9, color=text_color)

    if cbar:
        cb = fig.colorbar(im, ax=ax, shrink=0.75)
        if cbar_label:
            cb.set_label(cbar_label)

    if title:
        ax.set_title(title)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)

    ax.set_xticks(range(n_cols))
    ax.set_yticks(range(n_rows))
    return fig, ax


def confusion_matrix(
    cm,
    class_names: list[str],
    *,
    title: str = "混淆矩阵",
    normalize: bool = False,
    **kwargs,
) -> tuple[plt.Figure, plt.Axes]:
    """
    混淆矩阵专用（热力图封装）。

    参数:
        cm:          混淆矩阵 (n x n)
        class_names: 类别名列表
        normalize:   是否归一化到 [0, 1]
    """
    data = np.asarray(cm, dtype=float)
    if normalize:
        row_sums = data.sum(axis=1, keepdims=True)
        data = np.divide(data, row_sums, where=row_sums != 0, out=np.zeros_like(data))
        fmt_str = ".2f"
    else:
        fmt_str = "d"

    return heatmap(
        data,
        xticklabels=class_names,
        yticklabels=class_names,
        title=title,
        cmap="Blues",
        annot_format="{:.2f}" if normalize else "{}",
        fmt=".2f" if normalize else "d",
        xlabel="预测类别",
        ylabel="真实类别",
        square=True,
        **kwargs,
    )


def venn(
    sets: list[set],
    labels: list[str] | None = None,
    *,
    title: str = "",
    colors: list[str] | None = None,
    alpha: float = 0.45,
    set_colors: list[str] | None = None,
    figsize: tuple | None = None,
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    维恩图 — 支持 2~3 组集合。

    参数:
        sets:  [set1, set2, ...]
    """
    n = len(sets)
    if n < 2 or n > 3:
        raise ValueError("仅支持 2 组或 3 组集合的维恩图")

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize or (5.5, 4.5))
    else:
        fig = ax.figure

    if labels is None:
        labels = [f"Set {i+1}" for i in range(n)]

    ax.set_aspect("equal")
    ax.axis("off")

    colors = colors or [color(i) for i in range(n)]
    circles = []

    if n == 2:
        # 两圆相交
        r = 1.5
        centers = [(-0.6, 0), (0.6, 0)]
        for (cx, cy), col, lab in zip(centers, colors[:2], labels):
            c = plt.Circle((cx, cy), r, color=col, alpha=alpha, ec=col, lw=1.5)
            ax.add_patch(c)
            circles.append((cx, cy, r))
            ax.text(cx, cy + r + 0.4, lab, ha="center", va="bottom",
                    fontsize=11, fontweight="bold", color=col)

        # 计算各区域
        s1 = sets[0]
        s2 = sets[1]
        only1 = s1 - s2
        only2 = s2 - s1
        both = s1 & s2

        ax.text(centers[0][0] - 0.85, 0,
                "\n".join(only1) if only1 else "", ha="center", va="center", fontsize=9)
        ax.text(0, 0,
                "\n".join(both) if both else "", ha="center", va="center", fontsize=9)
        ax.text(centers[1][0] + 0.85, 0,
                "\n".join(only2) if only2 else "", ha="center", va="center", fontsize=9)

    else:  # n == 3
        # 三圆相交（标准 Venn 布局）
        r = 1.3
        angles = np.deg2rad([90, 210, 330])
        centers = [(1.0 * np.cos(a), 1.0 * np.sin(a)) for a in angles]

        for (cx, cy), col, lab in zip(centers, colors[:3], labels):
            c = plt.Circle((cx, cy), r, color=col, alpha=alpha, ec=col, lw=1.5)
            ax.add_patch(c)
            # 标签放圆外侧
            label_r = 1.0 + r + 0.35
            lx = label_r * np.cos(angles[len(circles)])
            ly = label_r * np.sin(angles[len(circles)])
            ax.text(lx, ly, lab, ha="center", va="center",
                    fontsize=10, fontweight="bold", color=col)
            circles.append((cx, cy, r))

        s1, s2, s3 = sets[0], sets[1], sets[2]

        # 7 个区域
        regions = {
            (1, 0, 0): s1 - s2 - s3,
            (0, 1, 0): s2 - s1 - s3,
            (0, 0, 1): s3 - s1 - s2,
            (1, 1, 0): (s1 & s2) - s3,
            (1, 0, 1): (s1 & s3) - s2,
            (0, 1, 1): (s2 & s3) - s1,
            (1, 1, 1): s1 & s2 & s3,
        }

        # 手工调整的坐标（简化版）
        pos_map = {
            (1, 0, 0): (0, 1.4),
            (0, 1, 0): (-1.25, -0.75),
            (0, 0, 1): (1.25, -0.75),
            (1, 1, 0): (-0.6, 0.25),
            (1, 0, 1): (0.6, 0.25),
            (0, 1, 1): (0, -0.85),
            (1, 1, 1): (0, 0),
        }

        for key, pos in pos_map.items():
            elements = regions[key]
            if elements:
                ax.text(pos[0], pos[1], "\n".join(elements),
                        ha="center", va="center", fontsize=8)

    ax.set_xlim(-3.5, 3.5)
    ax.set_ylim(-3, 3.5)

    if title:
        ax.set_title(title, pad=10)

    return fig, ax


def curve(
    func,
    x_range: tuple[float, float] = (-5, 5),
    *,
    params: dict | None = None,
    label: str = "",
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    color: str | None = None,
    linestyle: str = "-",
    linewidth: float = 2.0,
    n_points: int = 1000,
    secondary_funcs: list[tuple] | None = None,
    fill_area: tuple | None = None,
    show_zero_lines: bool = True,
    xlim: tuple | None = None,
    ylim: tuple | None = None,
    legend: bool = True,
    figsize: tuple | None = None,
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    函数曲线图 — 支持数学公式标注。

    参数:
        func:             函数或 lambda，接受 x 和 params 返回 y
        params:           func 的额外参数字典
        secondary_funcs:  副函数列表 [(func, label, color, style), ...]
        fill_area:        填充区域 [x_start, x_end] 为 None 则填满
        show_zero_lines:  是否显示坐标轴零线
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure

    x = np.linspace(x_range[0], x_range[1], n_points)
    p = params or {}
    y = func(x, **p) if callable(func) else func(x)

    if hasattr(y, "__iter__") and not isinstance(y, np.ndarray):
        y = np.array(y, dtype=float)

    c = color or COLOR_CYCLE[0]
    ax.plot(x, y, color=c, linestyle=linestyle, linewidth=linewidth,
            label=label or None, zorder=3)

    if secondary_funcs:
        for i, (sf, slab, sc, ssty) in enumerate(secondary_funcs):
            sy = _call_safe(sf, x, p)
            ax.plot(x, sy, color=sc or color(i+1), linestyle=ssty or "-",
                    linewidth=linewidth * 0.85, label=slab or None, zorder=3)

    if fill_area:
        x_fill = np.linspace(max(fill_area[0], x_range[0]),
                             min(fill_area[1], x_range[1]), n_points)
        y_fill = func(x_fill, **p) if callable(func) else func(x_fill)
        ax.fill_between(x_fill, y_fill, alpha=0.2, color=c)

    if show_zero_lines:
        ax.axhline(y=0, color="#333333", linewidth=0.5, linestyle="--", alpha=0.4)
        ax.axvline(x=0, color="#333333", linewidth=0.5, linestyle="--", alpha=0.4)

    if title:
        ax.set_title(title)
    ax.set_xlabel(xlabel or "x")
    ax.set_ylabel(ylabel or "y")
    if xlim:
        ax.set_xlim(xlim)
    if ylim:
        ax.set_ylim(ylim)
    if legend and label:
        ax.legend(framealpha=0.9)

    ax.grid(alpha=0.3)
    return fig, ax


def timeline(
    events: list[tuple],
    *,
    title: str = "",
    colors: list[str] | None = None,
    point_size: float = 60,
    linewidth: float = 2.5,
    figsize: tuple | None = None,
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    时间线图 — 以时间轴形式展示事件里程碑。

    参数:
        events: [(date_str, label, description), ...]
                date_str: 日期文本（显示在轴上）
                label:    事件名
                description: 事件描述（可选）
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure

    n = len(events)
    y_pos = np.arange(n)
    colors = colors or [color(i) for i in range(n)]

    # 水平时间线
    ax.hlines(y=y_pos, xmin=0, xmax=1, color="#BBBBBB", linewidth=linewidth, zorder=1)

    # 事件点
    for i, (date_str, label, *desc_parts) in enumerate(events):
        desc = desc_parts[0] if desc_parts else ""
        ax.plot(1, i, "o", color=colors[i % len(colors)],
                markersize=np.sqrt(point_size), zorder=3)
        ax.text(0, i, f"  {date_str}", ha="left", va="center",
                fontsize=9, color="#555555")
        ax.text(1, i + 0.25, label, ha="center", va="bottom",
                fontsize=10, fontweight="bold")

    ax.set_ylim(-0.5, n - 0.5)
    ax.set_xlim(-0.05, 1.15)
    ax.axis("off")

    if title:
        ax.set_title(title, pad=15)

    return fig, ax


def tree(
    nodes: dict[str, list[str]],
    *,
    root: str = "root",
    title: str = "",
    node_color: str | None = None,
    edge_color: str = "#888888",
    node_size: float = 1.0,
    font_size: int = 10,
    figsize: tuple | None = None,
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    树形图 — 基于递归布局。

    参数:
        nodes: {父节点: [子节点列表], ...}
        root:  根节点名
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize or (6, 5))
    else:
        fig = ax.figure

    nc = node_color or COLOR_CYCLE[0]
    ax.axis("off")

    # 计算子树大小
    def subtree_size(name):
        children = nodes.get(name, [])
        if not children:
            return 1
        return sum(subtree_size(c) for c in children)

    # 递归布局 (x, y) — x 为水平位置, y 为层级
    positions = {}
    y_offset = [0]

    def layout(name, depth, x_start):
        children = nodes.get(name, [])
        total = subtree_size(name)

        my_x = x_start + total / 2 - 0.5

        if children:
            child_x = x_start
            for c in children:
                layout(c, depth + 1, child_x)
                child_x += subtree_size(c)
            # 父节点居中于子节点
            positions[name] = ((positions[children[0]][0] + positions[children[-1]][0]) / 2, depth)
        else:
            positions[name] = (my_x, depth)

    layout(root, 0, 0)

    # 绘制边
    for parent, children in nodes.items():
        if parent not in positions:
            continue
        px, py = positions[parent]
        for c in children:
            if c not in positions:
                continue
            cx, cy = positions[c]
            # 曲线连接
            mid_y = (py + cy) / 2
            ax.plot([px, px, cx], [py, mid_y, cy],
                    color=edge_color, linewidth=1.2, zorder=1)

    # 绘制节点
    for name, (x, y) in positions.items():
        ax.plot(x, y, "o", color=nc, markersize=8 * node_size, zorder=2)
        ax.text(x, y - 0.2, name, ha="center", va="top",
                fontsize=font_size, zorder=3)

    # 调整范围
    all_y = [p[1] for p in positions.values()]
    all_x = [p[0] for p in positions.values()]
    if all_x:
        margin = max(1, (max(all_x) - min(all_x)) * 0.15 + 1)
        ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
    if all_y:
        ax.set_ylim(min(all_y) - 0.5, max(all_y) + 0.5)
    ax.invert_yaxis()

    if title:
        ax.set_title(title)

    return fig, ax


def flow(
    blocks: list[dict],
    connections: list[tuple[int, int]] | None = None,
    *,
    title: str = "",
    figsize: tuple | None = None,
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    简化流程图 — 基于 matplotlib patches，支持带数学标注的方框。

    blocks: [{
        "text": "方框文字",
        "w": 2.0,        # 宽度
        "h": 0.8,        # 高度
        "xy": (0, 0),    # 左下角坐标
        "color": "#4C72B0",
        "shape": "box",  # "box" | "diamond" | "circle" | "round"
        "fontsize": 10,
    }, ...]

    connections: [(from_idx, to_idx), ...]  在方框间绘制箭头
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize or (7, 5))
    else:
        fig = ax.figure

    ax.axis("off")
    ax.set_aspect("equal")

    for blk in blocks:
        text = blk.get("text", "")
        w = blk.get("w", 2.0)
        h = blk.get("h", 0.8)
        x, y = blk.get("xy", (0, 0))
        c = blk.get("color", COLOR_CYCLE[0])
        shape = blk.get("shape", "box")
        fs = blk.get("fontsize", 10)
        edge_lw = blk.get("edgewidth", 1.5)
        alpha = blk.get("alpha", 0.9)

        cx, cy = x + w / 2, y + h / 2

        if shape == "box":
            rect = FancyBboxPatch((x, y), w, h,
                                  boxstyle="round,pad=0.03",
                                  facecolor=c, edgecolor=c, alpha=alpha,
                                  linewidth=edge_lw, zorder=2)
            ax.add_patch(rect)
        elif shape == "diamond":
            pts = np.array([[cx, y], [x + w, cy], [cx, y + h], [x, cy]])
            diamond = plt.Polygon(pts, facecolor=c, edgecolor=c,
                                  alpha=alpha, linewidth=edge_lw, zorder=2)
            ax.add_patch(diamond)
        elif shape == "circle":
            r = max(w, h) / 2
            circle = plt.Circle((cx, cy), r, facecolor=c, edgecolor=c,
                                alpha=alpha, linewidth=edge_lw, zorder=2)
            ax.add_patch(circle)
        else:  # "round" - 圆角矩形
            rect = FancyBboxPatch((x, y), w, h,
                                  boxstyle="round,pad=0.15",
                                  facecolor=c, edgecolor=c, alpha=alpha,
                                  linewidth=edge_lw, zorder=2)
            ax.add_patch(rect)

        ax.text(cx, cy, text, ha="center", va="center",
                fontsize=fs, color="white", zorder=3)

    # 连接箭头
    if connections:
        for src, dst in connections:
            if src >= len(blocks) or dst >= len(blocks):
                continue
            b1 = blocks[src]
            b2 = blocks[dst]
            x1, y1 = b1["xy"][0] + b1["w"] / 2, b1["xy"][1] + b1["h"]
            x2, y2 = b2["xy"][0] + b2["w"] / 2, b2["xy"][1]
            ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                        arrowprops=dict(arrowstyle="->",
                                       color="#666666",
                                       lw=1.2,
                                       connectionstyle="arc3,rad=0"),
                        zorder=1)

    if title:
        ax.set_title(title)

    # auto-scale
    all_x = [b["xy"][0] for b in blocks] + [b["xy"][0] + b["w"] for b in blocks]
    all_y = [b["xy"][1] for b in blocks] + [b["xy"][1] + b["h"] for b in blocks]
    if all_x:
        mx = max(all_x) - min(all_x)
        ax.set_xlim(min(all_x) - mx * 0.15, max(all_x) + mx * 0.15)
    if all_y:
        my = max(all_y) - min(all_y)
        ax.set_ylim(min(all_y) - my * 0.15, max(all_y) + my * 0.15)

    return fig, ax

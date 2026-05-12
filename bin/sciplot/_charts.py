"""
科学绘图包 — 统计图表模块
"""

import numpy as np
import matplotlib.pyplot as plt
from ._config import color, COLOR_CYCLE, GRAYSCALE_CYCLE


def bar(
    categories: list[str],
    values,
    labels: list[str] | None = None,
    *,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    stacked: bool = False,
    horizontal: bool = False,
    width: float = 0.65,
    figsize: tuple | None = None,
    colors: list[str] | None = None,
    show_values: bool = False,
    value_format: str = "{:.1f}",
    legend: bool = True,
    legend_loc: str = "best",
    ylim: tuple | None = None,
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    柱状图 — 支持单组 / 分组 / 堆叠。

    参数:
        categories: 类别标签列表
        values:      单组时为一维列表，多组时为二维 [[组1值], [组2值], ...]
        labels:      多组时的图例标签
        show_values: 是否在柱子上显示数值
    """
    values = np.atleast_1d(np.asarray(values, dtype=float))
    multi = values.ndim == 2 and values.shape[0] > 1

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure

    n_cat = len(categories)
    if multi:
        n_series, n_cat = values.shape
        if labels is None:
            labels = [f"Series {i+1}" for i in range(n_series)]
    else:
        n_series = 1
        if values.ndim == 2:
            values = values.flatten()

    colors = colors or [color(i) for i in range(max(n_series, 1))]

    if horizontal:
        bar_func = ax.barh
    else:
        bar_func = ax.bar

    if multi:
        group_width = width
        bar_w = group_width / n_series
        positions = np.arange(n_cat)

        for i in range(n_series):
            offset = (i - (n_series - 1) / 2) * bar_w
            x = positions + offset
            bars = bar_func(x, values[i], bar_w,
                           label=labels[i] if legend else None,
                           color=colors[i % len(colors)],
                           zorder=3)
            if show_values:
                for b, v in zip(bars, values[i]):
                    if horizontal:
                        ax.text(v + (max(values[i]) * 0.01), b.get_y() + b.get_height()/2,
                                value_format.format(v), va="center", fontsize=9)
                    else:
                        ax.text(b.get_x() + b.get_width()/2, b.get_height(),
                                value_format.format(v), ha="center", va="bottom", fontsize=9)
        if horizontal:
            ax.set_yticks(positions)
            ax.set_yticklabels(categories)
        else:
            ax.set_xticks(positions)
            ax.set_xticklabels(categories)
    else:
        x = np.arange(n_cat)
        bars = bar_func(x, values, width, color=colors[0], zorder=3)
        if show_values:
            for b, v in zip(bars, values):
                if horizontal:
                    ax.text(v + (max(values) * 0.01), b.get_y() + b.get_height()/2,
                            value_format.format(v), va="center", fontsize=9)
                else:
                    ax.text(b.get_x() + b.get_width()/2, b.get_height(),
                            value_format.format(v), ha="center", va="bottom", fontsize=9)
        if horizontal:
            ax.set_yticks(x)
            ax.set_yticklabels(categories)
        else:
            ax.set_xticks(x)
            ax.set_xticklabels(categories)

    if title:
        ax.set_title(title)
    if xlabel and not horizontal:
        ax.set_xlabel(xlabel)
    if ylabel and not horizontal:
        ax.set_ylabel(ylabel)
    if horizontal:
        if xlabel:
            ax.set_xlabel(xlabel)
        if ylabel:
            ax.set_ylabel(ylabel)
    if ylim:
        ax.set_ylim(ylim)
    if multi and legend and labels:
        ax.legend(loc=legend_loc, framealpha=0.9)

    ax.grid(axis="y" if not horizontal else "x", alpha=0.35)
    return fig, ax


def line(
    x,
    y,
    labels: list[str] | None = None,
    *,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    markers: bool = False,
    marker_interval: int | None = None,
    colors: list[str] | None = None,
    linestyles: list[str] | None = None,
    linewidth: float | list | None = None,
    fill_between: bool = False,
    fill_alpha: float = 0.15,
    legend: bool = True,
    legend_loc: str = "best",
    xlim: tuple | None = None,
    ylim: tuple | None = None,
    figsize: tuple | None = None,
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    折线图 — 支持单线 / 多线 / 置信区间填充。

    参数:
        x:             X 值（一维数组）
        y:             Y 值，多组时为二维 [[组1], [组2], ...]
        labels:        图例标签
        markers:       是否显示数据点标记
        fill_between:  是否填充 Y 下方区域
    """
    y = np.asarray(y, dtype=float)
    x = np.asarray(x)
    multi = y.ndim == 2 and y.shape[0] > 1

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure

    if multi:
        n_series = y.shape[0]
        if labels is None:
            labels = [f"Line {i+1}" for i in range(n_series)]
    else:
        n_series = 1
        y = y.reshape(1, -1)

    colors = colors or [color(i) for i in range(n_series)]
    linestyles = linestyles or ["-"] * n_series
    lw = linewidth if linewidth else (1.8 if n_series <= 4 else 1.2)
    if isinstance(lw, (int, float)):
        lw = [lw] * n_series

    marker_list = ["o", "s", "D", "^", "v", "p", "*", "h"]

    for i in range(n_series):
        kw = dict(
            color=colors[i % len(colors)],
            linestyle=linestyles[i % len(linestyles)],
            linewidth=lw[i],
            label=labels[i] if legend else None,
            zorder=3,
        )
        if markers:
            kw["marker"] = marker_list[i % len(marker_list)]
            kw["markersize"] = 5
            if marker_interval and len(x) > marker_interval * 2:
                ax.plot(x, y[i], **kw, markevery=marker_interval)
            else:
                ax.plot(x, y[i], **kw)
        else:
            ax.plot(x, y[i], **kw)

        if fill_between:
            ax.fill_between(x, y[i], alpha=fill_alpha,
                            color=colors[i % len(colors)])

    if title:
        ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if xlim:
        ax.set_xlim(xlim)
    if ylim:
        ax.set_ylim(ylim)
    if multi and legend and labels:
        ax.legend(loc=legend_loc, framealpha=0.9)

    ax.grid(alpha=0.35)
    return fig, ax


def scatter(
    x,
    y,
    *,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    s: float = 20,
    c=None,
    cmap: str = "Blues",
    alpha: float = 0.7,
    edgecolors: str = "none",
    colorbar: bool = False,
    colorbar_label: str = "",
    fit_line: bool = False,
    fit_color: str = "#C44E52",
    fit_label: str = "趋势线",
    legend: bool = False,
    labels: list[str] | None = None,
    xlim: tuple | None = None,
    ylim: tuple | None = None,
    figsize: tuple | None = None,
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    散点图。

    参数:
        fit_line:   是否绘制拟合趋势线
        colorbar:   是否显示颜色条（c 参数为数值数组时）
        labels:     分类标签（用于图例，需相应设置 c 为颜色值）
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure

    sc = ax.scatter(x, y, s=s, c=c, cmap=cmap if c is not None else None,
                    alpha=alpha, edgecolors=edgecolors, zorder=3)

    if colorbar and c is not None:
        cb = fig.colorbar(sc, ax=ax)
        if colorbar_label:
            cb.set_label(colorbar_label)

    if fit_line:
        p = np.polyfit(x, y, 1)
        x_fit = np.linspace(min(x), max(x), 200)
        y_fit = np.polyval(p, x_fit)
        ax.plot(x_fit, y_fit, color=fit_color, linewidth=1.2,
                label=fit_label, linestyle="--", zorder=2)

    if title:
        ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if xlim:
        ax.set_xlim(xlim)
    if ylim:
        ax.set_ylim(ylim)

    ax.grid(alpha=0.35)
    return fig, ax


def histogram(
    data,
    labels: list[str] | None = None,
    *,
    bins: int | list = "auto",
    title: str = "",
    xlabel: str = "",
    ylabel: str = "频数",
    density: bool = False,
    cumulative: bool = False,
    alpha: float = 0.65,
    colors: list[str] | None = None,
    edgecolor: str = "white",
    legend: bool = True,
    legend_loc: str = "best",
    xlim: tuple | None = None,
    ylim: tuple | None = None,
    figsize: tuple | None = None,
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    直方图 — 支持多组重叠展示。

    参数:
        data:  一维数组或二维 [组1, 组2, ...]
        bins:  柱数或边界数组，同 matplotlib
    """
    data = np.asarray(data, dtype=float)
    multi = data.ndim == 2 and data.shape[0] > 1

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure

    colors = colors or [color(i) for i in range(3)]

    if multi:
        n_series = data.shape[0]
        if labels is None:
            labels = [f"Group {i+1}" for i in range(n_series)]
        for i in range(n_series):
            ax.hist(data[i], bins=bins, density=density, cumulative=cumulative,
                    alpha=alpha, color=colors[i % len(colors)],
                    edgecolor=edgecolor, label=labels[i] if legend else None)
    else:
        ax.hist(data, bins=bins, density=density, cumulative=cumulative,
                alpha=alpha, color=colors[0], edgecolor=edgecolor)

    if title:
        ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if xlim:
        ax.set_xlim(xlim)
    if ylim:
        ax.set_ylim(ylim)
    if multi and legend and labels:
        ax.legend(loc=legend_loc, framealpha=0.9)

    ax.grid(axis="y", alpha=0.35)
    return fig, ax


def boxplot(
    data,
    labels: list[str] | None = None,
    *,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    notch: bool = False,
    vert: bool = True,
    widths: float = 0.5,
    showfliers: bool = True,
    patch_artist: bool = True,
    colors: list[str] | None = None,
    meanline: bool = False,
    xlim: tuple | None = None,
    ylim: tuple | None = None,
    figsize: tuple | None = None,
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    箱线图 — 支持多组并列。

    参数:
        data:  二维 [[组1], [组2], ...]
    """
    if isinstance(data, (list, tuple)) and all(isinstance(d, (list, tuple, np.ndarray)) for d in data):
        pass  # already list of arrays
    else:
        data = np.asarray(data, dtype=float)
        if data.ndim == 1:
            data = [data]

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure

    n_groups = len(data)
    colors = colors or [color(i % len(COLOR_CYCLE)) for i in range(n_groups)]

    bp = ax.boxplot(data, labels=labels, notch=notch, vert=vert,
                    widths=widths, showfliers=showfliers,
                    patch_artist=patch_artist, meanline=meanline,
                    zorder=3)

    if patch_artist:
        for patch, c in zip(bp["boxes"], colors):
            patch.set_facecolor(c)
            patch.set_alpha(0.7)

    if title:
        ax.set_title(title)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if xlim:
        ax.set_xlim(xlim)
    if ylim:
        ax.set_ylim(ylim)

    ax.grid(axis="y" if vert else "x", alpha=0.35)
    return fig, ax


def pie(
    values,
    labels: list[str] | None = None,
    *,
    title: str = "",
    colors: list[str] | None = None,
    autopct: str = "{:.1f}%",
    pctdistance: float = 0.6,
    explode: list[float] | None = None,
    shadow: bool = False,
    startangle: float = 90,
    figsize: tuple | None = None,
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    饼图。

    参数:
        autopct: 数值格式，设为 None 则不显示
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize or (5, 5))
    else:
        fig = ax.figure

    values = np.asarray(values, dtype=float)
    colors = colors or [color(i) for i in range(len(values))]

    # 将格式字符串转为可调用对象，避免旧式 % 格式化兼容问题
    if isinstance(autopct, str):
        _fmt = autopct
        ap = lambda pct: _fmt.format(pct)
    else:
        ap = autopct

    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=colors,
        autopct=ap,
        pctdistance=pctdistance, explode=explode,
        shadow=shadow, startangle=startangle,
        textprops={"fontsize": 10},
    )

    if autotexts:
        for t in autotexts:
            t.set_fontsize(9)

    if title:
        ax.set_title(title)

    return fig, ax


def radar(
    categories: list[str],
    values,
    labels: list[str] | None = None,
    *,
    title: str = "",
    colors: list[str] | None = None,
    fill: bool = True,
    alpha: float = 0.15,
    linewidth: float = 1.6,
    figsize: tuple | None = None,
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    雷达图 / 蜘蛛网图 — 多维指标对比。

    参数:
        categories: 维度标签
        values:     二维 [[组1], [组2], ...]
    """
    values = np.atleast_2d(np.asarray(values, dtype=float))
    n_series = values.shape[0]
    n_cat = len(categories)

    if labels is None:
        labels = [f"Group {i+1}" for i in range(n_series)]

    angles = np.linspace(0, 2 * np.pi, n_cat, endpoint=False).tolist()
    angles += angles[:1]  # close the polygon

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize or (5, 5),
                               subplot_kw=dict(polar=True))
    else:
        fig = ax.figure

    colors = colors or [color(i) for i in range(n_series)]

    for i in range(n_series):
        v = values[i].tolist()
        v += v[:1]
        ax.plot(angles, v, "o-", color=colors[i % len(colors)],
                linewidth=linewidth, label=labels[i])
        if fill:
            ax.fill(angles, v, alpha=alpha, color=colors[i % len(colors)])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)
    ax.set_ylim(0, None)
    ax.set_title(title, pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.0),
              framealpha=0.9)

    return fig, ax

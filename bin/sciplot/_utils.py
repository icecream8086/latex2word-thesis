"""
科学绘图包 — 工具模块
"""

import inspect
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt


def _get_caller_script() -> Path | None:
    """尝试推断调用脚本的路径，用于自动确定输出目录。"""
    # sciplot 包所在目录
    package_dir = Path(__file__).parent.resolve()

    stack = inspect.stack()
    for frame in stack:
        filename = frame.filename
        if filename == "<stdin>" or filename.startswith("<"):
            continue
        p = Path(filename).resolve()
        # 跳过 sciplot 包内部模块
        if package_dir in p.parents:
            continue
        if p.exists() and p.suffix == ".py":
            return p
    return None


def savefig(
    fig_or_name,
    output_path: str | Path | None = None,
    *,
    dpi: int = 300,
    format: str | None = None,
    transparent: bool = False,
    bbox_inches: str = "tight",
    pad_inches: float = 0.05,
    **kwargs,
) -> Path:
    """
    智能保存图片。

    参数:
        fig_or_name: matplotlib Figure 对象，或输出文件名（不含扩展名）
        output_path: 输出路径。None 时自动推导：
                    - 如果调用脚本在 figures/sciplot/ 下，输出到同目录
                    - 否则输出到当前工作目录
        dpi:         输出 DPI（矢量图推荐 300，Word 导入友好）
        format:      输出格式，默认从扩展名推断，无扩展名时默认 SVG

    返回:
        保存的文件路径
    """
    from matplotlib.figure import Figure

    if isinstance(fig_or_name, Figure):
        fig = fig_or_name
        base_name = None
    elif isinstance(fig_or_name, str):
        fig = None  # 只给了名字，后面处理
        base_name = fig_or_name
    else:
        raise TypeError(f"需传入 Figure 对象或文件名, got {type(fig_or_name)}")

    # 确定输出目录和文件名基
    if output_path is not None:
        out = Path(output_path)
        if out.suffix:
            fmt = out.suffix.lstrip(".")
            out_dir = out.parent
            stem = out.stem
        else:
            out_dir = out
            stem = base_name or "figure"
            fmt = format or os.environ.get("SCIPLOT_FORMAT") or "svg"
    else:
        caller = _get_caller_script()
        if caller:
            out_dir = caller.parent
            stem = base_name or caller.stem
        else:
            out_dir = Path.cwd()
            stem = base_name or "figure"
        fmt = format or os.environ.get("SCIPLOT_FORMAT") or "svg"

    if format:
        fmt = format

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{stem}.{fmt}"

    if fig is None:
        fig = plt.gcf()

    fig.savefig(
        out_path,
        dpi=dpi,
        format=fmt,
        transparent=transparent,
        bbox_inches=bbox_inches,
        pad_inches=pad_inches,
        **kwargs,
    )

    plt.close(fig)
    print(f"  [保存] {out_path}")
    return out_path

#!/usr/bin/env python3
"""
sciplot 图片编译脚本

将 figures/sciplot/ 下的 Python 绘图脚本编译为 SVG/PNG 图片。
每个脚本创建自己的图表并调用 sp.savefig() 输出到同目录。

用法:
  python convert_sciplot.py                      # 编译所有脚本
  python convert_sciplot.py --watch              # 监听模式
  python convert_sciplot.py --file foo.py        # 编译单个文件
  python convert_sciplot.py --format svg         # 默认输出格式
  python convert_sciplot.py --help               # 查看帮助
"""

import argparse
import sys
import time
import traceback
from pathlib import Path


# 确保能找到 bin/ 下的 sciplot 包
_script_dir = Path(__file__).parent.resolve()
_bin_dir = _script_dir / "bin"
if str(_bin_dir) not in sys.path:
    sys.path.insert(0, str(_bin_dir))


# --- 配置 ------------------------------------------------------------------

SCRIPT_DIRS = ["figures/sciplot"]
DEFAULT_OUTPUT_DIR = "figures/sciplot"


def find_plot_scripts(project_root: Path) -> list[Path]:
    """在配置的目录中递归查找所有 .py 绘图脚本（排除 __init__.py）。"""
    files = []
    for d in SCRIPT_DIRS:
        target = project_root / d
        if target.is_dir():
            for f in sorted(target.rglob("*.py")):
                if f.name != "__init__.py":
                    files.append(f)
    return files


def execute_single(script_path: Path, output_format: str = "svg",
                   with_png: bool = True) -> bool:
    """
    执行单个绘图脚本。通过修改 __file__ 让脚本正确找到输出目录。

    返回是否成功。
    """
    script_path = script_path.resolve()
    if not script_path.exists():
        print(f"  [错误] 文件不存在: {script_path}", file=sys.stderr)
        return False

    # 构造脚本的 globals 上下文
    context = {
        "__file__": str(script_path),
        "__name__": "__main__",
        "__doc__": None,
        "__package__": None,
    }

    # 读取脚本源码
    try:
        source = script_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(f"  [编码错误] {script_path}: 文件不是有效的 UTF-8 编码", file=sys.stderr)
        return False

    # 注入 sciplot 到上下文，让脚本可以直接 import sciplot
    context["__builtins__"] = __builtins__

    try:
        # Set format in environment so sciplot.savefig can pick it up
        import os
        old_format = os.environ.get("SCIPLOT_FORMAT")
        os.environ["SCIPLOT_FORMAT"] = output_format

        exec(compile(source, str(script_path), "exec"), context)

        # 额外输出 PNG 格式（默认启用，--no-png 关闭）
        if with_png and output_format != "png":
            os.environ["SCIPLOT_FORMAT"] = "png"
            exec(compile(source, str(script_path), "exec"), context)

        if old_format is None:
            del os.environ["SCIPLOT_FORMAT"]
        else:
            os.environ["SCIPLOT_FORMAT"] = old_format

        print(f"  [成功] {script_path}")
        return True

    except Exception as e:
        print(f"  [失败] {script_path}", file=sys.stderr)
        tb = traceback.format_exc()
        # 只显示最后几行
        lines = tb.strip().split("\n")
        for line in lines[-5:]:
            print(f"         {line}", file=sys.stderr)
        return False


def execute_all(scripts: list[Path], output_format: str = "svg",
                with_png: bool = True) -> tuple[int, int]:
    """执行一批脚本，返回 (成功数, 总数)。"""
    success = 0
    total = len(scripts)

    if not total:
        print("未找到任何 Python 绘图脚本。")
        return 0, 0

    for f in scripts:
        ok = execute_single(f, output_format, with_png)
        if ok:
            success += 1
        if not ok and total == 1:
            sys.exit(1)

    return success, total


# --- 监听模式 ---------------------------------------------------------------

def watch_mode(project_root: Path, interval: float = 2.0,
               output_format: str = "svg",
               with_png: bool = True):
    """监听模式：轮询脚本变更，有变动时自动执行。"""
    def get_snapshot() -> dict[Path, float]:
        return {f: f.stat().st_mtime for f in find_plot_scripts(project_root)
                if f.exists()}

    snapshot = get_snapshot()
    print(f"监听模式已启动 (轮询间隔 {interval}s)，按 Ctrl+C 退出...")
    print(f"监控目录: {[str(project_root / d) for d in SCRIPT_DIRS]}")

    try:
        while True:
            time.sleep(interval)
            current = get_snapshot()
            changed = []
            deleted = []

            for path, mtime in current.items():
                old = snapshot.get(path)
                if old is None or mtime > old:
                    changed.append(path)

            for path in snapshot:
                if path not in current:
                    deleted.append(path)

            if changed:
                print(f"\n检测到 {len(changed)} 个文件变更:")
                for f in changed:
                    ok = execute_single(f, output_format, with_png)
                    status = "成功" if ok else "失败"
                    print(f"  [{status}] {f}")

            if deleted:
                print(f"\n以下 {len(deleted)} 个文件已删除:")
                for f in deleted:
                    print(f"  - {f}")

            snapshot = current

    except KeyboardInterrupt:
        print("\n监听已停止。")


# --- CLI --------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="sciplot 图片编译工具 — 将 Python 绘图脚本编译为 SVG/PNG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  %(prog)s                      编译 figures/sciplot/ 下所有脚本\n"
            "  %(prog)s --watch              监听模式\n"
            "  %(prog)s --file foo.py        编译单个脚本\n"
            "  %(prog)s --format png         输出 PNG 格式\n"
        ),
    )
    parser.add_argument("--watch", "-w", action="store_true",
                        help="监听模式：文件变更时自动编译")
    parser.add_argument("--file", "-f", type=str, default=None,
                        help="编译指定脚本（而非全部）")
    parser.add_argument("--format", type=str, default="svg",
                        choices=["svg", "png"],
                        help="输出格式（默认: svg）")
    parser.add_argument("--no-png", action="store_true",
                        help="跳过 PNG 输出")
    parser.add_argument("--interval", "-i", type=float, default=2.0,
                        help="监听模式轮询间隔（秒，默认: 2.0）")

    args = parser.parse_args()

    if args.file:
        project_root = Path(args.file).resolve().parent.parent.parent
    else:
        project_root = Path(__file__).parent.resolve()

    # 单文件模式
    if args.file:
        script_file = Path(args.file)
        if not script_file.exists():
            print(f"错误: 文件不存在: {script_file}", file=sys.stderr)
            sys.exit(1)
        print(f"正在编译: {script_file} -> {args.format}")
        success = execute_single(script_file, args.format, not args.no_png)
        if success:
            print("完成。")
        else:
            sys.exit(1)
        return

    # 监听模式
    if args.watch:
        watch_mode(project_root, args.interval, args.format, not args.no_png)
        return

    # 默认：编译所有
    scripts = find_plot_scripts(project_root)
    if not scripts:
        print(f"未找到任何 Python 绘图脚本。")
        print(f"请在 figures/sciplot/ 下创建 .py 文件，或在 {SCRIPT_DIRS} 中配置。")
        return

    print(f"正在编译 {len(scripts)} 个 sciplot 绘图脚本...")
    print(f"输出格式: {args.format}")

    success, total = execute_all(scripts, args.format, not args.no_png)
    print(f"完成: {success}/{total} 个脚本编译成功。")

    if success < total:
        sys.exit(1)


if __name__ == "__main__":
    main()

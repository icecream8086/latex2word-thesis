#!/usr/bin/env python3
"""
Chen 式 ER 图编译脚本

将 figures/chen_er/ 下的 Python 脚本编译为 SVG/PNG 图片。
每个脚本使用 chen_er.py 库定义 E-R 图，并调用 diagram.render() 输出。

用法:
  python convert_chen_er.py                      # 编译所有脚本
  python convert_chen_er.py --watch              # 监听模式
  python convert_chen_er.py --file foo.py        # 编译单个文件
  python convert_chen_er.py --format svg         # 默认输出格式
  python convert_chen_er.py --help               # 查看帮助
"""

import argparse
import sys
import time
import traceback
from pathlib import Path


# --- 配置 ------------------------------------------------------------------

SCRIPT_DIRS = ["figures/chen_er"]
DEFAULT_OUTPUT_DIR = "figures/chen_er"


def _read_ignore_list(project_root: Path):
    """读取 ignore.yaml 忽略列表，返回要跳过的文件名集合。

    文件不存在时创建模板（含注释），然后返回 None 表示编译全部。
    """
    path = project_root / "figures" / "chen_er" / "ignore.yaml"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Chen ER 图编译忽略列表 — 在此列出的 .py 完全不会编译\n"
            "# 用于已手动转成 drawio 编辑的脚本，防止覆盖\n"
            "# 格式:\n"
            "# - xxx.py\n",
            encoding="utf-8",
        )
        return None
    names = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("- ") and line.endswith(".py"):
            names.add(line[2:].strip())
    return names


def find_er_scripts(project_root: Path) -> list[Path]:
    """在配置的目录中递归查找 .py ER 图脚本（排除 __init__.py 和 ignore.yaml 中列出的）。"""
    ignore_list = _read_ignore_list(project_root)
    files = []
    for d in SCRIPT_DIRS:
        target = project_root / d
        if target.is_dir():
            for f in sorted(target.rglob("*.py")):
                if f.name == "__init__.py":
                    continue
                if ignore_list is not None and f.name in ignore_list:
                    print(f"  [跳过] {f.name} (在 ignore.yaml 中)")
                    continue
                files.append(f)
    return files


def execute_single(script_path: Path, output_format: str = "svg",
                   with_png: bool = True) -> bool:
    """
    执行单个 ER 图脚本。脚本调用 diagram.render("output.svg") 输出 SVG。
    自动根据 output_format 派生 PNG（通过 cairosvg 转换）。

    返回是否成功。
    """
    script_path = script_path.resolve()
    if not script_path.exists():
        print(f"  [错误] 文件不存在: {script_path}", file=sys.stderr)
        return False

    context = {
        "__file__": str(script_path),
        "__name__": "__main__",
        "__doc__": None,
        "__package__": None,
    }

    try:
        source = script_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(f"  [编码错误] {script_path}: 文件不是有效的 UTF-8 编码", file=sys.stderr)
        return False

    context["__builtins__"] = __builtins__
    import os

    try:
        os.environ["CHEN_ER_FORMAT"] = output_format
        exec(compile(source, str(script_path), "exec"), context)

        # PNG 转换：从 SVG 转换（不重新执行脚本）
        if with_png and output_format == "svg":
            svg_path = script_path.with_suffix(".svg")
            # 脚本可能输出到 figures/chen_er/ 下，尝试找到实际的 .svg 文件
            script_output = script_path.parent / script_path.stem
            svg_output = script_output.with_suffix(".svg")
            if svg_output.exists():
                png_output = script_output.with_suffix(".png")
                _convert_svg_to_png(svg_output, png_output)

        print(f"  [成功] {script_path}")
        return True

    except Exception as e:
        print(f"  [失败] {script_path}", file=sys.stderr)
        tb = traceback.format_exc()
        lines = tb.strip().split("\n")
        for line in lines[-5:]:
            print(f"         {line}", file=sys.stderr)
        return False


def _convert_svg_to_png(svg_path: Path, png_path: Path):
    """将 SVG 转换为 PNG。尝试 cairosvg → rsvg-convert → inkscape。"""
    try:
        import cairosvg
        cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), dpi=200)
        print(f"  PNG 已生成: {png_path}")
        return
    except ImportError:
        pass

    import subprocess
    try:
        subprocess.run(["rsvg-convert", "-f", "png", "-o", str(png_path),
                        "-d", "200", "-p", "200", str(svg_path)],
                       check=True, capture_output=True)
        print(f"  PNG 已生成 (rsvg-convert): {png_path}")
        return
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    try:
        subprocess.run(["inkscape", str(svg_path), "-o", str(png_path),
                        "-d", "200"],
                       check=True, capture_output=True)
        print(f"  PNG 已生成 (inkscape): {png_path}")
        return
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    print(f"  [提示] 跳过 PNG（需安装 cairosvg: pip install cairosvg）")


def execute_all(scripts: list[Path], output_format: str = "svg",
                with_png: bool = True) -> tuple[int, int]:
    """执行一批脚本，返回 (成功数, 总数)。"""
    success = 0
    total = len(scripts)

    if not total:
        print("未找到任何 Chen ER 图脚本。")
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
               output_format: str = "svg", with_png: bool = True):
    """监听模式：轮询脚本变更，有变动时自动执行。"""
    def get_snapshot() -> dict[Path, float]:
        return {f: f.stat().st_mtime for f in find_er_scripts(project_root)
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
        description="Chen 式 ER 图编译工具 — 将 Python ER 图脚本编译为 SVG/PNG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  %(prog)s                        编译 figures/chen_er/ 下所有脚本\n"
            "  %(prog)s --watch                监听模式\n"
            "  %(prog)s --file foo.py          编译单个脚本\n"
            "  %(prog)s --format png           输出 PNG 格式\n"
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
    scripts = find_er_scripts(project_root)
    if not scripts:
        print(f"未找到任何 Chen ER 图脚本。")
        print(f"请在 figures/chen_er/ 下创建 .py 文件。")
        return

    # 注入根的 sys.path ，让脚本能 import chen_er
    root = Path(__file__).parent.resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    print(f"正在编译 {len(scripts)} 个 Chen ER 图脚本...")
    print(f"输出格式: {args.format}")

    success, total = execute_all(scripts, args.format, not args.no_png)
    print(f"完成: {success}/{total} 个脚本编译成功。")

    if success < total:
        sys.exit(1)


if __name__ == "__main__":
    main()

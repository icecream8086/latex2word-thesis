#!/usr/bin/env python3
"""
Mermaid 图片编译脚本

将 .mmd 文件编译为 SVG/PNG，支持手动单次转换和自动监听模式。
使用 mermaid-cli (mmdc) 进行渲染。

用法:
  python convert_mermaid.py                     # 编译所有 mmd 文件
  python convert_mermaid.py --watch             # 监听模式，文件变动时自动编译
  python convert_mermaid.py --file xxx.mmd      # 编译指定文件
  python convert_mermaid.py --format png         # 输出为 PNG 格式
  python convert_mermaid.py --format both        # 同时输出 SVG + PNG
  python convert_mermaid.py --theme dark        # 使用深色主题
  python convert_mermaid.py --charset GBK       # 源文件为 GBK 编码
  python convert_mermaid.py --help              # 查看帮助
"""

import argparse
import locale
import subprocess
import sys
import time
from pathlib import Path


# --- 配置 ------------------------------------------------------------------

# 搜索 mmd 文件的目录（相对于项目根目录）
MMD_DIRS = ["figures"]
# 默认输出格式
DEFAULT_OUTPUT_FORMAT = "png"
# 默认主题
DEFAULT_THEME = "default"
# 默认背景色
DEFAULT_BG_COLOR = "white"


def find_mmdc() -> str:
    """
    查找 mmdc 命令路径。
    优先使用 bin/mermaid/node_modules/.bin/ 下的本地安装，
    找不到则 fallback 到 PATH 中的全局 mmdc。
    """
    local_dir = (
        Path(__file__).parent / "bin" / "mermaid" / "node_modules" / ".bin"
    )
    # Windows 上必须用 .cmd 包装器，不能用无扩展名的脚本文件
    if sys.platform == "win32":
        candidates = [
            local_dir / "mmdc.cmd",
            local_dir / "mmdc",
        ]
    else:
        candidates = [
            local_dir / "mmdc",
            local_dir / "mmdc.cmd",
        ]
    for p in candidates:
        if p.exists():
            return str(p)
    return "mmdc"


# --- 编码辅助 ---------------------------------------------------------------

def get_system_encoding() -> str:
    """获取终端/系统编码，非 UTF-8 环境（如 GBK）时用于 fallback。"""
    enc = locale.getpreferredencoding()
    return enc if enc.upper() != "UTF-8" else None


def safe_decode(data: bytes) -> str:
    """尝试用 UTF-8 解码，失败则 fallback 到系统编码（如 GBK）。"""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        enc = get_system_encoding() or "gbk"
        return data.decode(enc, errors="replace")


def safe_print(text: str, file=None):
    """安全打印，当 stdout/stderr 不是 UTF-8 时避免 UnicodeEncodeError。"""
    out = file or sys.stdout
    try:
        print(text, file=out)
    except UnicodeEncodeError:
        enc = out.encoding or "utf-8"
        print(text.encode(enc, errors="replace").decode(enc), file=out)


# --- 核心转换逻辑 -----------------------------------------------------------

def find_mmd_files(project_root: Path) -> list[Path]:
    """在配置的目录中递归查找所有 .mmd 文件。"""
    files = []
    for d in MMD_DIRS:
        target = (project_root / d)
        if target.is_dir():
            files.extend(sorted(target.rglob("*.mmd")))
    return files


def _run_mmdc(mmd_file: Path, output_file: Path, theme: str = "default",
              bg_color: str = "white", width: int = None,
              height: int = None) -> bool:
    """执行单次 mmdc 渲染，返回是否成功。"""
    mmdc_cmd = find_mmdc()
    cmd = [mmdc_cmd, "-i", str(mmd_file), "-o", str(output_file)]

    if theme:
        cmd.extend(["-t", theme])
    if bg_color:
        cmd.extend(["-b", bg_color])
    if width:
        cmd.extend(["-w", str(width)])
    if height:
        cmd.extend(["-H", str(height)])

    try:
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            err_text = safe_decode(result.stderr).strip()
            safe_print(f"  [失败] {mmd_file}", file=sys.stderr)
            if err_text:
                safe_print(f"         {err_text}", file=sys.stderr)
            return False

        out_text = safe_decode(result.stdout).strip()
        if out_text:
            safe_print(f"  [成功] {mmd_file} -> {output_file} ({out_text})")
        else:
            safe_print(f"  [成功] {mmd_file} -> {output_file}")
        return True

    except FileNotFoundError:
        mmdc_cmd = find_mmdc()
        safe_print(
            f"  [错误] 找不到命令 '{mmdc_cmd}'，请先安装:\n"
            f"         cd bin/mermaid && npm install",
            file=sys.stderr)
        return False
    except Exception as e:
        safe_print(f"  [错误] {mmd_file}: {e}", file=sys.stderr)
        return False


def convert_single(mmd_file: Path, output_format: str = "png",
                   theme: str = "default", bg_color: str = "white",
                   width: int = None, height: int = None,
                   charset: str = "UTF-8") -> bool:
    """
    编译单个 mmd 文件，返回是否成功。

    参数:
        mmd_file: mmd 源文件路径
        output_format: 输出格式（png/svg/both，both 表示同时输出 SVG+PNG）
        theme: Mermaid 主题
        bg_color: 背景色
        width: 输出图片宽度（像素）
        height: 输出图片高度（像素）
        charset: 源文件编码（仅用于校验提示，mmdc 自身处理文件读取）
    """
    # 预检源文件编码，提前给出明确提示
    if charset.upper() != "UTF-8":
        safe_print(f"  提示: {mmd_file} 使用 {charset} 编码", file=sys.stderr)
    else:
        try:
            with open(mmd_file, "r", encoding="utf-8") as f:
                f.read()
        except UnicodeDecodeError:
            safe_print(
                f"  [编码错误] {mmd_file}: 文件不是有效的 UTF-8 编码\n"
                f"             请尝试 --charset GBK 或转换为 UTF-8",
                file=sys.stderr)
            return False

    # both 模式：依次输出 SVG 和 PNG
    if output_format == "both":
        ok_svg = _run_mmdc(mmd_file, mmd_file.with_suffix(".svg"),
                           theme, bg_color, width, height)
        ok_png = _run_mmdc(mmd_file, mmd_file.with_suffix(".png"),
                           theme, bg_color, width, height)
        return ok_svg and ok_png

    output_file = mmd_file.with_suffix(f".{output_format}")
    ok = _run_mmdc(mmd_file, output_file, theme, bg_color, width, height)

    return ok


def convert_all(mmd_files: list[Path], output_format: str = "png",
                theme: str = "default", bg_color: str = "white",
                width: int = None, height: int = None,
                charset: str = "UTF-8") -> tuple[int, int]:
    """编译一批 mmd 文件，返回 (成功数, 总数)。"""
    success = 0
    total = len(mmd_files)

    if not total:
        safe_print("未找到任何 .mmd 文件。")
        return 0, 0

    for f in mmd_files:
        ok = convert_single(f, output_format, theme, bg_color, width, height, charset)
        if ok:
            success += 1
        if not ok and total == 1:
            sys.exit(1)

    return success, total


# --- 监听模式 ---------------------------------------------------------------

def watch_mode(project_root: Path, interval: float = 2.0,
               output_format: str = "png", theme: str = "default",
               bg_color: str = "white", width: int = None, height: int = None,
               charset: str = "UTF-8"):
    """
    监听模式：轮询 mmd 文件变更，有变动时自动编译。
    """
    def get_snapshot() -> dict[Path, float]:
        return {f: f.stat().st_mtime for f in find_mmd_files(project_root)
                if f.exists()}

    snapshot = get_snapshot()
    safe_print(f"监听模式已启动 (轮询间隔 {interval}s)，按 Ctrl+C 退出...")
    safe_print(f"监控目录: {[str(project_root / d) for d in MMD_DIRS]}")

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
                safe_print(f"\n检测到 {len(changed)} 个文件变更:")
                for f in changed:
                    ok = convert_single(f, output_format, theme, bg_color, width, height, charset)
                    status = "成功" if ok else "失败"
                    safe_print(f"  [{status}] {f}")

            if deleted:
                safe_print(f"\n以下 {len(deleted)} 个文件已删除:")
                for f in deleted:
                    safe_print(f"  - {f}")

            snapshot = current

    except KeyboardInterrupt:
        safe_print("\n监听已停止。")


# --- 辅助函数 ---------------------------------------------------------------

def check_and_warn_encoding(mmd_files: list[Path]):
    """检查 mmd 文件的编码，对非 UTF-8 文件给出警告。"""
    non_utf8 = []
    for f in mmd_files:
        try:
            with open(f, "rb") as fp:
                raw = fp.read(4)
            if raw.startswith(b"\xef\xbb\xbf"):
                safe_print(f"  提示: {f.name} 包含 UTF-8 BOM，建议移除（使用 without BOM）")
            with open(f, "r", encoding="utf-8") as fp:
                fp.read(100)
        except UnicodeDecodeError:
            non_utf8.append(f)

    if non_utf8:
        safe_print(
            "\n警告：以下文件不是 UTF-8 编码，可能导致编译失败：",
            file=sys.stderr)
        for f in non_utf8:
            safe_print(f"  - {f}", file=sys.stderr)
        safe_print("请使用以下命令转换编码：", file=sys.stderr)
        safe_print("  iconv -f gbk -t utf-8 input.mmd > output.mmd", file=sys.stderr)
        safe_print("  或在 VSCode / Notepad++ 中另存为 UTF-8 编码\n", file=sys.stderr)


# --- CLI --------------------------------------------------------------------

def main():
    # 优先确保 Python I/O 使用 UTF-8，降低终端编码带来的风险
    if not sys.stdout.encoding or sys.stdout.encoding.upper() not in ("UTF-8", "UTF8"):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Mermaid 图片编译工具 — 将 .mmd 编译为 SVG/PNG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  %(prog)s                    编译所有 mmd 文件\n"
            "  %(prog)s --watch            监听模式\n"
            "  %(prog)s --file foo.mmd     编译单个文件\n"
            "  %(prog)s --format svg       输出为 SVG 格式\n"
            "  %(prog)s --format both      同时输出 SVG + PNG 两种格式\n"
            "  %(prog)s --theme dark       使用深色主题\n"
            "  %(prog)s --charset GBK      源文件为 GBK 编码\n"
        ),
    )
    parser.add_argument("--watch", "-w", action="store_true",
                        help="监听模式：文件变更时自动编译")
    parser.add_argument("--file", "-f", type=str, default=None,
                        help="编译指定 mmd 文件（而非全部）")
    parser.add_argument("--format", type=str, default=DEFAULT_OUTPUT_FORMAT,
                        choices=["png", "svg", "both"],
                        help=f"输出格式（默认: {DEFAULT_OUTPUT_FORMAT}，both 表示同时输出 SVG+PNG）")
    parser.add_argument("--theme", "-t", type=str, default=DEFAULT_THEME,
                        choices=["default", "dark", "neutral", "forest", "base"],
                        help=f"Mermaid 主题（默认: {DEFAULT_THEME}）")
    parser.add_argument("--background", "-b", type=str, default=DEFAULT_BG_COLOR,
                        help=f"背景色（默认: {DEFAULT_BG_COLOR}）")
    parser.add_argument("--width", type=int, default=None,
                        help="输出图片宽度（像素）")
    parser.add_argument("--height", type=int, default=None,
                        help="输出图片高度（像素）")
    parser.add_argument("--interval", "-i", type=float, default=2.0,
                        help="监听模式轮询间隔（秒，默认: 2.0）")
    parser.add_argument("--charset", "-c", type=str, default="UTF-8",
                        help="mmd 源文件编码（默认: UTF-8，GBK 终端可设为 GBK）")
    parser.add_argument("--check-encoding", action="store_true",
                        help="检查所有 mmd 文件的编码并给出警告")

    args = parser.parse_args()

    if args.file:
        project_root = Path(args.file).resolve().parent.parent
    else:
        project_root = Path(__file__).parent.resolve()

    charset = args.charset.upper()

    # 编码检查模式
    if args.check_encoding:
        mmd_files = find_mmd_files(project_root)
        if not mmd_files:
            safe_print("未找到任何 .mmd 文件。")
            return
        check_and_warn_encoding(mmd_files)
        return

    # 单文件模式
    if args.file:
        mmd_file = Path(args.file)
        if not mmd_file.exists():
            safe_print(f"错误: 文件不存在: {mmd_file}", file=sys.stderr)
            sys.exit(1)
        safe_print(f"正在编译: {mmd_file} -> {args.format} (编码: {charset})")
        success = convert_single(mmd_file, args.format, args.theme,
                                  args.background, args.width, args.height, charset)
        if success:
            safe_print("完成。")
        else:
            sys.exit(1)
        return

    # 监听模式
    if args.watch:
        watch_mode(project_root, args.interval, args.format, args.theme,
                   args.background, args.width, args.height, charset)
        return

    # 默认：编译所有
    mmd_files = find_mmd_files(project_root)
    if not mmd_files:
        safe_print("未找到任何 .mmd 文件。")
        return

    safe_print(f"正在编译 {len(mmd_files)} 个 Mermaid 文件...")
    safe_print(f"输出格式: {args.format}")

    # 可选：先检查编码
    if charset == "UTF-8":
        check_and_warn_encoding(mmd_files)

    success, total = convert_all(mmd_files, args.format, args.theme,
                                  args.background, args.width, args.height, charset)
    safe_print(f"完成: {success}/{total} 个文件编译成功。")

    if success < total:
        sys.exit(1)


if __name__ == "__main__":
    main()

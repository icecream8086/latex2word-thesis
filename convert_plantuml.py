#!/usr/bin/env python3
"""
PlantUML 图片编译脚本

将 .puml 文件编译为 SVG/PNG，支持手动单次转换和自动监听模式。
支持 UTF-8 编码，确保中文正确显示。

用法:
  python convert_plantuml.py                  # 编译所有 puml 文件（默认 SVG）
  python convert_plantuml.py --watch          # 监听模式，文件变动时自动编译
  python convert_plantuml.py --file xxx.puml  # 编译指定文件
  python convert_plantuml.py --format png     # 输出为 PNG 格式
  python convert_plantuml.py --format both    # 同时输出 SVG + PNG
  python convert_plantuml.py --help           # 查看帮助
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


# --- 配置 ------------------------------------------------------------------

# PlantUML JAR 路径（相对于项目根目录或绝对路径）
JAR_PATH = Path(__file__).parent / "bin" / "plantuml-1.2024.6.jar"
# 搜索 puml 文件的目录（相对于项目根目录）
PUML_DIRS = ["figures"]
# 默认输出格式
DEFAULT_OUTPUT_FORMAT = "svg"
# Java 命令
JAVA_CMD = "java"
# Java 编码参数（UTF-8）
JAVA_ENCODING_OPTS = ["-Dfile.encoding=UTF-8", "-Dsun.jnu.encoding=UTF-8"]


# --- 核心转换逻辑 -----------------------------------------------------------

def find_puml_files(project_root: Path) -> list[Path]:
    """在配置的目录中递归查找所有 .puml 文件。"""
    files = []
    for d in PUML_DIRS:
        target = (project_root / d)
        if target.is_dir():
            files.extend(sorted(target.rglob("*.puml")))
    return files


def _run_plantuml(jar: Path, puml_file: Path, check_metadata: bool,
                  charset: str, output_format: str) -> bool:
    """执行单次 PlantUML 编译，返回是否成功。"""
    cmd = [JAVA_CMD] + JAVA_ENCODING_OPTS + ["-jar", str(jar)]

    if check_metadata:
        cmd.append("-checkmetadata")

    if output_format == "svg":
        cmd.append("-tsvg")
    elif output_format == "png":
        cmd.append("-tpng")

    cmd.extend(["-charset", charset])
    cmd.append(str(puml_file))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        if result.returncode != 0:
            print(f"  [失败] {puml_file} ({output_format})", file=sys.stderr)
            if result.stderr.strip():
                print(f"         {result.stderr.strip()}", file=sys.stderr)
            return False
        if result.stdout.strip():
            print(f"  [成功] {puml_file} -> {result.stdout.strip()}")
        else:
            print(f"  [成功] {puml_file} ({output_format})")
        return True
    except Exception as e:
        print(f"  [错误] {puml_file}: {e}", file=sys.stderr)
        return False


def _convert_svg_to_pdf(svg_path: Path, pdf_path: Path) -> bool:
    """将 SVG 文件转换为 PDF，支持 cairosvg 和 svglib 两种后端。"""
    svg_path = Path(svg_path)
    pdf_path = Path(pdf_path)

    if not svg_path.exists():
        print(f"  [错误] SVG 文件不存在: {svg_path}", file=sys.stderr)
        return False

    # 优先使用 cairosvg
    try:
        import cairosvg
        cairosvg.svg2pdf(url=str(svg_path), write_to=str(pdf_path))
        print(f"  [成功] {svg_path.name} -> {pdf_path.name}")
        return True
    except ImportError:
        pass

    # 备选 svglib + reportlab（纯 Python，无需 C 扩展）
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPDF
        drawing = svg2rlg(str(svg_path))
        if drawing is None:
            print(f"  [失败] {svg_path.name}: svglib 无法解析此 SVG", file=sys.stderr)
            return False
        renderPDF.drawToFile(drawing, str(pdf_path))
        print(f"  [成功] {svg_path.name} -> {pdf_path.name}")
        return True
    except ImportError:
        pass

    print(f"  [错误] 无法将 SVG 转换为 PDF，请安装:", file=sys.stderr)
    print(f"          pip install cairosvg", file=sys.stderr)
    print(f"         或 pip install svglib reportlab", file=sys.stderr)
    return False


def convert_single(jar: Path, puml_file: Path, check_metadata: bool = True,
                   charset: str = "UTF-8", output_format: str = "svg",
                   with_pdf: bool = False) -> bool:
    """
    编译单个 puml 文件，返回是否成功。

    参数:
        jar: PlantUML JAR 文件路径
        puml_file: puml 源文件路径
        check_metadata: 是否检查元数据（增量编译）
        charset: 源文件编码（默认 UTF-8）
        output_format: 输出格式（png/svg/both，默认 svg）
        with_pdf: 是否额外输出 PDF 格式
    """
    # 预检源文件编码
    try:
        with open(puml_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if content.startswith('﻿'):
                print(f"  警告: {puml_file} 包含 BOM 头，建议另存为 UTF-8 without BOM",
                      file=sys.stderr)
    except UnicodeDecodeError as e:
        print(f"  [编码错误] {puml_file}: 文件不是有效的 UTF-8 编码", file=sys.stderr)
        print(f"             请将文件转换为 UTF-8 编码: {e}", file=sys.stderr)
        return False

    # both 模式：依次输出 SVG 和 PNG
    if output_format == "both":
        ok_svg = _run_plantuml(jar, puml_file, check_metadata, charset, "svg")
        ok_png = _run_plantuml(jar, puml_file, check_metadata, charset, "png")
        ok_pdf = True
        if with_pdf:
            ok_pdf = _convert_svg_to_pdf(puml_file.with_suffix(".svg"),
                                         puml_file.with_suffix(".pdf"))
        return ok_svg and ok_png and ok_pdf

    ok = _run_plantuml(jar, puml_file, check_metadata, charset, output_format)

    if with_pdf and output_format != "pdf":
        # PNG 格式没有 SVG 文件，需要先生成 SVG 再转 PDF
        if output_format == "png":
            _run_plantuml(jar, puml_file, check_metadata, charset, "svg")
        ok_pdf = _convert_svg_to_pdf(puml_file.with_suffix(".svg"),
                                     puml_file.with_suffix(".pdf"))
        return ok and ok_pdf

    return ok


def convert_all(jar: Path, puml_files: list[Path],
                check_metadata: bool = True, charset: str = "UTF-8",
                output_format: str = "svg",
                with_pdf: bool = False) -> tuple[int, int]:
    """编译一批 puml 文件，返回 (成功数, 总数)。"""
    success = 0
    total = len(puml_files)

    if not total:
        print("未找到任何 .puml 文件。")
        return 0, 0

    for f in puml_files:
        ok = convert_single(jar, f, check_metadata, charset, output_format, with_pdf)
        if ok:
            success += 1
        # 单文件模式：失败时直接退出
        if not ok and total == 1:
            sys.exit(1)

    return success, total


# --- 监听模式 ---------------------------------------------------------------

def watch_mode(jar: Path, project_root: Path, interval: float = 2.0,
               check_metadata: bool = True, charset: str = "UTF-8",
               output_format: str = "svg",
               with_pdf: bool = False):
    """
    监听模式：轮询 puml 文件变更，有变动时自动编译。
    无需安装 watchdog，纯依赖文件 mtime 轮询。
    """
    # 构建 {路径: mtime} 映射
    def get_snapshot() -> dict[Path, float]:
        return {f: f.stat().st_mtime for f in find_puml_files(project_root)
                if f.exists()}

    snapshot = get_snapshot()
    print(f"监听模式已启动 (轮询间隔 {interval}s)，按 Ctrl+C 退出...")
    print(f"监控目录: {[str(project_root / d) for d in PUML_DIRS]}")
    print(f"输出格式: {output_format}")
    print(f"文件编码: {charset}")

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
                    ok = convert_single(jar, f, check_metadata, charset, output_format, with_pdf)
                    status = "成功" if ok else "失败"
                    print(f"  [{status}] {f}")

            if deleted:
                print(f"\n以下 {len(deleted)} 个文件已删除:")
                for f in deleted:
                    print(f"  - {f}")

            snapshot = current

    except KeyboardInterrupt:
        print("\n监听已停止。")


# --- 辅助函数 ---------------------------------------------------------------

def check_and_warn_encoding(puml_files: list[Path]):
    """检查 puml 文件的编码，对非 UTF-8 文件给出警告。"""
    non_utf8 = []
    for f in puml_files:
        try:
            with open(f, 'rb') as fp:
                raw = fp.read(4)
                # 检查 UTF-8 BOM
                if raw.startswith(b'\xef\xbb\xbf'):
                    print(f"  提示: {f.name} 包含 UTF-8 BOM，建议移除（使用 without BOM）")
                # 简单检查是否为有效 UTF-8（读取前几个字符）
                with open(f, 'r', encoding='utf-8') as fp:
                    fp.read(100)
        except UnicodeDecodeError:
            non_utf8.append(f)

    if non_utf8:
        print("\n警告：以下文件不是 UTF-8 编码，可能导致编译失败：", file=sys.stderr)
        for f in non_utf8:
            print(f"  - {f}", file=sys.stderr)
        print("请使用以下命令转换编码：", file=sys.stderr)
        print("  iconv -f gbk -t utf-8 input.puml > output.puml", file=sys.stderr)
        print("  或在 VSCode/Notepad++ 中另存为 UTF-8 编码\n", file=sys.stderr)


# --- CLI --------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PlantUML 图片编译工具 — 将 .puml 编译为 SVG/PNG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  %(prog)s                    编译所有 puml 文件\n"
            "  %(prog)s --watch            监听模式\n"
            "  %(prog)s --file foo.puml    编译单个文件\n"
            "  %(prog)s --no-check         全量重新编译（忽略缓存）\n"
            "  %(prog)s --format svg       输出为 SVG 格式（默认）\n"
            "  %(prog)s --format png       输出为 PNG 格式\n"
            "  %(prog)s --format both      同时输出 SVG + PNG 两种格式\n"
            "  %(prog)s --jar path/to/jar  指定 PlantUML JAR 路径\n"
            "  %(prog)s --charset GBK      使用 GBK 编码读取源文件\n"
        ),
    )
    parser.add_argument("--watch", "-w", action="store_true",
                        help="监听模式：文件变更时自动编译")
    parser.add_argument("--file", "-f", type=str, default=None,
                        help="编译指定 puml 文件（而非全部）")
    parser.add_argument("--no-check", action="store_true",
                        help="禁用 -checkmetadata，全量重新编译")
    parser.add_argument("--format", type=str, default=DEFAULT_OUTPUT_FORMAT,
                        choices=["png", "svg", "both"],
                        help=f"输出格式（默认: {DEFAULT_OUTPUT_FORMAT}，both 表示同时输出 SVG+PNG）")
    parser.add_argument("--jar", type=str, default=None,
                        help=f"PlantUML JAR 路径（默认: {JAR_PATH}）")
    parser.add_argument("--interval", "-i", type=float, default=2.0,
                        help="监听模式轮询间隔（秒，默认: 2.0）")
    parser.add_argument("--charset", "-c", type=str, default="UTF-8",
                        help="puml 源文件编码（默认: UTF-8）")
    parser.add_argument("--no-pdf", action="store_true",
                        help="跳过 PDF 输出")
    parser.add_argument("--check-encoding", action="store_true",
                        help="检查所有 puml 文件的编码并给出警告")

    args = parser.parse_args()

    # 确定 JAR 路径
    jar = Path(args.jar) if args.jar else JAR_PATH
    if not jar.exists():
        print(f"错误: 找不到 PlantUML JAR: {jar}", file=sys.stderr)
        print("请通过 --jar 指定正确路径，或确认 bin/ 目录下存在 JAR 文件。",
              file=sys.stderr)
        sys.exit(1)

    # 项目根目录：脚本所在目录，或 puml 文件所在目录
    if args.file:
        project_root = Path(args.file).resolve().parent.parent
    else:
        project_root = Path(__file__).parent.resolve()

    check_metadata = not args.no_check
    charset = args.charset.upper()

    # 单文件模式
    if args.file:
        puml_file = Path(args.file)
        if not puml_file.exists():
            print(f"错误: 文件不存在: {puml_file}", file=sys.stderr)
            sys.exit(1)
        print(f"正在编译: {puml_file} -> {args.format} (编码: {charset})")
        success = convert_single(jar, puml_file, check_metadata, charset, args.format, not args.no_pdf)
        if success:
            print("完成。")
        else:
            sys.exit(1)
        return

    # 编码检查模式
    if args.check_encoding:
        puml_files = find_puml_files(project_root)
        if not puml_files:
            print("未找到任何 .puml 文件。")
            return
        check_and_warn_encoding(puml_files)
        return

    # 监听模式
    if args.watch:
        watch_mode(jar, project_root, args.interval, check_metadata, charset, args.format, not args.no_pdf)
        return

    # 默认：编译所有
    puml_files = find_puml_files(project_root)
    if not puml_files:
        print("未找到任何 .puml 文件。")
        return

    print(f"正在编译 {len(puml_files)} 个 PlantUML 文件...")
    print(f"输出格式: {args.format}")
    print(f"使用编码: {charset}")

    # 可选：先检查编码（非侵入式）
    check_and_warn_encoding(puml_files)

    success, total = convert_all(jar, puml_files, check_metadata, charset, args.format, not args.no_pdf)
    print(f"完成: {success}/{total} 个文件编译成功。")

    if success < total:
        sys.exit(1)


if __name__ == "__main__":
    main()

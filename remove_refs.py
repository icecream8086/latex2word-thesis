#!/usr/bin/env python3
"""
remove_refs.py - Pandoc JSON 过滤器，移除 citeproc 生成的参考文献列表

用法:
  python remove_refs.py < input.json > output.json
  python remove_refs.py input.json          # 覆盖源文件
  python remove_refs.py input.json output.json
"""

import sys
import json
import os
import io

# 强制 stdout 使用 UTF-8 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)


def remove_refs(inpath=None, outpath=None):
    """从 pandoc JSON 中移除 citeproc 生成的参考文献列表"""

    # 读取输入
    if inpath:
        with open(inpath, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
    else:
        input_data = sys.stdin.buffer.read()
        try:
            text = input_data.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = input_data.decode('utf-8')
        data = json.loads(text)

    def filter_blocks(blocks):
        """递归过滤块，移除 identifier 为 'refs' 的 Div"""
        filtered = []
        for block in blocks:
            if block.get('t') == 'Div':
                if len(block.get('c', [])) >= 1:
                    identifier_info = block['c'][0]
                    if isinstance(identifier_info, list) and len(identifier_info) > 0:
                        identifier = identifier_info[0]
                    else:
                        identifier = identifier_info
                    if identifier == 'refs':
                        continue
            filtered.append(block)
        return filtered

    if 'blocks' in data:
        data['blocks'] = filter_blocks(data['blocks'])

    json_str = json.dumps(data, ensure_ascii=False)

    if outpath:
        with open(outpath, 'w', encoding='utf-8') as f:
            f.write(json_str)
    else:
        sys.stdout.write(json_str)
        sys.stdout.write('\n')

    print("DEBUG: remove_refs.py 执行完成", file=sys.stderr)


if __name__ == '__main__':
    argc = len(sys.argv)
    if argc >= 3:
        remove_refs(sys.argv[1], sys.argv[2])
    elif argc == 2:
        # 原地修改
        inpath = sys.argv[1]
        outpath = inpath + '.tmp'
        remove_refs(inpath, outpath)
        os.replace(outpath, inpath)
    else:
        remove_refs()

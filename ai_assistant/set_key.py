#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 API Key（默认 ZHIPU_API_KEY，可传 DASHSCOPE_API_KEY）写入服务器的 env 配置文件。
Key 从 stdin 读取（不经过命令行参数，避免出现在进程列表/历史记录），
写入后权限锁定为 600（仅 root 可读）。

用法（在服务器或通过 deploy_assistant.sh 调用）：
    printf '%s' 'sk-xxx' | python3 set_key.py /etc/aitoollab/ai-assistant.env
    printf '%s' 'sk-xxx' | python3 set_key.py /etc/aitoollab/ai-assistant.env DASHSCOPE_API_KEY
"""

from __future__ import print_function
import io
import os
import re
import sys


def main():
    if len(sys.argv) < 2:
        print('usage: set_key.py <env_file> [KEY_NAME]', file=sys.stderr)
        return 1
    path = sys.argv[1]
    key_name = sys.argv[2] if len(sys.argv) > 2 else 'ZHIPU_API_KEY'
    if not re.fullmatch(r'[A-Za-z0-9_]+', key_name):
        print('错误：KEY_NAME 非法，仅支持字母/数字/下划线', file=sys.stderr)
        return 1
    key = sys.stdin.read().strip()
    if not key:
        print('错误：stdin 未读到 Key', file=sys.stderr)
        return 1
    # 严格校验：只允许 ASCII 字母/数字/常见连接符，杜绝空格、中文等误粘贴内容
    if len(key) < 10 or len(key) > 200:
        print('错误：Key 长度异常（%d 字符），请检查是否粘贴了多余内容' % len(key), file=sys.stderr)
        return 1
    for ch in key:
        o = ord(ch)
        if not (48 <= o <= 57 or 65 <= o <= 90 or 97 <= o <= 122 or ch in '._-'):
            print('错误：Key 包含非法字符 %r（第 %d 位），请只粘贴 Key 本身，不要带空格或其他文字' % (ch, key.index(ch) + 1), file=sys.stderr)
            return 1

    lines = []
    try:
        with io.open(path, 'r', encoding='utf-8') as fh:
            lines = fh.readlines()
    except OSError:
        pass

    found = False
    for i, ln in enumerate(lines):
        if ln.strip().startswith(key_name):
            lines[i] = key_name + '=' + key + '\n'
            found = True
            break
    if not found:
        lines.append(key_name + '=' + key + '\n')

    with io.open(path, 'w', encoding='utf-8') as fh:
        fh.writelines(lines)
    os.chmod(path, 0o600)
    print('OK: %s 已写入 %s（权限 600）' % (key_name, path))
    return 0


if __name__ == '__main__':
    sys.exit(main())

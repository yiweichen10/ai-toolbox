#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把钉钉群机器人 Webhook（可选：加签密钥）写入服务器 env 配置。
内容从 stdin 读取（不经过命令行参数，避免出现在进程列表/历史记录），
写入后权限锁定为 600（仅 root 可读）。

用法：
    printf '%s' 'https://oapi.dingtalk.com/robot/send?access_token=xxx' \
      | python3 set_alert_key.py /etc/aitoollab/health-alert.env

    如需加签模式（创建机器人时勾选"加签"），stdin 第二行为密钥：
    printf '%s\n%s' 'https://oapi.dingtalk.com/robot/send?access_token=xxx' 'SECxxx' \
      | python3 set_alert_key.py /etc/aitoollab/health-alert.env
"""

from __future__ import print_function
import io
import os
import sys


def main():
    if len(sys.argv) < 2:
        print('usage: set_alert_key.py <env_file>', file=sys.stderr)
        return 1
    path = sys.argv[1]
    lines = [ln.strip() for ln in sys.stdin.read().splitlines() if ln.strip()]
    if not lines:
        print('错误：stdin 未读到 Webhook', file=sys.stderr)
        return 1
    webhook = lines[0]
    secret = lines[1] if len(lines) > 1 else ''

    if not webhook.startswith('https://oapi.dingtalk.com/robot/send?') or 'access_token=' not in webhook:
        print('错误：Webhook 格式不正确，应为 https://oapi.dingtalk.com/robot/send?access_token=xxx', file=sys.stderr)
        return 1
    for ch in webhook:
        o = ord(ch)
        if o < 33 or o > 126:
            print('错误：Webhook 含空格或非 ASCII 字符，请只粘贴链接本身', file=sys.stderr)
            return 1
    if secret and (len(secret) > 200 or any(ord(c) < 33 or ord(c) > 126 for c in secret)):
        print('错误：加签密钥格式不正确', file=sys.stderr)
        return 1

    old = {}
    try:
        with io.open(path, 'r', encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    k, _, v = line.partition('=')
                    old[k.strip()] = v.strip()
    except OSError:
        pass

    old['DINGTALK_WEBHOOK'] = webhook
    if secret:
        old['DINGTALK_SECRET'] = secret
    elif 'DINGTALK_SECRET' in old:
        # 未提供第二行则保留原密钥；如需清除请单独编辑配置文件
        pass

    with io.open(path, 'w', encoding='utf-8') as fh:
        for k, v in old.items():
            fh.write('%s=%s\n' % (k, v))
    os.chmod(path, 0o600)
    print('OK: 钉钉 Webhook 已写入 %s（权限 600）%s' % (
        path, '，已配置加签密钥' if secret else '，未配置加签密钥'))
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一次性补推脚本：将 sitemap.xml 中所有 URL 用【正确】参数重新推送给百度。

背景：旧版 build.py 推送时 site 参数带了 https:// 前缀，导致百度 token 校验全部失败，
百度从未成功收录。本脚本修正 site 为纯域名后全量补推。

用法: python repush_baidu.py
依赖: 仅标准库（不依赖 dotenv，自己解析 .env）
"""
import os
import sys
import re
import json
import urllib.request
import urllib.error

BASE = os.path.dirname(os.path.abspath(__file__))


def read_env(path):
    env = {}
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def main():
    env = read_env(os.path.join(BASE, '.env'))
    site_domain = env.get('SITE_DOMAIN', 'https://www.aitoollab.cn')
    token = env.get('BAIDU_PUSH_TOKEN', '')
    if not token:
        print('[错误] .env 未配置 BAIDU_PUSH_TOKEN，退出')
        sys.exit(1)

    # 关键：site 必须是纯域名
    baidu_site = site_domain.replace('https://', '').replace('http://', '').rstrip('/')

    sm_path = os.path.join(BASE, 'sitemap.xml')
    if not os.path.exists(sm_path):
        print(f'[错误] 找不到 {sm_path}，请先运行 build.py 生成 sitemap')
        sys.exit(1)

    with open(sm_path, 'r', encoding='utf-8') as f:
        sm = f.read()
    urls = re.findall(r'<loc>(.*?)</loc>', sm)
    print(f'[信息] 从 sitemap 提取 {len(urls)} 个 URL，目标 site={baidu_site}')

    api = f"http://data.zz.baidu.com/urls?site={baidu_site}&token={token}"
    batch_size = 500
    total_success = 0
    for i in range(0, len(urls), batch_size):
        chunk = urls[i:i + batch_size]
        data = '\n'.join(chunk).encode('utf-8')
        req = urllib.request.Request(api, data=data, headers={'Content-Type': 'text/plain'})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = resp.read().decode('utf-8')
                print(f'[batch {i // batch_size + 1}] {result}')
                try:
                    rj = json.loads(result)
                    total_success += rj.get('success', 0)
                    if rj.get('remain', 1) == 0 or rj.get('success', 0) == 0:
                        print('[警告] 当日普通收录配额耗尽(remain=0)，停止推送。'
                              '剩余 URL 请次日再跑本脚本，或去百度站长平台申请「快速收录」提升配额。')
                        break
                except Exception:
                    total_success += len(chunk)
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            print(f'[HTTP {e.code}] {body}')
            print('[提示] 若报错 site error / token error，请检查百度站长平台的站点验证域名与 token 是否匹配。')
            break
        except Exception as e:
            print(f'[异常] {e}')
            break

    print(f'[完成] 本次成功推送给百度 {total_success} 条 URL')


if __name__ == '__main__':
    main()

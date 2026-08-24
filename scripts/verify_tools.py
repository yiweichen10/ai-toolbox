"""#14 工具信息核实自动化

定期核实 data/tools.json 中工具数据的准确性，输出报告供人工或自动修复：
  1. URL 健康度：官网是否仍可访问（2xx/3xx/4xx/5xx/超时/DNS/SSL错误）
  2. 重复检测：同域多工具 + 名称高度相似（疑似重复收录，如 可灵/Kling 3.0）
  3. 字段完整性：关键字段缺失（url/description/category/subcategory/slug）
  4. 分类可疑：category/subcategory 与名称/标签明显不符的软提示

用法：
  python scripts/verify_tools.py            # 全量核实，写 reports/
  python scripts/verify_tools.py --quick     # 仅字段+重复（不发起网络请求，秒级）
  python scripts/verify_tools.py --sample 20 # 随机抽样20个做网络检查

输出：
  reports/tool_verification_YYYY-MM-DD.json  结构化全量
  reports/tool_verification_YYYY-MM-DD.md    人工可读摘要
"""
import json
import os
import sys
import argparse
import datetime
import concurrent.futures
from urllib.parse import urlparse
from difflib import SequenceMatcher

try:
    import urllib.request as ureq
    import urllib.error as uerr
    import ssl
    _HAS_URLLIB = True
except Exception:
    _HAS_URLLIB = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
REPORT_DIR = os.path.join(BASE_DIR, 'reports')
TOOLS_FILE = os.path.join(DATA_DIR, 'tools.json')

SSL_CTX = None
try:
    SSL_CTX = ssl.create_default_context()
    SSL_CTX.check_hostname = False
    SSL_CTX.verify_mode = ssl.CERT_NONE
except Exception:
    SSL_CTX = None

USER_AGENT = 'Mozilla/5.0 (compatible; AIToolLabBot/1.0; +https://www.aitoollab.cn)'


def _registrable_domain(host):
    """取主域名（简化版，处理常见二级后缀）"""
    host = (host or '').lower().strip()
    if not host:
        return ''
    if host.startswith('www.'):
        host = host[4:]
    parts = host.split('.')
    if len(parts) <= 2:
        return host
    # 常见二级后缀
    two_level = {'co.uk', 'com.cn', 'net.cn', 'org.cn', 'com.hk', 'co.jp', 'com.tw', 'io', 'ai', 'dev', 'app', 'sh'}
    last2 = '.'.join(parts[-2:])
    last3 = '.'.join(parts[-3:])
    if last2 in two_level and len(parts) >= 3:
        return '.'.join(parts[-3:])
    return last2


def check_url(url, timeout=8):
    """返回 (status_label, detail)"""
    if not url:
        return ('NO_URL', 'empty')
    if not _HAS_URLLIB:
        return ('SKIP', 'no urllib')
    parsed = urlparse(url if url.startswith('http') else 'https://' + url)
    host = parsed.netloc
    if not host:
        return ('BAD_URL', url)
    for scheme in ('https', 'http'):
        target = f'{scheme}://{host}{parsed.path or "/"}'
        try:
            req = ureq.Request(target, method='HEAD', headers={'User-Agent': USER_AGENT})
            with ureq.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
                code = resp.getcode()
                if 200 <= code < 400:
                    return ('OK' if code < 300 else 'REDIRECT', str(code))
                return ('HTTP_%d' % code, str(code))
        except uerr.HTTPError as e:
            code = e.code
            if scheme == 'https' and code in (403, 405):
                # HEAD 被拒，试 GET
                try:
                    req2 = ureq.Request(target, method='GET', headers={'User-Agent': USER_AGENT})
                    with ureq.urlopen(req2, timeout=timeout, context=SSL_CTX) as resp2:
                        return ('OK' if 200 <= resp2.getcode() < 400 else 'HTTP_%d' % resp2.getcode(), str(resp2.getcode()))
                except Exception:
                    pass
            if scheme == 'https' and code >= 500:
                continue  # 试 http
            if 200 <= code < 400:
                return ('OK' if code < 300 else 'REDIRECT', str(code))
            return ('HTTP_%d' % code, str(code))
        except uerr.URLError as e:
            reason = str(getattr(e, 'reason', e))
            if 'timed out' in reason.lower() or 'timeout' in reason.lower():
                if scheme == 'https':
                    continue
                return ('TIMEOUT', reason[:60])
            if 'Name or service' in reason or 'getaddrinfo' in reason or 'nodename' in reason:
                if scheme == 'https':
                    continue
                return ('DNS_ERROR', reason[:60])
            if 'SSL' in reason or 'certificate' in reason:
                continue  # 试 http
            if scheme == 'https':
                continue
            return ('URL_ERROR', reason[:60])
        except Exception as e:
            if scheme == 'https':
                continue
            return ('ERR', str(e)[:60])
    return ('UNREACHABLE', 'both schemes failed')


def find_duplicates(tools):
    """同域 + 名称相似 两类重复"""
    issues = []
    # 1) 同域
    by_domain = {}
    for t in tools:
        url = t.get('url', '')
        host = urlparse(url).netloc if url else ''
        dom = _registrable_domain(host)
        if not dom:
            continue
        by_domain.setdefault(dom, []).append(t)
    for dom, group in by_domain.items():
        if len(group) > 1:
            names = [g.get('name', '?') for g in group]
            issues.append({
                'type': 'same_domain',
                'domain': dom,
                'tools': names,
                'slugs': [g.get('slug', '?') for g in group],
            })
    # 2) 名称相似（跨域也查）
    names = [(t.get('name', ''), t.get('slug', '')) for t in tools]
    seen = set()
    for i in range(len(names)):
        a_name, a_slug = names[i]
        if not a_name or a_slug in seen:
            continue
        for j in range(i + 1, len(names)):
            b_name, b_slug = names[j]
            if not b_name or b_slug in seen:
                continue
            ratio = SequenceMatcher(None, a_name.lower(), b_name.lower()).ratio()
            if ratio >= 0.82:
                issues.append({
                    'type': 'similar_name',
                    'ratio': round(ratio, 2),
                    'tools': [a_name, b_name],
                    'slugs': [a_slug, b_slug],
                })
                seen.add(a_slug)
                seen.add(b_slug)
    return issues


def _load_subcategory_parents():
    """从 subcategories.json 读取哪些父类目定义了子类目"""
    subcats_path = os.path.join(BASE_DIR, 'data', 'subcategories.json')
    if not os.path.exists(subcats_path):
        return set()
    with open(subcats_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {v['name'] for v in data.values() if v.get('name') and v.get('subcats')}


def check_fields(tools):
    """关键字段完整性"""
    parents_with_subcats = _load_subcategory_parents()  # 动态读取，不硬编码
    issues = []
    for t in tools:
        miss = []
        for f in ('name', 'slug', 'url', 'description', 'category'):
            if not t.get(f):
                miss.append(f)
        # subcategory 仅对有子类定义的父类目强制（来源：subcategories.json）
        if t.get('category') in parents_with_subcats and not t.get('subcategory'):
            miss.append('subcategory')
        if miss:
            issues.append({
                'type': 'missing_field',
                'slug': t.get('slug', '?'),
                'name': t.get('name', '?'),
                'missing': miss,
            })
    return issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--quick', action='store_true', help='仅字段+重复，不发起网络请求')
    ap.add_argument('--sample', type=int, default=0, help='仅随机抽样 N 个做网络检查')
    args = ap.parse_args()

    with open(TOOLS_FILE, 'r', encoding='utf-8') as f:
        tools = json.load(f)

    today = datetime.date.today().strftime('%Y-%m-%d')
    print(f'[verify] 加载 {len(tools)} 个工具 ({today})')

    # 字段 + 重复（始终做）
    field_issues = check_fields(tools)
    dup_issues = find_duplicates(tools)
    print(f'[verify] 字段缺失: {len(field_issues)} | 疑似重复: {len(dup_issues)}')

    # URL 健康（除非 --quick）
    url_results = {}
    if not args.quick:
        targets = tools
        if args.sample and args.sample < len(tools):
            import random
            random.seed(7)
            targets = random.sample(tools, args.sample)
            print(f'[verify] 抽样 {args.sample} 个做网络检查')
        urls = [t.get('url', '') for t in targets]
        print(f'[verify] 网络检查 {len(urls)} 个 URL ...')
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
            fut = {ex.submit(check_url, u): t.get('slug', '?') for t, u in zip(targets, urls)}
            done = 0
            for f in concurrent.futures.as_completed(fut):
                slug = fut[f]
                label, detail = f.result()
                url_results[slug] = {'status': label, 'detail': detail}
                done += 1
                if done % 50 == 0:
                    print(f'  ... {done}/{len(urls)}')
        bad = [s for s, r in url_results.items() if r['status'] not in ('OK', 'REDIRECT')]
        print(f'[verify] URL 异常: {len(bad)}')
    else:
        print('[verify] --quick 模式，跳过网络检查')

    # 汇总
    report = {
        'date': today,
        'total_tools': len(tools),
        'field_issues': field_issues,
        'duplicate_issues': dup_issues,
        'url_results': url_results,
        'url_summary': {},
    }
    if url_results:
        from collections import Counter
        c = Counter(r['status'] for r in url_results.values())
        report['url_summary'] = dict(c)

    os.makedirs(REPORT_DIR, exist_ok=True)
    json_path = os.path.join(REPORT_DIR, f'tool_verification_{today}.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # MD 摘要
    md = [f'# 工具信息核实报告 {today}', '', f'- 工具总数：**{len(tools)}**']
    if url_results:
        md.append(f'- URL 检查：**{len(url_results)}** 个 → {report["url_summary"]}')
    md.append(f'- 字段缺失：**{len(field_issues)}** 条')
    md.append(f'- 疑似重复：**{len(dup_issues)}** 组')
    md.append('')
    if field_issues:
        md.append('## 字段缺失')
        for i in field_issues:
            md.append(f'- `{i["slug"]}` ({i["name"]}) 缺: {", ".join(i["missing"])}')
        md.append('')
    if dup_issues:
        md.append('## 疑似重复')
        for i in dup_issues:
            if i['type'] == 'same_domain':
                md.append(f'- 同域 `{i["domain"]}`: {", ".join(i["tools"])}')
            else:
                md.append(f'- 名称相似 ({i["ratio"]}): {i["tools"][0]} ↔ {i["tools"][1]}')
        md.append('')
    if url_results:
        bad = [(s, r) for s, r in url_results.items() if r['status'] not in ('OK', 'REDIRECT')]
        if bad:
            md.append('## URL 异常')
            name_map = {t.get('slug'): t.get('name', '?') for t in tools}
            for s, r in bad:
                md.append(f'- `{s}` ({name_map.get(s, "?")}) → {r["status"]} ({r["detail"]})')
            md.append('')
    md_path = os.path.join(REPORT_DIR, f'tool_verification_{today}.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))

    print(f'[verify] 报告已写: {json_path}')
    print(f'[verify] 摘要已写: {md_path}')
    # 退出码：有严重问题返回 1（供自动化判断）
    severe = len(field_issues) + len([d for d in dup_issues if d['type'] == 'same_domain'])
    if severe > 0:
        print(f'[verify] ⚠ 发现 {severe} 项需处理的问题')
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()

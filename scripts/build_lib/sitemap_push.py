# sitemap_push.py — sitemap 生成 + IndexNow/Baidu 推送
# 模块11：从 build.py 拆分（2026-08-24）
import os
import re
import json
from datetime import datetime

from build_lib.html_utils import (_collapse_blank_lines,)
from build_lib.render_category import (get_subcat_def,)


def generate_sitemap(tools, articles, categories, compares=None, alternatives=None, quizzes=None, rankings=None, lives=None, dict_terms=None, news_urls=None):
    import build  # 延迟：build 完全加载后解析
    """生成 sitemap.xml"""
    from datetime import datetime, timedelta
    import re as _re_sm
    today = datetime.now().strftime('%Y-%m-%d')

    def _tool_lastmod(tool):
        v = tool.get('dateModified', tool.get('date_modified', tool.get('last_updated', '')))
        if v:
            return str(v)[:10]
        if tool.get('created_date'):
            try:
                cd = datetime.strptime(str(tool['created_date'])[:10], '%Y-%m-%d')
                return cd.strftime('%Y-%m-%d')
            except Exception:
                pass
        return today

    def _article_lastmod(article):
        d = article.get('dateModified', article.get('dateFull', article.get('date', '')))
        m = _re_sm.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', str(d))
        if m:
            return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
        m2 = _re_sm.match(r'^(\d{4}-\d{2}-\d{2})', str(d))
        return m2.group(1) if m2 else today

    urls = []

    # 首页
    urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>''')

    # 全部AI工具大全页 /tools/（SEO+GEO 总入口）
    urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/tools/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.9</priority>
    </url>''')

    # 注意：不在sitemap中加入文章分页URL（/articles/page/N/），避免浪费爬虫预算
    # 分页通过页面上的 rel=next/prev 让爬虫自然发现即可

    # 工具页
    for tool in tools:
        priority = '0.9' if tool.get('badge') else '0.8'
        urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/tools/{tool['slug']}/</loc>
        <lastmod>{_tool_lastmod(tool)}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>{priority}</priority>
        </url>''')

    # 文章页
    for article in articles:
        priority = '0.9' if '2026' in article.get('title', '') else '0.8'
        urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/articles/{article['slug']}/</loc>
        <lastmod>{_article_lastmod(article)}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>{priority}</priority>
    </url>''')

    # 文章内容分类页（2026-08-08：评测/教程/分析 3 个分类枢纽页）
    for _cp in build.ARTICLE_CATEGORY_PAGES:
        urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/articles/{_cp['slug']}/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>''')
    
    # 分类枢纽页 /category/（SEO+GEO 2026-08-03：此前遗漏，导致枢纽页仅靠全局导航被发现）
    urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/category/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.9</priority>
    </url>''')

    # 各栏目总入口页（2026-08-13：Bing 报"网站地图中缺少重要页面"，补齐枢纽页）
    # 2026-08-17：补上 /news/ 枢纽页（快讯为站内最大流量板块，check_closed_loop 门禁要求）
    # 2026-08-23 修复：补 /quiz/ 与 /dict/ 枢纽页——check_closed_loop 门禁
    # 要求 hubs 含这两项，但此处遗漏导致 sitemap 缺 loc，门禁 FAIL 阻断部署。
    for _hub, _prio in (("/ranking/", "0.9"), ("/compare/", "0.8"), ("/alternatives/", "0.8"),
                        ("/articles/", "0.8"), ("/author/", "0.6"), ("/live/", "0.7"),
                        ("/news/", "0.9"), ("/quiz/", "0.8"), ("/dict/", "0.8")):
        urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn{_hub}</loc>
        <lastmod>{today}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>{_prio}</priority>
    </url>''')

    # 分类页（categories 参数已经是经过 get_category_slug 处理的 slug 列表）
    for category_name in categories:
        urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/category/{category_name}/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>''')

    # 子类目页（独立SEO入口）
    _subdef = get_subcat_def()
    for _parent_slug, _pdata in _subdef.items():
        for _sub_slug, _sdata in _pdata.get('subcats', {}).items():
            urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/category/{_sub_slug}/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.7</priority>
    </url>''')

    # 对比页 (Phase 2)
    if compares:
        for cp in compares:
            cslug = cp.get('slug', '')
            if cslug:
                prio = '0.9' if cp.get('priority') == 'high' else '0.8'
                urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/compare/{cslug}/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>{prio}</priority>
    </url>''')

    # 替代方案页 (Phase 3)
    if alternatives:
        for alt in alternatives:
            aslug = alt.get('slug', '')
            if aslug:
                urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/alternatives/{aslug}/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.8</priority>
    </url>''')

    # Quiz 选择器页 (Phase 4)
    if quizzes:
        for qd in quizzes:
            qslug = qd.get('slug', '')
            if qslug:
                is_main = (qd.get('target_url') == '/quiz/') or qslug == 'ai-tool-finder-2026'
                loc = f'/' if is_main else f'/{qslug}/'
                urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/quiz{loc}</loc>
        <lastmod>{today}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.9</priority>
    </url>''')

    # Ranking 排名页 (Phase 5)
    if rankings:
        for rd in rankings:
            rslug = rd.get('slug', '')
            if rslug:
                urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/ranking/{rslug}/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.9</priority>
    </url>''')

    # Live Dashboard 页 (Phase 5b)
    if lives:
        for lp in lives:
            lslug = lp.get('slug', '')
            if lslug:
                urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/live/{lslug}/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.9</priority>
    </url>''')

    # AI词典页
    if dict_terms:
        urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/dict/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>''')
        for term in dict_terms:
            urls.append(f'''    <url>
        <loc>https://www.aitoollab.cn/dict/{term['slug']}/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.7</priority>
    </url>''')

    # 快讯页（每日更新，changefreq=daily）
    if news_urls:
        for nu in news_urls:
            urls.append(f'''    <url>
        <loc>{nu}</loc>
        <lastmod>{today}</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.6</priority>
    </url>''')

    sitemap = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>'''

    return sitemap

def _urlopen_bounded(req, timeout, label="request"):
    import build  # 延迟：build 完全加载后解析
    """urlopen with a HARD wall-clock timeout that ALSO covers DNS resolution.

    urllib.request.urlopen(req, timeout=N) 的 timeout 只约束「建连/读取」阶段，
    不约束 DNS 解析(getaddrinfo)。在 VPN/沙箱网络中，若 api.indexnow.org 等
    外部域名 DNS 丢包且无 RST，getaddrinfo 会无限阻塞，N 秒形同虚设，导致
    build.py / publish 流水线卡死。用 daemon 线程 + join(timeout) 把整个
    操作(含 DNS)硬上限到 timeout+2 秒，超时即放弃，绝不阻塞构建。
    """
    import threading
    import urllib.request
    box = {}
    def _run():
        try:
            box['resp'] = urllib.request.urlopen(req, timeout=timeout)
        except Exception as e:
            box['err'] = e
    th = threading.Thread(target=_run, daemon=True)
    th.start()
    th.join(timeout + 2)  # 墙钟硬上限，覆盖 DNS 挂死
    if th.is_alive():
        print(f"[{label}] Timeout (incl. DNS), skipped to avoid blocking build.")
        return None
    if 'err' in box:
        raise box['err']
    return box['resp']

def push_to_indexnow(urls):
    import build  # 延迟：build 完全加载后解析
    """通过 IndexNow 协议向 Bing/Yandex 等搜索引擎推送新链接"""
    import urllib.request
    import urllib.error
    import json as _json

    KEY = build.INDEXNOW_KEY
    api_url = "https://api.indexnow.org/indexnow"

    payload = _json.dumps({
        "host": "www.aitoollab.cn",
        "key": KEY,
        "keyLocation": f"https://www.aitoollab.cn/{KEY}.txt",
        "urlList": urls[:10000]  # IndexNow 单次上限 10000 条
    }).encode("utf-8")

    req = urllib.request.Request(
        api_url,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST"
    )
    try:
        resp = _urlopen_bounded(req, 15, "IndexNow")
        if resp is None:
            return False
        with resp:
            print(f"[IndexNow] Success: HTTP {resp.status}, pushed {len(urls)} URLs")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[IndexNow] HTTP {e.code}: {body}")
        return False
    except Exception as e:
        print(f"[IndexNow] Failed: {e}")
        return False

def push_to_baidu(urls):
    import build  # 延迟：build 完全加载后解析
    """主动向百度搜索引擎推送链接

    修复1: site参数必须是纯域名(www.aitoollab.cn)，不能带 http(s)://，否则百度token校验失败、推送全部无效。
    修复2: 百度返回 success/remain 字段，当 remain==0 时说明当日配额耗尽，必须 return False 不更新缓存，
           否则未收录的URL会被误标记为已推送、永不重推。分批推送避免一次性砸光配额。
    """
    if not build.BAIDU_PUSH_TOKEN:
        print("[Baidu Push] 跳过: 未配置 build.BAIDU_PUSH_TOKEN")
        return False
    # 关键修复：剥离协议头，得到纯域名
    baidu_site = build.SITE_DOMAIN.replace('https://', '').replace('http://', '').rstrip('/')
    api_url = f"http://data.zz.baidu.com/urls?site={baidu_site}&token={build.BAIDU_PUSH_TOKEN}"

    try:
        import urllib.request
        import urllib.error
        import json as _json
        batch_size = 500
        total_success = 0
        for i in range(0, len(urls), batch_size):
            chunk = urls[i:i + batch_size]
            data = '\n'.join(chunk).encode('utf-8')
            req = urllib.request.Request(api_url, data=data, headers={'Content-Type': 'text/plain'})
            try:
                response = _urlopen_bounded(req, 15, "Baidu Push")
                if response is None:
                    return False
                with response:
                    result = response.read().decode('utf-8')
                    print(f"[Baidu Push] batch {i // batch_size + 1} Success: {result}")
                    try:
                        rj = _json.loads(result)
                        total_success += rj.get('success', len(chunk))
                        if rj.get('remain', 1) == 0 or rj.get('success', 0) == 0:
                            print("[Baidu Push] 当日配额耗尽(remain=0)，停止推送，剩余URL留待次日重试")
                            return False
                    except Exception:
                        total_success += len(chunk)
            except urllib.error.HTTPError as e:
                body = e.read().decode('utf-8', errors='replace')
                print(f"[Baidu Push] HTTP {e.code}: {body}")
                return False
    except Exception as e:
        print(f"[Baidu Push] Failed: {e}")
        return False
    return total_success > 0

def _push_single_url(url):
    import build  # 延迟：build 完全加载后解析
    """增量构建时推送单个新URL到百度和IndexNow"""
    import urllib.request, urllib.error

    # 百度推送（修复：site参数剥离协议头，必须为纯域名）
    if build.BAIDU_PUSH_TOKEN:
        baidu_site = build.SITE_DOMAIN.replace('https://', '').replace('http://', '').rstrip('/')
        baidu_api = f"http://data.zz.baidu.com/urls?site={baidu_site}&token={build.BAIDU_PUSH_TOKEN}"
    try:
        data = url.encode('utf-8')
        req = urllib.request.Request(baidu_api, data=data, headers={'Content-Type': 'text/plain'})
        resp = _urlopen_bounded(req, 10, "Baidu Push")
        if resp is not None:
            with resp:
                print(f'[Baidu Push] {resp.read().decode("utf-8", errors="replace")}')
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f'[Baidu Push] HTTP {e.code}: {body}')
    except Exception as e:
        print(f'[Baidu Push] Failed: {e}')

    # IndexNow推送
    try:
        indexnow_url = "https://api.indexnow.org/indexnow"
        payload = json.dumps({"host": "www.aitoollab.cn", "key": build.INDEXNOW_KEY, "urlList": [url]}).encode('utf-8')
        req = urllib.request.Request(indexnow_url, data=payload, headers={'Content-Type': 'application/json'})
        resp = _urlopen_bounded(req, 10, "IndexNow")
        if resp is not None:
            with resp:
                print(f'[IndexNow] HTTP {resp.status}, pushed 1 URL')
    except Exception as e:
        print(f'[IndexNow] Failed: {e}')

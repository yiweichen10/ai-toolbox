#!/usr/bin/env python3
"""
URL 可用性检查脚本
功能：
1. 检查 tools.json 中所有工具 URL 的可访问性
2. 区分：真实死链(404) vs 被中国墙(ERR) vs Bot保护(403)
3. 输出问题报告，供人工决策哪些需要修复
4. 用于构建前质检，防止死链上线

用法：
  python scripts/check_url_health.py          # 检查所有
  python scripts/check_url_health.py --fix   # 自动修复已知可修复的问题
"""

import json
import httpx
import asyncio
import argparse
import os
from pathlib import Path

# 从配置文件读取已知问题 URL 映射
# 格式：{"旧URL": "新URL", ...}
# 当检测到旧URL不可用时，提示用户更新
KNOWN_REDIRECTS = {
    "www.phind.com": "phindai.org",
    "phind.com": "phindai.org",
    "tome.app/ai": "tome.app",
    "pitch.com/ai": "pitch.com",
    # 添加更多已知变更...
}

# 已知有 Bot 保护（403）的域名，检查时不报警
KNOWN_BOT_PROTECTED = {
    "www.midjourney.com",
    "www.canva.com",
    "openai.com/sora",
    "openai.com/dall-e-3",
    "openai.com/index/introducing-codex",
    "arc.net",
    "consensus.app",
    "looka.com",
    "www.make.com",
    "lottiefiles.com/ai",
    "kaiber.ai",
    "www.freepik.com",
}

TOOLS_JSON = Path(__file__).parent.parent / "data" / "tools.json"
REPORT_FILE = Path(__file__).parent.parent / "data" / "url_health_report.json"


async def check_url(session: httpx.AsyncClient, name: str, url: str) -> dict:
    """检查单个 URL"""
    result = {"name": name, "url": url, "status": "unknown", "issue": None, "suggestion": None}

    try:
        resp = await session.head(url, timeout=10, follow_redirects=True)
        status = resp.status_code

        if status == 200:
            result["status"] = "ok"
        elif status == 403:
            # 区分Bot保护和真实403
            if any(bot in url for bot in KNOWN_BOT_PROTECTED):
                result["status"] = "bot_protected"
            else:
                result["status"] = "forbidden"
                result["issue"] = "403 Forbidden"
                result["suggestion"] = "域名可能被墙或需要更新，请手动验证"
        elif status == 404:
            result["status"] = "not_found"
            result["issue"] = "404 Not Found"
            result["suggestion"] = "URL已失效，需要更新为正确域名"
        elif status in (500, 502, 503):
            result["status"] = "server_error"
            result["issue"] = f"{status} Server Error"
            result["suggestion"] = "服务器暂时不可用，可稍后重试"
        else:
            result["status"] = f"http_{status}"
            result["issue"] = f"HTTP {status}"

    except httpx.TimeoutException:
        result["status"] = "timeout"
        result["issue"] = "连接超时"
        result["suggestion"] = "可能在中国大陆被墙，需VPN测试"
    except httpx.ConnectError:
        result["status"] = "blocked"
        result["issue"] = "连接被拒绝"
        result["suggestion"] = "域名可能在中国大陆被墙，需VPN测试"
    except Exception as e:
        result["status"] = "error"
        result["issue"] = str(e)[:100]

    return result


async def check_all_urls(concurrency: int = 10) -> list[dict]:
    """并发检查所有工具 URL"""
    tools = json.load(open(TOOLS_JSON, encoding="utf-8"))
    urls = [(t["name"], t.get("url", "")) for t in tools if t.get("url")]

    results = []
    semaphore = asyncio.Semaphore(concurrency)

    async def bounded_check(name, url):
        async with semaphore:
            return await check_url(httpx.AsyncClient(), name, url)

    tasks = [bounded_check(name, url) for name, url in urls]
    for coro in asyncio.as_completed(tasks):
        results.append(await coro)

    return results


def fix_url(name: str, old_url: str, new_url: str):
    """修复 tools.json 中的 URL"""
    tools = json.load(open(TOOLS_JSON, encoding="utf-8"))
    fixed = []
    for t in tools:
        if t.get("name") == name and t.get("url") == old_url:
            t["url"] = new_url
            fixed.append(name)
            print(f"  [FIXED] {name}: {old_url} -> {new_url}")
        # 同时修复 content 中的旧 URL
        if t.get("content"):
            if old_url in t["content"]:
                t["content"] = t["content"].replace(old_url, new_url)
                fixed.append(f"{name} (content)")
                print(f"  [FIXED] {name} content 中的链接")
    if fixed:
        json.dump(tools, open(TOOLS_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"  Saved: {TOOLS_JSON}")
    return fixed


def generate_report(results: list[dict]) -> dict:
    """生成分类报告"""
    ok = [r for r in results if r["status"] == "ok"]
    bot_protected = [r for r in results if r["status"] == "bot_protected"]
    not_found = [r for r in results if r["status"] == "not_found"]
    forbidden = [r for r in results if r["status"] == "forbidden"]
    blocked = [r for r in results if r["status"] in ("blocked", "timeout")]
    error = [r for r in results if r["status"] in ("server_error", "http_500", "error")]

    return {
        "total": len(results),
        "ok": len(ok),
        "bot_protected": len(bot_protected),
        "not_found": len(not_found),
        "forbidden": len(forbidden),
        "blocked_china": len(blocked),
        "errors": len(error),
        "not_found_tools": [{"name": r["name"], "url": r["url"], "suggestion": r["suggestion"]} for r in not_found],
        "forbidden_tools": [{"name": r["name"], "url": r["url"], "suggestion": r["suggestion"]} for r in forbidden],
        "blocked_tools": [{"name": r["name"], "url": r["url"]} for r in blocked],
    }


async def main():
    parser = argparse.ArgumentParser(description="检查工具 URL 健康状态")
    parser.add_argument("--fix", action="store_true", help="自动修复已知可修复的问题")
    args = parser.parse_args()

    print("正在检查 URL 可用性...")
    results = await check_all_urls()
    report = generate_report(results)

    # 保存报告
    json.dump(report, open(REPORT_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"报告已保存: {REPORT_FILE}")

    # 打印汇总
    print("\n=== URL 健康检查报告 ===")
    print(f"总计: {report['total']} 个工具")
    print(f"✅ 正常: {report['ok']}")
    print(f"🤖 Bot保护(无影响): {report['bot_protected']}")
    print(f"🔴 404死链(需修复): {report['not_found']}")
    print(f"🟡 403/错误(需人工): {report['forbidden'] + report['errors']}")
    print(f"🌏 中国墙(国内访问): {report['blocked_china']}")

    if report["not_found_tools"]:
        print("\n⚠️ 需要修复的 404 死链:")
        for t in report["not_found_tools"]:
            print(f"  - {t['name']}: {t['url']}")

    if report["forbidden_tools"]:
        print("\n⚠️ 需要人工确认的 403:")
        for t in report["forbidden_tools"]:
            print(f"  - {t['name']}: {t['url']} ({t['suggestion']})")

    if report["blocked_tools"]:
        print(f"\n🌏 国内被墙的站点（共{report['blocked_china']}个，通常无需修复）:")
        for t in report["blocked_tools"][:10]:
            print(f"  - {t['name']}: {t['url']}")
        if len(report["blocked_tools"]) > 10:
            print(f"  ... 及其他 {report['blocked_china'] - 10} 个")

    # 自动修复
    if args.fix and report["not_found_tools"]:
        print("\n=== 开始自动修复 ===")
        fixed_total = 0
        for t in report["not_found_tools"]:
            # 检查是否是已知重定向
            for old, new in KNOWN_REDIRECTS.items():
                if old in t["url"]:
                    fix_url(t["name"], t["url"], t["url"].replace(old, new))
                    fixed_total += 1
                    break
        print(f"\n自动修复完成: {fixed_total} 个")

    return report


if __name__ == "__main__":
    asyncio.run(main())

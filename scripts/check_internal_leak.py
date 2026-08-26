# -*- coding: utf-8 -*-
"""内部信息泄漏扫描：检查 tools.json 所有工具的对外可见字段是否含内部痕迹。
对外字段：description / content / features / pros / cons / faq / tags / url
内部痕迹：收录来源、ai-bot.cn（、官网：https（content内）、utm_source=ai-bot 追踪参数、
         verify_notes 内部备注、内部字段名等。
用法：python scripts/check_internal_leak.py   # 有违规 exit 1，构建前可拦截
（2026-08-05 新增：入库模板曾把溯源写进 content 导致泄漏，改为机制扫描防再犯）

退出码约定（2026-08-06 修复，供 build.py 区分处理）：
  0 = 对外字段干净，放行
  1 = 检测到真实泄漏，必须拦截构建
  2 = 检查器自身故障（文件缺失/JSON 损坏等），打印警告但不应卡死流水线

（2026-08-06 修复：TOOLS_JSON 原为相对路径 "data/tools.json"，仅在 cwd=seo-site 根时可用。
  publish_new_tools.py 以 cwd=scripts 调用 build.py 时守卫脚本 FileNotFoundError 崩溃，
  returncode=1 被 build.py 误判为"检测到泄漏"→ 每日发布流水线整条中止。改为基于 __file__ 绝对定位。）"""
import json, os, re, sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SITE_ROOT = os.path.dirname(_SCRIPT_DIR)
TOOLS_JSON = os.path.join(_SITE_ROOT, "data", "tools.json")   # 兼容回退; 真源为分片
TOOLS_SHARD_DIR = os.path.join(_SITE_ROOT, "data", "tools")
LEAK_PATTERNS = [
    (r"收录来源", "含'收录来源'"),
    (r"收录自 ai-bot|来源：ai-bot|ai-bot\.cn（|（2026-08），官网已验证", "含 ai-bot 收录/验证溯源"),
    (r"官网：https?://", "含'官网：http'溯源行"),
    (r"utm_source=ai-bot|utm_medium=aitools&utm_source=aibot", "URL 含 ai-bot 追踪参数"),
    (r"verify_notes|verified_[a-z_]+", "对外字段出现内部字段名"),
]

def check():
    try:
        # 2026-08-26 去单体化: 真源为分片 data/tools/*.json, 单体仅回退
        if os.path.isdir(TOOLS_SHARD_DIR):
            import glob
            _all = []
            for _fp in sorted(glob.glob(os.path.join(TOOLS_SHARD_DIR, "*.json"))):
                try:
                    with open(_fp, encoding="utf-8") as _f:
                        _r = json.load(_f)
                    _all.extend(_r if isinstance(_r, list) else [_r])
                except Exception:
                    continue
            d = _all
        else:
            with open(TOOLS_JSON, encoding="utf-8") as f:
                d = json.load(f)
    except Exception as e:
        # 检查器自身故障：不冒充"检测到泄漏"，返回 2 让调用方降级为警告
        print(f"[leak-check][ERROR] 无法读取工具数据: {type(e).__name__}: {e}")
        return 2
    tools = d if isinstance(d, list) else d.get("tools", d.get("data", []))
    violations = []
    for t in tools:
        name = t.get("name", "?")
        slug = t.get("slug", "?")
        url = t.get("url", "") or ""
        fields = {
            "description": str(t.get("description", "") or ""),
            "content": str(t.get("content", "") or ""),
            "features": " ".join(map(str, t.get("features", []) or [])),
            "pros": " ".join(map(str, t.get("pros", []) or [])),
            "cons": " ".join(map(str, t.get("cons", []) or [])),
            "faq": json.dumps(t.get("faq", []) or [], ensure_ascii=False),
            "tags": json.dumps(t.get("tags", []) or [], ensure_ascii=False),
            "url": url,
        }
        for fname, ftext in fields.items():
            for pat, desc in LEAK_PATTERNS:
                if re.search(pat, ftext, re.I):
                    violations.append((slug, name, fname, desc, ftext[:60]))
    if violations:
        print(f"⚠️ 发现 {len(violations)} 处内部信息泄漏：")
        for slug, name, fname, desc, sample in violations:
            print(f"  - {name} ({slug}) [{fname}] {desc}: ...{sample}")
        return 1
    print(f"✅ 无内部信息泄漏（{len(tools)} 个工具对外字段干净）")
    return 0

if __name__ == "__main__":
    sys.exit(check())

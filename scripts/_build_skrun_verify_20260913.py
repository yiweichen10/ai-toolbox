# -*- coding: utf-8 -*-
"""生成 data/_verify_batch_versions_daily.json（2026-09-13 运行：仅 skrun v1.1.0）
依据（官方源，2026-09-12 发布）：
  - https://github.com/skrun-dev/skrun/releases/tag/v1.1.0  (release notes 原文)
  - https://github.com/skrun-dev/skrun/blob/main/README.md  (provider 列表：6 家内置)
  - https://registry.npmjs.org/@skrun-dev/cli                (latest 1.1.0, MIT, 2026-09-12)
  - scripts/scrape_price.py → success=false（GitHub 定价导航，无工具价）→ 价格未变、不动
写后自校验：每条 stale_facts.old 必须逐字命中 data/tools/skrun.json 的 content / faq。
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARD = os.path.join(ROOT, "data", "tools", "skrun.json")
OUT = os.path.join(ROOT, "data", "_verify_batch_versions_daily.json")

DESC = (
    "Skrun 是一个开源的 Agent 运行时（2026 年 4 月 8 日 Show HN 发布，MIT 许可证），由日内瓦开发者 "
    "Ian Bernardo（GitHub 昵称 frizull）与同事 Tarcroi 创建。它的核心洞见是：你在 Claude Code、Copilot、"
    "Codex 里攒的 Agent Skill（SKILL.md）被困在各自工具里，不能被产品用 POST 请求调用；Skrun 把这些技能"
    "变成可调用的 HTTP 端点，让“技能即服务”成为现实。2026-08-30 发布的 v1.0.0「Cloud Runtime & "
    "Production Foundation」将其从早期原型推进到生产可用：内置多租户云运行时、Operator Dashboard 与 "
    "GitHub OAuth / API key 鉴权；2026-09-12 的 v1.1.0「Enforced Limits & Durable Sessions」补齐生产细节——"
    "文档承诺的限流（POST /run 60 次/分、POST /push 10 次/分）真正生效并返回 429 与 X-RateLimit-* 头、"
    "Dashboard 会话改为跨实例共享的 sessions 表（重新部署不再强制登出，有效期 7 天）、`skrun login` "
    "密钥默认 90 天过期、云沙箱在解包前校验 bundle 的 SHA-256。"
)

FEATURES = [
    "SKILL.md → API：一条 init 加 deploy，把技能暴露成 POST /run 端点",
    "多模型 + 自动回退：在 agent.yaml 选 provider（内置 Anthropic / OpenAI / Google / Mistral / Groq / xAI 六家，或任意 OpenAI 兼容端点如 DeepSeek / Kimi / Qwen / Ollama），失败自动切下一个",
    "有状态 Agent：用键值状态在多次运行间持久化上下文",
    "工具调用：可捆绑自有 CLI 脚本，或接入任意 MCP server（如 Playwright）",
    "类型化 I/O：定义结构化输入输出，保证 API 交互可靠",
    "CLI 管理：约 12 个 CLI 命令负责初始化、测试与部署",
    "Cloud Runtime（v1.0.0）：多租户命名空间 + GitHub OAuth / API key 鉴权，共享实例上 push/verify/delete 限定命名空间所有者",
    "Operator Dashboard：/dashboard 提供智能体 / 运行 / 统计看板、SSE 流式 Playground 与 API key 管理；SQLite 默认持久化存储（可选 Supabase）",
    "限流与体积上限真正生效（v1.1.0）：POST /run 60 次/分、POST /push 10 次/分，超限返回 429 并在每个响应带 X-RateLimit-* 头；push 正文超过 50 MB 在读之前直接以 413 拒绝",
    "会话与密钥生命周期（v1.1.0）：Dashboard 会话移入跨实例共享的 sessions 表，重新部署不再把所有人登出且 7 天有效；`skrun login` 密钥默认 90 天过期，每个密钥返回 expires_at",
]

PROS = [
    "把 SKILL.md 变成 API 极简，几分钟拿到可调用端点",
    "多模型支持（内置 Anthropic / OpenAI / Google / Mistral / Groq / xAI 六家，可接任意 OpenAI 兼容端点）+ 自动回退",
    "有状态 Agent：用键值状态在多次运行间记住上下文",
    "可接入 CLI 工具与任意 MCP server 扩展能力",
    "MIT 开源，自托管即可，无供应商锁定",
]

CONS = [
    "生态仍年轻，第三方集成与社区规模还比较小",
    "沙箱隔离需显式开启（SKRUN_RUNTIME=flyio，首个后端依赖 Fly.io）；未开启时公开部署仍存在 prompt injection 等风险",
    "需自托管与运维，调用方要自己管契约与版本",
    "v1.1.0 起限流真正生效（超限 429）、`skrun login` 密钥默认 90 天过期，已有调用链需要自查",
]

STALE_FACTS = [
    {
        "where": "content",
        "old": "托管的商业云定价目前仍未公布，自建多租户运行时本身不收费。",
        "new": (
            "2026-09-12 发布的 **v1.1.0「Enforced Limits & Durable Sessions」** 把生产细节补齐："
            "文档里承诺的限流终于真正生效（POST /run 60 次/分、POST /push 10 次/分，超限返回 429 "
            "RATE_LIMITED 并在每个响应带 X-RateLimit-* 头，push 正文超过 50 MB 直接以 413 拒绝）、"
            "Dashboard 会话从进程内存迁到跨实例共享的 sessions 表（重新部署不再把所有人登出，会话 7 天有效）、"
            "`skrun login` 签发的密钥默认 90 天后过期、云沙箱在解包前校验 bundle 的 SHA-256，"
            "测试规模也从 1836 涨到 1907 项。托管的商业云定价目前仍未公布，自建多租户运行时本身不收费。"
        ),
    },
    {
        "where": "content",
        "old": (
            "v1.0.0 已是稳定版、测试套件达 1800+ 单元与 140 项 E2E，但项目生态仍年轻；"
            "公开部署存在 prompt injection 等安全风险（官方沙箱方案已在规划），"
            "敏感场景建议先留在内网或自托管多租户实例。"
        ),
        "new": (
            "v1.1.0 已是稳定版、测试套件达 1907 项单元与集成加 140 项 E2E，但项目生态仍年轻；"
            "沙箱隔离已随 v1.0.0 落地并可开启（首个后端 Fly.io，设 `SKRUN_RUNTIME=flyio`，出口按网络层允许清单收紧），"
            "v1.1.0 又补上解包前校验 bundle SHA-256；未开启沙箱的公开部署仍存在 prompt injection 等安全风险，"
            "敏感场景建议先留在内网或自托管多租户实例。"
        ),
    },
    {
        "where": "content",
        "old": "多模型 + 自动回退：在 agent.yaml 里选 Anthropic / OpenAI / Google / Mistral / Groq，失败自动切下一个。",
        "new": (
            "多模型 + 自动回退：在 agent.yaml 里选 Anthropic / OpenAI / Google / Mistral / Groq / xAI，"
            "或接任意 OpenAI 兼容端点（DeepSeek、Kimi、Qwen、Ollama、vLLM 等），失败自动切下一个。"
        ),
    },
    {
        "where": "content",
        "old": "避免共享实例上的 `dev-token` 被拒（v1.0.0 的 Breaking 变更）。",
        "new": (
            "避免共享实例上的 `dev-token` 被拒（v1.0.0 的 Breaking 变更），并留意 v1.1.0 起 "
            "`skrun login` 签发的密钥默认 90 天后过期；若调用链里按次覆盖 agent 的 environment，"
            "需改用账户级凭据，否则会被拒绝。"
        ),
    },
    {
        "where": "faq",
        "old": "沙箱隔离方案在规划中，建议敏感场景先留在内网。",
        "new": (
            "沙箱隔离已于 v1.0.0 落地并可开启（设 SKRUN_RUNTIME=flyio，出口按网络层允许清单收紧），"
            "v1.1.0 加固为解包前校验 bundle SHA-256；未开启沙箱时公开部署仍有风险，建议敏感场景先留在内网。"
        ),
    },
    {
        "where": "faq",
        "old": "Skrun 在 agent.yaml 中支持 Anthropic、OpenAI、Google、Mistral、Groq，并可在主模型失败时自动回退到备选 provider。",
        "new": (
            "Skrun 在 agent.yaml 中内置 6 家 provider：Anthropic、OpenAI、Google、Mistral、Groq 与 xAI，"
            "也可接任意 OpenAI 兼容端点（DeepSeek、Kimi、Qwen、Ollama、vLLM 等），"
            "并可在主模型失败时自动回退到备选 provider。"
        ),
    },
]

RESULT = {
    "slug": "skrun",
    "confidence": "high",
    "conflict": False,
    "official_url": "https://github.com/skrun-dev/skrun",
    "verified_description": DESC,
    "core_features": FEATURES,
    "verified_pros": PROS,
    "verified_cons": CONS,
    "stale_facts": STALE_FACTS,
    "source_urls": [
        "https://github.com/skrun-dev/skrun/releases/tag/v1.1.0",
        "https://github.com/skrun-dev/skrun",
        "https://github.com/skrun-dev/skrun/blob/main/README.md",
        "https://registry.npmjs.org/@skrun-dev/cli",
    ],
    "notes": (
        "价格核实：scrape_price.py success=false（跳转 github.com/skrun-dev/skrun/pricing-plans，"
        "命中的是 GitHub 站点通用定价导航，无工具自身价目）→ 按 WebSearch/npm 兜底：npm @skrun-dev/cli@1.1.0 "
        "license=MIT、仓库 license=MIT、v1.1.0 发布说明未提及任何定价变更 → 开源免费不变，"
        "托管商业云定价仍未公布；price / verified_price 均未改动。"
    ),
}


def main():
    with open(SHARD, encoding="utf-8") as f:
        tool = json.load(f)
    content = tool.get("content") or ""
    faq = tool.get("faq") or []
    miss = []
    for item in STALE_FACTS:
        old = item["old"]
        if item["where"].startswith("faq"):
            hit = any(old in (f.get(k) or "") for f in faq for k in ("q", "a", "question", "answer"))
        else:
            hit = old in content
        print(("[HIT ] " if hit else "[MISS] ") + item["where"] + " :: " + old[:42])
        if not hit:
            miss.append(old[:42])
    if miss:
        print("\n未命中 %d 条，禁止写入：" % len(miss))
        for m in miss:
            print("  -", m)
        sys.exit(1)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump([RESULT], f, ensure_ascii=False, indent=2)
    print("\n[OK] 写入 %s（1 条，confidence=high / conflict=false，stale_facts %d/%d 逐字命中）"
          % (OUT, len(STALE_FACTS), len(STALE_FACTS)))
    # 读回校验
    back = json.load(open(OUT, encoding="utf-8"))
    assert back[0]["slug"] == "skrun" and len(back[0]["stale_facts"]) == len(STALE_FACTS)
    print("[OK] 读回校验通过：slug=%s, stale_facts=%d" % (back[0]["slug"], len(back[0]["stale_facts"])))


if __name__ == "__main__":
    main()

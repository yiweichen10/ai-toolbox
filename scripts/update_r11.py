import os as _os  # 2026-08-28 单体退役拦截（AGENTS.md「数据架构：分片即真源，单体已退役」）
if not _os.path.exists(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                                       "data", "tools.json")):
    raise SystemExit("[已停用] 本脚本按已退役的单体 data/tools.json | data/articles.json 读写；"
                     "真源是分片 data/tools/*.json + data/articles/*.json，"
                     "改数据请走 scripts/data_store.py 的 load_all_*/save_* 后再用。")
# --- 单体退役拦截 end ---
import json

PATH = "data/tools.json"

with open(PATH, encoding="utf-8") as f:
    data = json.load(f)

updates = {
    "anyscale": {
        "url": "https://www.anyscale.com/",
        "description": "Anyscale 是由 Ray 开源框架原班团队打造的生产级 AI 计算平台，帮助团队在任意云上构建、运行和扩展数据/AI 工作负载（训练、推理、微调），无需自行管理集群。",
        "features": [
            "基于 Ray 的生产级分布式 AI 计算平台（训练、批推理、在线推理、LLM 微调）",
            "云 IDE 工作区（Workspaces）+ 托管 Ray 集群与自动扩缩容",
            "多云/混合云部署，单控制面跨云调度 GPU",
            "企业级治理：SSO/SAML/SCIM、审计日志、预算与配额管控",
            "内置可观测性与调试（Ray Data/Train/Serve 仪表盘）",
        ],
        "price": "暂未公开",
        "platform": "Web（托管云平台，支持 AWS/Azure/GCP 等）",
        "source_url": "https://www.anyscale.com/platform",
        "last_verified": "2026-07-29",
        "confidence": "high",
        "conflict": False,
        "content_verified": True,
    },
    "lakera": {
        "url": "https://www.lakera.ai/",
        "description": "Lakera 是企业级 GenAI / AI 原生安全平台，实时防御提示注入、越狱与数据泄露，保护 AI 应用与 AI Agent，被 Dropbox 等 Fortune 500 企业采用。",
        "features": [
            "实时防御提示注入、越狱与数据泄露",
            "AI Agent 运行时防护（威胁检测 + 数据保护）",
            "AI 红队测试（风险导向的漏洞管理与修复建议）",
            "API 优先、云原生部署，支持 100+ 语言、模型无关",
            "上下文感知策略，超低延迟、可横向覆盖应用",
        ],
        "price": "暂未公开",
        "platform": "Web / API / SaaS",
        "source_url": "https://www.lakera.ai/",
        "last_verified": "2026-07-29",
        "confidence": "high",
        "conflict": False,
        "content_verified": True,
    },
    "trojai": {
        "url": "https://trojai.mitre.org",
        "description": "TrojAI 是 MITRE/NIST 主导的开源 AI 安全工具集，用于检测深度学习模型中的后门（木马）与对抗性攻击，支持 TensorFlow、PyTorch 等框架。（注：另有同名商业公司 TrojAI Inc，域名为 troj.ai，二者非同一主体）",
        "features": [
            "深度学习模型后门/木马检测",
            "对抗性样本生成与鲁棒性评估",
            "数据投毒检测",
            "多框架兼容（TensorFlow、PyTorch 等）",
            "开源免费，提供检测工具与示例数据集",
        ],
        "price": "开源免费",
        "platform": "Python / CLI / Web",
        "source_url": "https://trojai.mitre.org",
        "last_verified": "2026-07-29",
        "confidence": "low",
        "conflict": True,
        "content_verified": False,
    },
    "kubiya-ai": {
        "url": "https://kubiya.ai",
        "description": "Kubiya 是面向 DevOps / 平台工程团队的对话式 AI 助手，用自然语言在 Slack、MS Teams 与 CLI 中执行云基础设施操作（部署、扩缩容、CI/CD、故障响应）。",
        "features": [
            "自然语言驱动的基础设施操作（部署、扩缩容、回滚）",
            "集成 Slack / MS Teams / CLI，提供开发者自助服务",
            "连接 100+ 工具：AWS、Kubernetes、GitHub、Terraform 等",
            "可视化工作流编排（Composer）与 Python SDK",
            "临时权限、审计日志与团队协作",
        ],
        "price": "暂未公开",
        "platform": "Web / Slack / MS Teams / CLI",
        "source_url": "https://docs.kubiya.ai/",
        "last_verified": "2026-07-29",
        "confidence": "medium",
        "conflict": False,
        "content_verified": True,
    },
    "pulumi-ai": {
        "url": "https://www.pulumi.com/ai",
        "description": "Pulumi AI（现 Pulumi Neo）是 Pulumi 的 AI 基础设施代理，用自然语言生成并部署基础设施即代码（IaC），支持 AWS/Azure/GCP 等多云，输出 TypeScript/Python/Go 等。",
        "features": [
            "自然语言生成 Pulumi IaC 代码（TypeScript/Python/Go/C# 等）",
            "多云平台支持（AWS、Azure、GCP、Kubernetes 等）",
            "人类审批工作流与完整审计轨迹",
            "成本优化与配置/合规检查",
            "IDE 集成（VS Code/Cursor/Claude Code，经 MCP）与多云可见性",
        ],
        "price": "暂未公开（个人版开源免费）",
        "platform": "Web / CLI / IDE / API",
        "source_url": "https://www.pulumi.com/ai",
        "last_verified": "2026-07-29",
        "confidence": "high",
        "conflict": False,
        "content_verified": True,
    },
}

targets = set(updates.keys())
count = 0
for t in data:
    if t.get("slug") in targets:
        u = updates[t["slug"]]
        for k, v in u.items():
            t[k] = v
        count += 1

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print("updated", count, "tools")

# 英文内容生成：6版本对比（5个API模型 + Agent）

> 同一个工具：ChatGPT  
> Agent版本 = 我（WorkBuddy AI）直接撰写  
> API版本 = 通过SiliconFlow调用各模型生成  
> 测试时间：2026-04-11

---

## 1. 基本数据

| 版本 | 字数 | 生成时间 | 成本 |
|------|------|---------|------|
| DeepSeek-V3.2 | 1742 | 102.8s | ¥0.012 |
| Kimi-K2.5 | 1853 | 67.9s | ¥0.083 |
| MiniMax-M2.5 | 1626 | 34.6s | ¥0.012 |
| GLM-5.1 | 1863 | 96.8s | ¥0.100 |
| **GLM-5** | **2061** | **79.6s** | **¥0.??** |
| **Agent** | ~1650 | ~3min | ¥0.59 |

> GLM-5 成本待用户查SiliconFlow后台确认

---

## 2. GLM-5 vs GLM-5.1 快速对比

这两个模型来自同一家（智谱AI），先看看区别：

| 维度 | GLM-5 | GLM-5.1 |
|------|-------|---------|
| 字数 | 2061 | 1863 |
| 速度 | 79.6s | 96.8s |
| 结构 | ⭐⭐⭐⭐⭐ 最清晰（每个feature都有Pros/Cons双栏） | ⭐⭐⭐⭐ 标准 |
| 语言自然度 | ⭐⭐⭐⭐ 自然，有态度 | ⭐⭐⭐⭐⭐ 最自然 |
| 敢说真话 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 独特亮点 | "hallucinates package functions" "It's obvious to professors when AI writes a paper" | "Swiss Army knife" "a few of the blades are a bit dull" |
| 金句 | "It doesn't 'think' like a human. It predicts the next word." "Use it for outlines. It's terrible at writing the final copy." | "It loves to start answers with 'Certainly!'" |

**GLM-5 的最大亮点**：Feature部分用了 **Pros/Cons 双栏结构**，每个功能都明确说了"什么时候有用+什么时候会翻车"。这是5个模型里唯一这么做的，对用户决策帮助最大。

---

## 3. 六版本综合评分

| 维度 | DeepSeek | Kimi | MiniMax | GLM-5.1 | **GLM-5** | Agent |
|------|----------|------|---------|---------|-----------|-------|
| 吸引力 | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 实用性 | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 敢说真话 | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 语言自然 | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| SEO价值 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 结构清晰 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **总分** | **15/30** | **21/30** | **16/30** | **26/30** | **27/30** | **26/30** |

---

## 4. 关键发现

### 🏆 GLM-5 是英文内容的最佳API模型

GLM-5 在实用性维度超越了 GLM-5.1，主要因为：

1. **Pros/Cons 双栏结构** — 每个功能都有"什么时候有用+什么时候翻车"，用户决策效率最高
2. **具体的技术细节** — "hallucinates package functions" "pandas.merge_on_multiple_columns() which does not exist"，这是真实开发者才会遇到的问题
3. **安全提醒独特** — "Don't paste sensitive data" 这个tip其他模型都没提到，但对企业用户极其重要
4. **竞争对比** — 主动提到 "Claude 3.5 Sonnet is arguably better at coding"，这种诚实对比增加了内容可信度

### 对比 Agent 版本

| | Agent | GLM-5 |
|--|-------|-------|
| 优势 | 个人经验感更强（"I've personally gotten the most value"） | 结构更专业（Pros/Cons双栏） |
| 优势 | 决策引导更直接 | 技术细节更准确（"delve into""elevate"等AI高频词） |
| 优势 | 开头用数据吸引 | 竞争对手对比（Claude/Gemini） |
| 劣势 | 没有Pros/Cons结构 | 缺少个人视角 |
| 劣势 | 没提竞争对手 | "As a tech editor who spends hours every day testing" 是虚构人设 |

**结论**：GLM-5 和 Agent 质量几乎并列，但 GLM-5 在**结构化**方面更胜一筹，Agent 在**个人化**方面更强。

---

## 5. 最终排名

| 排名 | 模型 | 总分 | 成本 | 推荐场景 |
|------|------|------|------|---------|
| 🥇 | **GLM-5** | 27/30 | ¥0.?? | 英文工具页首选 |
| 🥈 | **Agent** | 26/30 | ¥0.59 | 特殊内容/有观点的页面 |
| 🥈 | **GLM-5.1** | 26/30 | ¥0.10 | 高质量+可接受价格 |
| 4 | **Kimi-K2.5** | 21/30 | ¥0.083 | 性价比不错 |
| 5 | **MiniMax-M2.5** | 16/30 | ¥0.012 | 中文最佳，英文一般 |
| 6 | **DeepSeek-V3.2** | 15/30 | ¥0.012 | 不推荐用于英文 |

---

## 6. 务实建议

**查一下GLM-5在SiliconFlow的实际消耗金额**，然后：

| 如果GLM-5价格... | 建议 |
|-----------------|------|
| ≤ ¥0.05/篇 | 🏆 **英文站默认用GLM-5**，中文站继续用MiniMax-M2.5 |
| ¥0.05-0.10/篇 | 英文重点工具用GLM-5，普通工具用MiniMax |
| > ¥0.10/篇 | 跟GLM-5.1一样贵，选5.1（语言更自然） |

---

## 7. 原文位置

- Agent版本：`data/_agent_chatgpt_en.md`
- 5个API版本：`data/_en_model_compare.md`
- GLM-5版本：`data/_glm5_en.md`

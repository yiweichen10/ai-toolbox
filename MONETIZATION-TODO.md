# 变现待办清单（CPS / 广告 / 商业化）

> 本文件集中记录 aitoollab.cn 变现相关的一切遗留问题与未闭环事项。
> 维护规则：完成一项就划掉并注明日期；新发现问题追加到对应优先级；"触发时机"判断何时做。
> 最后更新：2026-08-15

---

## 🔴 P0 — 时机成熟立即做

### 1. CPS 选品替换：云服务器 → 顺意图 AI SaaS 分销
- **现状**：CPS 卡主推阿里云/腾讯云/百度云（算力/服务器），与"来查工具"的 C 端流量意图错位，转化天然低。
- **方案**：云厂商降级为「AI编程 / AI开发」两品类的补充；主力换稿定、5118、AiPPT、讯飞等国内 AI 工具官方分销（注册返 + 会员分成 20-40%）。
- **触发时机**：beacon 数据积累 1-2 周（约 2026-08-29 前后），跑 `python scripts/analyze_beacon.py` 看各品类真实点击率，用数据决定换哪个品类。
- **依赖**：① beacon+utm 数据闭环（✅ 已建）；② 数据积累。

### 2. 变现覆盖缺口：高商业意图页面无 CPS 卡
- **现状**：对比页 / 替代页 / 排行页 / 分类页的 pageType 非 tool/article/news，loader.js 不注入 CPS 卡。这些「XX替代 / XX vs XX」页面购买意图最强，却是变现空白。
- **方案**：loader.js 的 init 增加对这些 pageType 的 CPS 处理 + 匹配规则（分类页按分类、对比页按被比工具品类）。
- **触发时机**：等 P0-1 数据出来后一起评估（改 pageType 逻辑影响面大，需单独一轮）。

---

## 🟡 P1 — 数据出来后做

### 3. 文章分类字段整体规范化
- **现状**：articles.json（177 篇）category 字段约 30 种值，中英文混用、同义多值，导致 CPS 卡匹配大量落 default、utm_campaign 归因维度散乱。
- **已做**：`industry-analysis`（12 篇）→「行业趋势」（2026-08-15）。
- **剩余**：
  - 英文残留：`tool-review`(2) / `tools-comparison`(1) / `industry-news`(1) / `ai-news`(1)，共 5 篇；
  - 中文同义：评测类 3 种 / 资讯类 5 种 / 趋势类 6 种写法待归并。
- **注意**：项目已有 `content_type` 字段（4 类）+ `scripts/classify_articles.py` 归并体系，category 混乱属历史遗留。归并时不能破坏已有 content_type 逻辑。
- **触发时机**：数据出来后，带着"哪个品类转化差"的目的去归并，而非为干净而干净。

---

## 🟢 P2 — 可选优化

### 4. 曝光改"视口曝光"（IntersectionObserver）
- **现状**：beacon 曝光是"渲染即计"（display 非 none 就算曝光），移动端正文深处 CPS 卡未滚到也计曝光，数据偏高。
- **方案**：用 IntersectionObserver 做真正"进入视口"的曝光判断。
- **触发时机**：不影响周报基本可用性，可选，优先级低。

---

## ⏳ 待验证 / 待数据

### 5. 曝光 bug 修复验收
- **状态**：✅ **已通过（2026-08-17 周报 #1）**。曝光 2277 / 点击 10 / CTR 0.44%，impression 与 click 均有数据，链路闭环。CTR 略低于 0.5% 合理区间下限，属 beacon 上线仅 3 天的积累初期正常偏低。
- **后续**：P0-1 选品替换按原计划 8/29 前后（数据积累 1-2 周）启动；08-24 周报 #2 做首次周环比。
- **若失败**：优先排查曝光是否仍为 0（见下方排查路径）。

### 7. ⚠️ 云大使"老用户/未认证"白关联风险（2026-08-17 用户后台实测）
- **现状**：云大使客户列表 6 条关联（8/16 前后）：老用户 3 条 + 未认证 2 条 + 新用户 1 条（nic***709）。**仅新用户首单返佣**——6 条里 5 条即使后续消费也不返佣。
- **含义**：CPS 引流的用户大量是"已注册过阿里云的老用户"（点推广链接也能关联，但不返佣），真实返佣转化率会远低于点击率表现。
- **方向（记入选品评估）**：① 落地文案引导"新用户/首次注册"场景；② 选品评估时把"目标人群是否大概率已是云用户"作为筛选维度（如开发者工具类用户基本都注册过云厂商，云服务器返佣效率天然低）；③ 与 P0-1（AI SaaS 分销）一起评估，SaaS 类（稿定/5118 等）无此老用户陷阱。

### 6. 平台后台转化数据归因核对（分平台而异）
- **阿里云云大使（被动，需等订单）**：
  - 实测「客户列表」页只展示脱敏客户名 + 关联时间 + 支付金额，**不展示来源/推广位字段**——看不到 utm 是设计如此，非 utm 失效；
  - 「云气值规则」入口是规则文档页，无导出按钮（此前指引有误）；
  - 当前 6 条关联客户全部 ¥0.00，无订单可归因。
  - 验证：待新用户（如 nic***709）产生首笔消费后，进「收益明细 / 订单明细」类菜单，按订单查推广位来源。
- **腾讯云 CPS（主动打标，可行 ✅ 2026-08-17 用户确认）**：
  - **用户确认腾讯支持直接打标（utm）**——推广链接的 `cps_key`（专属推广位）+ `utm_source/utm_medium/utm_campaign/utm_content` 能被后台解析归因，无需像阿里云那样盲等订单。
  - 2026-08-17 用户截图进一步确认：复制推广链接后弹窗提供 **「自定义标记推广位」** 功能，可给链接加推广位标记以追踪不同位置转化效果。
  - ✅ **机制已确认（2026-08-17）**：腾讯「自定义标记推广位」通过改变 URL 里的 `cps_promotion_id` 来区分推广位，**不新增其他参数**。不标记直接推广 = `cps_promotion_id=102961`；标记 `aitoollab-test` = `cps_promotion_id=102962`。
  - 🔴 **当前问题**：`ads/cps.json` 里 6 个腾讯品类/场景链接**全部缺失 `cps_promotion_id`**。没有它，腾讯后台只能按 `cps_key` 看总数据，无法区分 AI对话/绘画/视频/音频/产品发布/观点 哪个品类在转化；`utm_campaign` 仅用于我们自己的 beacon 统计，不进腾讯后台。
  - **下一步**：用户在腾讯云联盟后台为下表 6 个推广位各创建一个「自定义标记推广位」，把对应的 6 个 `cps_promotion_id` 贴给 AI；AI 一次性更新 `ads/cps.json` 所有腾讯链接并部署。

| 推广位名称（建议） | 对应 cps.json 位置 | 当前 utm_campaign（仅 beacon 用） |
|---|---|---|
| `aitoollab-ai-chat` | by_category.AI对话 | ai-chat |
| `aitoollab-ai-image` | by_category.AI绘画 | ai-image |
| `aitoollab-ai-video` | by_category.AI视频 | ai-video |
| `aitoollab-ai-audio` | by_category.AI音频 | ai-audio |
| `aitoollab-news-product` | by_news_category.产品发布 | product-release |
| `aitoollab-news-opinion` | by_news_category.观点 | opinion |

  - **注意**：创建时推广位类型选「自有平台/自建站点」（见你截图），名称按上表填，方便后台筛选。
  - ✅ **已落地（2026-08-17 18:24）**：用户创建 6 个推广位并贴回 ID，已批量写入 `ads/cps.json`（备份 cps.json.20260817.bak），scp 到服务器 `/var/www/aitoollab/html/ads/cps.json`，线上验证 6 处全部带 `cps_promotion_id`。loader.js 运行时 no-store 拉取，无需重建即生效。
  - ⚠️ **一处异常待用户确认**：AI对话 推广位的链接 `redirect=6871`（其余 5 个均为 `redirect=6544`=AI 焕新·智启新局）。可能用户创建时选了不同活动，已按用户给的链接原样写入；若是误选，需用户改回 6544 或确认 6871 即目标活动。
- **百度文心合伙人**：43 曝光 0 点击，暂无验证必要（等流量起来再说）。

---

## 附：曝光为 0 时的排查路径（备查）

1. `curl -sL https://www.aitoollab.cn/ads/loader.js | grep -c setTimeout` → 应为 ≥1（修复版已上线）；
2. `ssh ... "grep beacon.gif /var/www/aitoollab/logs/access.log | grep -o 'act=[a-z]*' | sort | uniq -c"` → 看 impression 是否有；
3. 本地起服 + 无头浏览器打开工具页，Network 面板看 `/ads/beacon.gif?act=impression` 是否发出；
4. 若仍无 impression：检查 CPS 卡是否真的渲染（`/ads/cps.json` 与 `/ads/slots/cps-card.html` 是否 200、body `data-category` 是否命中 by_category）。

# aitoollab.cn — DESIGN.md（升级版设计系统）

> 基于现有 `css/style.css` 变量体系升级而来。保留已验证的紫蓝主色与阴影底座，
> 把「Hero 动效 + Mockup」「真实 Logo 卡片」「紫渐变减法（留白 + 中性灰）」
> 「阴影分层」「排版四级」「暗色模式」六条升级点固化为可消费的设计规范。
> 供 Cursor / Claude Code / Google Stitch 等 AI 编程代理直接读取执行。

---

## 1. Visual Theme & Atmosphere（视觉主题与氛围）

- **设计哲学**：以「实测、专业、可信」为内核的 AI 工具导航站。视觉上从「扁平贴纸风」升级为「有呼吸感的专业中台」——大面积中性留白承载信息，紫蓝主色只在关键交互（CTA / 激活态）点睛，工具卡用真实品牌 Logo 制造一眼可辨的专业感。
- **视觉基调**：现代科技、克制专业、微暖中性。
- **核心视觉特征关键词**：`中性留白` · `真实 Logo 卡片` · `紫蓝点睛` · `微动效` · `清晰层级`
- **光影与质感倾向**：以「微阴影分层」为主（静止态 shadow-sm，hover 升 shadow-md/lg 形成呼吸），Hero 与 Stat 卡片使用毛玻璃（backdrop-filter: blur(10px)）+ 渐变光斑；不使用重投影、不堆高饱和。

---

## 2. Color Palette & Roles（调色板与角色）

```css
:root {
  --primary:       #2563eb;  /* 主交互色：按钮、链接、激活态（电光蓝） */
  --primary-light: #3b82f6;  /* 主色 hover / 渐变起笔（蓝 500） */
  --secondary:     #06b6d4;  /* 次色：渐变收笔、强调标签（青 500） */
  --accent:        #22d3ee;  /* 点缀交互：聚焦环、数据高亮（青 400） */
  --bg-gradient:   linear-gradient(135deg, #2563eb 0%, #06b6d4 100%);
}
```

| 角色 | HEX | CSS 变量 | 使用场景 |
|------|-----|----------|----------|
| 主色 Primary | `#4f46e5` | `--primary` | Primary 按钮底、文字链接、导航激活下划线、返回顶部 |
| 主色浅 Light | `#6366f1` | `--primary-light` | 按钮 hover、渐变起笔 |
| 次色 Secondary | `#7c3aed` | `--secondary` | 渐变收笔、Feature 标签、Hero |
| 强调 Accent | `#06b6d4` | `--accent` | Input 聚焦环、次级强调、数据高亮 |
| 文字主 Text Main | `#1e293b` | `--text-main` | 标题、正文强强调 |
| 文字次 Muted | `#64748b` | `--text-muted` | 辅助说明、元信息、占位符 |
| 文字浅 Light | `#f8fafc` | `--text-light` | 深色面（Hero/导航）上的文字 |
| 页面底 Body BG | `#f1f5f9` | `--body-bg` | 全局页面背景（中性冷灰，替代纯白堆叠） |
| 表面 Surface | `#ffffff` | `--surface` | 卡片、弹窗、输入框底 |
| 表面二 Surface-2 | `#f8fafc` | `--surface-2` | 斑马行、hover 底色、代码块 |
| 边框 Border | `#e2e8f0` | `--border` | 卡片描边、分隔线、输入框边框（新增，替代旧 #f1f5f9 描边） |
| 毛玻璃底 Glass BG | `rgba(255,255,255,0.15)` | `--glass-bg` | Hero / Stat 卡片底 |
| 毛玻璃边 Glass Border | `rgba(255,255,255,0.30)` | `--glass-border` | Hero / Stat 卡片描边 |

**Neutral / Gray Scale（中性灰阶，升级重点：大量用于底色与分隔，减少紫渐变滥用）**

| 层级 | HEX | 变量 | 用途 |
|------|-----|------|------|
| Gray-50 | `#f8fafc` | `--gray-50` | 表面二、hover 底 |
| Gray-100 | `#f1f5f9` | `--gray-100` | 页面底 |
| Gray-200 | `#e2e8f0` | `--gray-200` | 边框、分隔线 |
| Gray-300 | `#cbd5e1` | `--gray-300` | 滚动条、禁用态 |
| Gray-400 | `#94a3b8` | `--gray-400` | 占位符、图标次色 |
| Gray-500 | `#64748b` | `--gray-500` | 文字次 |
| Gray-700 | `#334155` | `--gray-700` | 正文（替代纯黑 #1e293b，更柔和） |
| Gray-900 | `#0f172a` | `--gray-900` | 深色模式页面底 |

**Semantic Colors（语义色，复用分类色系，保证全站一致）**

| 语义 | HEX | 变量 | 用途 |
|------|-----|------|------|
| Success | `#10b981` | `--success` | 可用 / 已收录 / 成功状态 |
| Warning | `#f59e0b` | `--warning` | 即将过期 / 待审核 |
| Error | `#ef4444` | `--error` | 错误 / 失效链接 |
| Info | `#3b82f6` | `--info` | 提示 / 新功能标记 |

**Shadow Colors（阴影色，rgba 底座）**

| 名称 | box-shadow 值 | 变量 |
|------|---------------|------|
| 阴影底 | `rgba(15,23,42,0.08)` | `--shadow-base` |
| 紫晕 | `rgba(79,70,229,0.18)` | `--shadow-primary` |

---

## 3. Typography Rules（排版规则）

**Font Family**
```css
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
             'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
--font-cn-display: 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
```
> 中文正文实际落到 `PingFang SC` / `Microsoft YaHei`；Inter 仅在拉丁字符（数字、英文工具名）生效，不强行用于中文。

**Type Scale（四级字重拉开：Hero 800 → 区块 700 → 卡片 600 → 正文 400）**

| 层级 | 字号 | 字重 | 行高 | 字距 | 用途 |
|------|------|------|------|------|------|
| Display Hero | 48px / 3rem | 800 | 1.10 | -1.5px | 首页 Hero 主标题 |
| H1 Page | 40px / 2.5rem | 800 | 1.15 | -1px | 内页大标题 |
| H2 Section | 28px / 1.75rem | 700 | 1.30 | -0.5px | 区块标题 |
| H3 Card | 18px / 1.125rem | 600 | 1.40 | -0.2px | 卡片标题、工具名 |
| Body LG | 17px / 1.0625rem | 400 | 1.70 | 0 | 引导段、Hero 副文 |
| Body | 16px / 1rem | 400 | 1.75 | 0 | 正文（行高由 1.6 提至 1.75，长文更透气） |
| Body SM | 14px / 0.875rem | 400 | 1.60 | 0 | 列表、元信息 |
| Caption | 13px / 0.8125rem | 500 | 1.50 | 0.3px | 标签内文 |
| Nano (UPPER) | 12px / 0.75rem | 600 | 1.40 | 0.5px | 区块 eyebrow、统计 label（uppercase） |

**设计哲学**：正文用 `--gray-700 (#334155)` 而非纯黑，降低长文视觉硬度；字重四级拉开避免「全站都在喊」；正文行高 1.75 适配中文阅读节奏。

---

## 4. Component Stylings（组件样式）

**Buttons**
```css
.btn-primary {
  background: var(--bg-gradient);
  color: #fff; padding: 13px 28px; border: none;
  border-radius: var(--radius-md); font-weight: 600; font-size: 15px;
  box-shadow: 0 4px 14px rgba(79,70,229,0.28);
  transition: var(--transition); cursor: pointer;
}
.btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 22px rgba(79,70,229,0.38); }
.btn-primary:active { transform: translateY(0); }

.btn-secondary {
  background: var(--surface); color: var(--primary);
  border: 1px solid var(--border); padding: 13px 28px;
  border-radius: var(--radius-md); font-weight: 600; font-size: 15px;
  transition: var(--transition);
}
.btn-secondary:hover { background: var(--surface-2); border-color: var(--primary-light); }

.btn-ghost {
  background: transparent; color: var(--text-muted); border: none;
  padding: 13px 20px; border-radius: var(--radius-md); font-weight: 500;
}
.btn-ghost:hover { background: var(--surface-2); color: var(--text-main); }

.btn-danger {
  background: var(--error); color: #fff; padding: 13px 28px;
  border: none; border-radius: var(--radius-md); font-weight: 600;
}
.btn-danger:hover { background: #dc2626; }
```

**Cards（工具卡：真实 Logo + 分层阴影，静止 shadow-sm，hover 呼吸）**
```css
.tool-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 22px 20px 18px;
  box-shadow: var(--shadow-sm);            /* 0 2px 8px rgba(0,0,0,0.07) */
  transition: var(--transition);
}
.tool-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);            /* 0 10px 30px rgba(0,0,0,0.12) */
  border-color: var(--primary-light);
}
.tool-icon-real {                          /* 真实品牌 Logo，优先于 emoji */
  width: 48px; height: 48px; border-radius: var(--radius-md);
  object-fit: contain; background: var(--surface-2);
  display: flex; align-items: center; justify-content: center; font-size: 24px;
}
```

**Inputs**
```css
.input {
  width: 100%; padding: 13px 18px;
  border: 1px solid var(--border); border-radius: var(--radius-pill);
  background: var(--surface); color: var(--text-main); font-size: 15px;
  transition: var(--transition);
}
.input::placeholder { color: var(--gray-400); }
.input:focus {
  outline: none; border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(79,70,229,0.15);
}
```

**Navigation（桌面端搜索合并进 header 右侧，去掉独立吸顶搜索条）**
```css
.header {
  position: sticky; top: 0; z-index: 100;
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
}
.nav-link { color: var(--text-muted); font-weight: 500; padding: 8px 14px; border-radius: var(--radius-sm); }
.nav-link:hover { color: var(--text-main); background: var(--surface-2); }
.nav-link.active { color: var(--primary); font-weight: 600; }
```

**Badges / Tags**
```css
.badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 10px; border-radius: var(--radius-pill);
  font-size: 12px; font-weight: 600; letter-spacing: 0.3px;
}
.badge-cat { background: var(--surface-2); color: var(--text-muted); }
.badge-free { background: rgba(16,185,129,0.12); color: var(--success); }
```

**Modals / Dialogs**
```css
.modal-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(15,23,42,0.55); backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center;
  animation: overlayIn 0.2s ease;
}
.modal-content {
  background: var(--surface); border-radius: var(--radius-lg);
  padding: 28px 32px; box-shadow: var(--shadow-2xl);
  animation: modalIn 0.28s cubic-bezier(0.4,0,0.2,1);
}
@keyframes overlayIn { from { opacity: 0 } to { opacity: 1 } }
@keyframes modalIn { from { opacity: 0; transform: translateY(12px) scale(0.98) } to { opacity: 1; transform: none } }
```

---

## 5. Layout Principles（布局原则）

- **Spacing System**：以 `4px` 为基数的倍数系统 — `4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48 / 64 / 72`。
- **Grid System**：工具卡用响应式网格 `grid-template-columns: repeat(auto-fill, minmax(260px, 1fr))`，列间距 `20px`。
- **Container**：内容容器 `max-width: 1200px`，左右 `padding: 0 24px`（移动端 `0 16px`）。
- **Section Spacing**：区块间距 `margin-bottom: 48px`；首屏 Hero 上下 `padding: 72px 24px`（桌面）/ `56px 18px`（移动）。
- **留白哲学**：从「紫渐变填满」改为「中性灰底 + 大留白承载」。Hero 之外大量使用 `#f1f5f9` 底色与白卡对比，区块间用 48px 呼吸，避免信息贴脸。

---

## 6. Depth & Elevation（深度与层级）

**Shadow System（完整 box-shadow 值，静止→悬浮→覆盖 形成呼吸）**
```css
--shadow-xs:   0 1px 3px  rgba(15,23,42,0.06);
--shadow-sm:   0 2px 8px  rgba(15,23,42,0.07);   /* 卡片静止态 */
--shadow-md:   0 4px 16px rgba(15,23,42,0.09);   /* 卡片 hover / 下拉 */
--shadow-lg:   0 10px 30px rgba(15,23,42,0.12);  /* 卡片强 hover / 浮层 */
--shadow-xl:   0 16px 40px rgba(15,23,42,0.16);  /* 吸顶导航 / 大卡 */
--shadow-2xl:  0 24px 60px rgba(15,23,42,0.22);  /* 弹窗 / 遮罩内容 */
--shadow-card: 0 2px 12px rgba(15,23,42,0.06), 0 0 0 1px rgba(15,23,42,0.04);
--shadow-hover:0 20px 40px rgba(79,70,229,0.18);  /* 主色晕，CTA 专用 */
```

**Surface Layers（表面层级）**
`background(#f1f5f9) → surface(#fff) → elevated(hover/shadow-lg) → overlay(模态 rgba(15,23,42,0.55))`

**Z-index Scale**
` sticky-header:100 · dropdown:200 · sticky-search:300 · modal-overlay:1000 · toast:1100 `

**Backdrop Effects（毛玻璃）**
`backdrop-filter: blur(12px)` 用于吸顶导航；`blur(10px)` 用于 Hero Stat 卡片；遮罩 `blur(4px)`。

---

## 7. Do's and Don'ts（设计规范与禁忌）

**Do's**
1. 紫蓝渐变只用在 Primary CTA 与 Hero，其余交互改中性灰，制造焦点。
2. 工具卡优先渲染真实品牌 Logo（`.tool-icon-real`），emoji 仅作兜底。
3. 卡片静止态给 `--shadow-sm`，hover 升 `--shadow-lg`，形成层级呼吸。
4. 正文用 `--gray-700 (#334155)`、行高 1.75，长文更透气。
5. 区块标题用 eyebrow 小标签 + 大留白制造节奏，避免千篇一律的紫色小横条。
6. 暗色模式用 `[data-theme="dark"]` 覆盖变量，不重写组件样式。
7. 所有可点元素加 `transition: var(--transition)`，hover 用 `translateY(-2~4px)` 微动。

**Don'ts**
1. 不要在全站每一个元素（按钮/标签/下划线/返回顶部/Newsletter 条）都铺同一渐变。
2. 不要把正文行高压在 1.6 以下，中文会显挤。
3. 不要用 `font-weight:800` 堆满所有标题，至少拉开 4 级字重。
4. 不要静止卡片零阴影「贴地」，扁平不等于无层次。
5. 不要为移动端保留常驻吸顶搜索条独占 150px 首屏，搜索应合并进 header。
6. 不要在亮色站强行套用未适配的暗色组件，必须走变量覆盖。
7. 不要对 320 个工具全用 emoji 图标，导致品牌不可辨。

---

## 8. Responsive Behavior（响应式行为）

| 断点 | 范围 | 策略 |
|------|------|------|
| Mobile | `< 640px` | 单列，搜索合并进 header 汉堡；Hero 标题 32px；卡片 grid 1 列 |
| Tablet | `640–1024px` | 卡片 grid 2 列；Hero 标题 40px；导航横向滚动 |
| Desktop | `1024–1440px` | 卡片 grid 3–4 列；Container 1200px 居中 |
| Wide | `> 1440px` | Container 上限 1200px 不变，留白增大 |

- **Touch Targets**：所有可点元素最小 `44 × 44px`。
- **折叠策略**：Desktop 搜索框内联 header 右侧；`< 640px` 收为汉堡菜单 + 搜索图标。分类导航桌面横排，`< 640px` 转 `.mobile-categories` 横向滚动。
- **Font Scaling**：Hero 48px → 移动 32px；H2 28px → 移动 22px；正文保持 16px 不变，仅行高微调。

---

## 9. Agent Prompt Guide（AI 代理提示指南）

**Quick Reference**
- 主色 `#2563eb` / 次色 `#06b6d4` / 强调 `#22d3ee`；底色 `#f1f5f9`；表面 `#fff`；边框 `#e2e8f0`；正文 `#334155`。
- 字体 `Inter` + `PingFang SC` 栈；正文行高 1.75；四级字重 800/700/600/400。
- 阴影：静止 `shadow-sm` → hover `shadow-lg`；圆角 sm8/md14/lg20/xl28/pill9999。
- 间距基数 4px；Container 1200px；暗色走 `[data-theme="dark"]` 变量覆盖。

**Component Prompts（可直接复制）**
1. 生成工具卡片组件，使用 `.tool-icon-real` 真实 Logo + `shadow-sm` 静止 + hover `shadow-lg` 上移 4px，遵循本 DESIGN.md 色彩与圆角。
2. 生成 Hero 区，紫蓝渐变底 + 两枚毛玻璃 Stat 卡片 + `@keyframes float` 光斑漂移 + 右侧产品 mockup，桌面双栏移动单栏。
3. 生成吸顶 header，桌面搜索框内联右侧，毛玻璃 `blur(12px)`，激活态 `nav-link.active` 紫色。
4. 生成暗色模式 CSS，仅用 `[data-theme="dark"]` 覆盖 `:root` 变量，页面底 `#0f172a`、表面 `#1e293b`、文字 `#e2e8f0`。
5. 生成区块标题组件，eyebrow 小标签（Nano uppercase）+ H2 700 + 大留白，不使用紫色小横条装饰线。
6. 生成模态框，遮罩 `rgba(15,23,42,0.55)` + `blur(4px)`，`modalIn` 0.28s 入场动画。

**Iteration Guide（AI 生成 UI 时的迭代建议）**
1. 先确认主色/底色/边框三色已对齐变量，再生成组件，避免色值漂移。
2. 每生成一个组件，检查静止态是否给了 `shadow-sm`，不要零阴影贴地。
3. 紫渐变出现超过 2 处时主动收敛，只保留 CTA 与 Hero。
4. 工具卡必须优先真实 Logo，生成后用 emoji 兜底校验降级路径。
5. 中文正文一律落到 `PingFang SC` 栈，行高不低于 1.75。
6. 移动端每次都验证：搜索是否并入 header、首屏是否露出至少 1 排工具卡。
7. 暗色模式改完必须切换验证对比度，文字不能低于 `#94a3b8` 太弱。
8. hover 动效统一 `translateY(-2~-4px)` + `var(--transition)`，不要混用位移与缩放导致抖动。
9. 区块标题装饰做差异化（eyebrow / 序号 / 纯留白），避免模板感。
10. 交付前用本文件第 2、3、6 章逐项核对色值与阴影一致性。

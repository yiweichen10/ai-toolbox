# 广告管理系统（ads/）

把广告从「写死在页面里」变成「独立文件夹管理」，改广告**不用重建站点**，直接在服务器上改文件即可生效。

## 目录结构

```
ads/
├── loader.js          # 前端加载器：读 config.json，按页型把广告注入页面
├── config.json        # 广告位总配置（位置 / 开关 / 适用页型）
├── slots/             # 每个广告位一份独立 HTML 文件（放真实广告代码的地方）
│   ├── content-top.html
│   ├── in-article.html
│   ├── sidebar-top.html
│   ├── sidebar-mid.html      # 默认关闭
│   ├── sidebar-bottom.html   # 默认关闭
│   ├── content-bottom.html
│   └── footer.html           # 默认关闭
├── nginx-ads-cache.conf      # 推荐：让广告文件不缓存，改完立即生效
└── README.md
```

## 工作流程

1. `build.py` 生成纯静态 HTML（不含任何广告代码）
2. 部署时 `inject_ads.py` 自动给每个页面加：
   - `<body data-page-type="tool">`（告诉前端这是工具页）
   - `<script src="/ads/loader.js" defer></script>`
3. 用户访问页面 → 浏览器加载 `loader.js` → 读取 `config.json` → 按当前页型把对应 `slots/*.html` 注入到页面合适位置

## 日常怎么改广告（核心：都不用重建）

| 需求 | 操作 | 是否重建 |
|------|------|----------|
| 换某广告位的代码 | 服务器上编辑 `ads/slots/xxx.html` | ❌ 不用 |
| 开/关某个广告位 | 改 `ads/config.json` 里该 slot 的 `enabled` | ❌ 不用 |
| 调整广告出现在哪些页 | 改 `config.json` 里该 slot 的 `pageTypes` | ❌ 不用 |
| 新增一个广告位 | 在 `config.json` 加一个 slot + 新建 `slots/新文件.html` | ❌ 不用 |
| 移动广告位置 | 改 `config.json` 里 `target`(CSS选择器) / `position` | ❌ 不用 |

> 改完服务器上的文件后，**广告立即生效**（loader 用 `no-store` 拉取，且建议加 nginx 不缓存规则）。
> 只有第一次需要部署本文件夹（deploy.sh 已自动同步 `ads/` 目录）。

## 页面类型（data-page-type）

| 值 | 页面 |
|----|------|
| home | 首页 |
| tool | 工具详情页 |
| article | 文章页 / 文章列表页 |
| category | 分类页 |
| compare | 对比页 |
| alternatives | 替代方案页 |
| ranking | 排名页 |
| quiz | 测试选择器页 |
| live | 实时数据面板 |
| dict | AI词典页 |
| news | 快讯页（每日快讯 / 分类 / 列表） |
| misc | 关于/联系/隐私/404 等 |

## 广告位说明（默认开启的）

| 广告位 | 位置 | 出现页型 |
|--------|------|----------|
| content-top | 内容区顶部通栏（建议 728×90 / 自适应） | 全部 |
| in-article | 正文第1段之后（信息流/原生广告） | tool / article |
| sidebar-top | 右侧栏顶部（300×250 / 300×600） | tool / article / dict |
| content-bottom | 内容区底部（相关推荐之上） | 全部 |
| sidebar-mid | 右侧栏中部 | tool / article / dict（默认关） |
| sidebar-bottom | 右侧栏底部 | tool / article / dict（默认关） |
| footer | 页脚上方 | 全部（默认关） |
| news-top | 资讯页顶部横幅（728×90 / 自适应） | news（默认关，2026-08-12 新增） |
| news-inline | 资讯页信息流中插（第 4 条快讯之后） | news（默认关，2026-08-12 新增） |
| news-bottom | 资讯页列表底部通栏 | news（默认关，2026-08-12 新增） |

> 资讯页额外有一张 **CPS 推广卡**（2026-08-12 新增）：loader.js 在 news 页面自动取
> `cps.json` 的 `by_news_category` 渠道（按第一条快讯栏目标签匹配，未命中回落 default）
> 渲染到第 `afterIndex` 条快讯之后，开关在 `config.json` 的 `cps.news.enabled`。
> 文章页也有一张 **CPS 推广卡**：桌面端侧边栏顶部、移动端正文第 4 段后（CSS 互斥只显示其一），
> 渠道按文章 `data-category` 匹配 `by_category` → `by_article_category` → default，
> 开关在 `config.json` 的 `cps.article.enabled`。
> 无需任何联盟账号即可开始变现（阿里云/腾讯云/百度文心推广链接已配置）。
> 卡片曝光与点击已上报百度统计（事件名 `CPS/impression`、`CPS/click`，参数=渠道|页型），
> 优化文案/位置前先看这里的数据。
> 卡片支持**引流钩子福利条**：`cps.json` 顶层 `hooks` 按渠道配置（当前阿里云=
> "🎁 新用户赠超 1 亿 Tokens 免费额度"，千问/百炼新用户活动），条目可用 `hook` 字段覆盖。

## 放入真实广告代码示例

**AdSense 展示广告**（把下面整段替换 slots/xxx.html 里的内容）：

```html
<ins class="adsbygoogle"
     style="display:block"
     data-ad-client="ca-pub-你的发布商ID"
     data-ad-slot="你的广告单元ID"
     data-ad-format="auto"
     data-full-width-responsive="true"></ins>
<script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
```

> 提示：Google AdSense 的库脚本 `<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js">`
> 只需在**任意一个** slot 文件里放一次，loader 会自动去重，不会重复加载。

**自营 / 联盟 banner**：直接放 `<a><img></a>` 或对方给的 HTML 代码片段即可。

## 推荐：nginx 不缓存（让修改秒级生效）

把 `nginx-ads-cache.conf` 的内容加进站点的 nginx `server {}` 块，然后 `nginx -s reload`：

```nginx
location /ads/ {
    add_header Cache-Control "no-cache, no-store, must-revalidate";
}
```

不加也能用（loader 用 `no-store` 拉取），加了更稳妥，避免浏览器/CDN 缓存旧广告。

# SEO 网站优化指南

根据模板标准，对网站进行系统性SEO优化。

## 📁 已完成
- ✅ 网站备份：`C:/Users/27040/WorkBuddy/20260321092139/backup-20260506-071740`

## 🎯 优化重点

### 1. 结构化数据（JSON-LD）优化

#### 文章页（Article）
需要添加的字段：
```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "标题（不超过110字符）",
  "description": "描述",
  "image": {
    "@type": "ImageObject",
    "url": "图片URL",
    "width": 1200,
    "height": 630
  },
  "datePublished": "YYYY-MM-DDThh:mm:ss+08:00",
  "dateModified": "YYYY-MM-DDThh:mm:ss+08:00",
  "author": {
    "@type": "Person",
    "name": "AI工具宝箱编辑组",
    "url": "https://www.aitoolbox.hk/about"
  },
  "publisher": {
    "@type": "Organization",
    "name": "AI工具宝箱",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.aitoolbox.hk/images/logo.png",
      "width": 200,
      "height": 60
    }
  },
  "wordCount": 数字,
  "about": [
    {
      "@type": "Thing",
      "name": "主题实体1"
    }
  ],
  "abstract": "150-250字摘要，AI引擎优先读取",
  "speakable": {
    "@type": "SpeakableSpecification",
    "cssSelector": ["h1", ".tl-dr", ".article-body h2", ".faq-section"]
  }
}
```

#### 工具页（SoftwareApplication）
需要修正的字段：
```json
{
  "@type": "SoftwareApplication",
  "applicationCategory": "ProductivityApplication",  // 修正
  "offers": [  // 必须是数组
    {
      "@type": "Offer",
      "name": "免费版",
      "price": 0,  // 必须是数字
      "priceCurrency": "USD"
    }
  ],
  "aggregateRating": {
    "ratingCount": 12500  // 必须是整数，不能是 "12.50000"
  },
  "featureList": ["功能1", "功能2"],
  "abstract": "150-250字摘要",
  "speakable": {...}
}
```

#### 文章列表页
需要添加：
- `Blog` JSON-LD
- `ItemList` JSON-LD
- `WebPage` with `speakable`

### 2. Meta 标签优化

#### 所有页面需要添加：
```html
<meta property="og:locale" content="zh_HK">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="图片描述">
```

#### Twitter Card 统一改为：
```html
<meta name="twitter:card" content="summary_large_image">
```

#### 文章页需要添加 OG 文章标签：
```html
<meta property="article:published_time" content="YYYY-MM-DDThh:mm:ss+08:00">
<meta property="article:modified_time" content="YYYY-MM-DDThh:mm:ss+08:00">
<meta property="article:author" content="作者名">
<meta property="article:section" content="分类">
<meta property="article:tag" content="标签1">
```

### 3. HTML 结构优化

#### 修正 lang 属性：
```html
<html lang="zh-HK">  <!-- 原来是 zh-CN -->
```

#### 文章页添加 TL;DR 区块：
```html
<div class="tl-dr" style="background:#f0f9ff;border-left:4px solid #4f46e5;padding:14px 18px;border-radius:0 8px 8px 0;margin:18px 0;">
  <strong style="font-size:13px;color:#4f46e5;">📌 核心结论（TL;DR）</strong>
  <p style="margin:6px 0 0;font-size:14px;line-height:1.7;color:#1e293b;">
    核心结论...
  </p>
</div>
```

#### 添加 FAQ 可见区块（与 JSON-LD FAQPage 对应）：
```html
<section class="faq-section">
  <h2>常见问题</h2>
  <div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
    <h3 itemprop="name">问题1</h3>
    <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
      <p itemprop="text">回答1</p>
    </div>
  </div>
</section>
```

### 4. .gitignore 完善

确保包含以下敏感文件保护：
```
# Environment variables (API keys, secrets)
.env
.env.*
!.env.example

# Keys and certificates
*.key
*.pem
*.p12
*.pfx

# Config with sensitive data
secrets.json
config-private.*
credentials.*

# Backup files
backup-*/

# Build output
dist/
build/
out/
.next/
.nuxt/

# Logs
*.log
logs/
```

## 🚀 批量优化脚本使用说明

### 方法1：使用 Python 脚本（推荐）
```bash
cd C:/Users/27040/WorkBuddy/20260321092139/seo-site
pip install beautifulsoup4 lxml
python3 optimize_site.py
```

### 方法2：手动优化关键页面
选择几个重要页面手动优化，作为示例：
1. `articles/ai-terminal-coding-tools-comparison-2026/index.html`
2. `tools/chatgpt/index.html`
3. `articles/page/1/index.html`

## ✅ 优化检查清单

- [ ] 所有页面 `lang="zh-HK"`
- [ ] 所有页面添加 `og:locale`
- [ ] 所有页面 `twitter:card` = `summary_large_image`
- [ ] 文章页 JSON-LD 添加 `abstract`, `speakable`, `wordCount`
- [ ] 工具页 JSON-LD 修正 `offers`, `ratingCount`, `applicationCategory`
- [ ] 列表页添加 `Blog`, `ItemList` JSON-LD
- [ ] 文章页添加 TL;DR 区块
- [ ] 文章页和工具页添加 FAQ 可见区块
- [ ] 完善 .gitignore 文件
- [ ] 测试网站确保无报错

## 🔒 安全提醒

**推送前务必检查**：
1. 运行 `git status` 确认没有敏感文件
2. 检查 `.env` 文件不会被推送
3. 确认 `backup-*` 目录在 .gitignore 中
4. 检查 HTML 中没有硬编码的 API Key

## 📞 联系信息

优化完成后，使用以下命令检查：
```bash
# 检查哪些文件会被推送
git add -n .

# 如果误加了敏感文件，用以下命令移除
git reset HEAD <file>
```

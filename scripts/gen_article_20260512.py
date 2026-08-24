#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 2026-05-12 SEO文章：Chrome DevTools MCP完整使用教程
类型：D（操作指南型）
"""

import json, sys, os, datetime

ARTICLE = {
    "title": "Chrome DevTools MCP完全使用教程：让AI Agent直接控制浏览器，从安装到实战（2026年5月更新）",
    "slug": "chrome-devtools-mcp-tutorial-2026",
    "date": "2026-05-12",
    "category": "AI工具教程",
    "tags": ["Chrome DevTools", "MCP", "AI Agent", "浏览器自动化", "GitHub Trending", "编程工具"],
    "summary": "Chrome DevTools MCP是Chrome官方团队推出的MCP Server，让AI编程助手（Claude/Cursor等）直接读取浏览器控制台、网络请求、DOM结构，实现真正的AI驱动浏览器自动化。本文手把手教你从安装到三个实战案例。",
    "content": """## 一句话结论

Chrome DevTools MCP 把浏览器的「开发者工具」变成了 AI Agent 的眼睛和手——AI 现在能直接看控制台报错、抓网络请求、操作 DOM，不再是个「瞎子程序员」。

如果你在用 Claude Desktop、Cursor、Windsurf 这类 AI 编程工具，花 10 分钟配好这个，调试前端问题的效率至少翻倍。

---

## 一、Chrome DevTools MCP 是什么？为什么突然火了？

### 先说背景：AI 写代码的最大痛点

你让 Claude 帮你写一个登录页面，它生成了代码，但你运行后发现报错。你把报错信息复制给 Claude，它分析后给出修复方案——这个过程需要**人工中转**。

更糟糕的是：Claude 看不到浏览器控制台的红色报错、看不到网络请求的 404、看不到 DOM 结构到底长什么样。它只能「盲改」。

**Chrome DevTools MCP 解决的就是这个问题。**

### MCP 是什么（简单版）

MCP（Model Context Protocol，模型上下文协议）是 Anthropic 2024 年推出的开放标准，让 AI 模型能够连接各种外部工具和数据源。

你可以把 MCP 理解为 AI 的「插件系统」：
- 没有 MCP：AI 只能「说话」（生成文本）
- 有了 MCP：AI 能「做事」（读文件、查数据库、控制浏览器）

### Chrome DevTools MCP 做了什么

Chrome DevTools 团队（注意：是 Google 官方团队，不是第三方）在 2026 年 5 月正式开源了 `chrome-devtools-mcp` 项目，它的核心是：

> 把 Chrome 浏览器的 DevTools 协议封装成了一个 MCP Server，让任何支持 MCP 的 AI 客户端都能直接「驾驶」浏览器。

具体能做什么？

| 功能 | 描述 |
|------|------|
| 🔍 控制台监控 | AI 实时读取 console.log/error/warning |
| 🌐 网络请求捕获 | 查看所有网络请求、响应状态码、耗时 |
| 🎯 DOM  inspection | 查看页面元素结构、属性、样式 |
| 🖱️ 交互操作 | 点击、输入、滚动、截图 |
| 🧪 调试断点 | 设置断点、单步执行 JavaScript |
| 📸 截图对比 | 全页截图、元素截图、视觉回归测试 |

**最关键的是**：这一切都是 AI 自动完成的，不需要你手动复制报错信息。

### 为什么现在才火？

- **2026 年 5 月**：项目在 GitHub Trending 走红，Chrome 官方团队正式维护
- **MCP 生态成熟**：Claude Desktop、Cursor、Windsurf 都支持了 MCP
- **AI Agent 时代**：大家意识到「让 AI 自己看浏览器」比「把报错复制给 AI」效率高 10 倍

---

## 二、环境准备：安装前必须检查的三件事

### 2.1 安装 Node.js（必需）

Chrome DevTools MCP 是一个 Node.js 包，需要 Node.js 18+。

```bash
# 检查是否已安装
node --version
npm --version

# 如果没安装，去官网下载：https://nodejs.org/
# 推荐 LTS 版本（目前是 Node 22.x）
```

### 2.2 安装 Chrome 浏览器（必需）

DevTools MCP 通过 Chrome DevTools Protocol（CDP）连接浏览器，需要 Chrome 或 Chromium。

```bash
# 检查 Chrome 是否已安装
# Windows: chrome://version/
# macOS: Applications/Google Chrome.app
# Linux: google-chrome --version
```

### 2.3 选择一个 MCP 客户端（三选一）

| 客户端 | 推荐度 | 特点 |
|--------|--------|------|
| **Claude Desktop** | ⭐⭐⭐⭐⭐ | 官方支持最好，配置最简单 |
| **Cursor** | ⭐⭐⭐⭐ | 编程场景最强，MCP 支持完善 |
| **Windsurf** | ⭐⭐⭐ | 新兴 IDE，MCP 支持较新 |

本文以 **Claude Desktop** 和 **Cursor** 为例，分别给出配置方案。

---

## 三、方式一：在 Claude Desktop 中配置 DevTools MCP

### 3.1 安装 Claude Desktop

如果还没安装：[https://claude.ai/download](https://claude.ai/download)

### 3.2 找到配置文件

| 系统 | 配置文件路径 |
|------|-------------|
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

### 3.3 编辑配置文件

打开配置文件（如果不存在就新建），加入以下内容：

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": [
        "@google/chrome-devtools-mcp"
      ]
    }
  }
}
```

### 3.4 重启 Claude Desktop

配置修改后必须完全退出 Claude Desktop（系统托盘右键退出），再重新打开。

### 3.5 验证安装

打开 Claude Desktop，在对话中输入：

```
请帮我检查一下我的 Chrome 浏览器是否连接成功，列出当前打开的标签页。
```

如果看到 Claude 调用了 `chrome-list-tabs` 工具并返回了标签页列表，说明配置成功！

**常见问题 1：Claude 说「没有找到 chrome-devtools 工具」**

→ 检查配置文件路径是否正确，JSON 格式是否有语法错误（可以用 `jsonlint` 验证）。

**常见问题 2：连接 Chrome 时提示「No Chrome instance found」**

→ 需要先启动 Chrome 并开启远程调试端口：
```bash
# Windows
chrome.exe --remote-debugging-port=9222

# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# Linux
google-chrome --remote-debugging-port=9222
```

---

## 四、方式二：在 Cursor 中配置 DevTools MCP

Cursor 的 MCP 配置方式略有不同，支持两种方式：**命令式**（推荐）和 **SSE 流式**。

### 4.1 打开 Cursor 设置

1. 打开 Cursor
2. 按 `Ctrl+Shift+P`（macOS: `Cmd+Shift+P`）
3. 输入 `MCP`，选择 `MCP: Add MCP Server`

### 4.2 命令式配置（推荐）

在弹出的配置界面中填入：

```json
{
  "name": "Chrome DevTools",
  "command": "npx",
  "args": ["@google/chrome-devtools-mcp"],
  "env": {}
}
```

### 4.3 SSE 流式配置（高级）

如果你希望 MCP Server 持续运行（而不是每次调用都启动新进程），可以用 SSE 模式：

```bash
# 先全局安装
npm install -g @google/chrome-devtools-mcp

# 启动 SSE 服务器
chrome-devtools-mcp --transport sse --port 9222
```

然后在 Cursor 中配置：

```json
{
  "name": "Chrome DevTools SSE",
  "url": "http://localhost:9222/sse"
}
```

### 4.4 验证安装

在 Cursor 的 MCP 面板（`Ctrl+Shift+P` → `MCP: List Servers`）中，应该能看到 `Chrome DevTools` 显示为「Running」状态。

---

## 五、实战案例 1：让 AI 自动发现并修复前端 Bug

这是最实用的场景。传统流程是：

> 你：运行代码 → 打开控制台看报错 → 复制报错给 Claude → Claude 分析 → 你手动改代码

用了 DevTools MCP 之后：

> 你：打开有 Bug 的页面，告诉 Claude「帮我找出为什么按钮点击没反应」→ Claude 自动看控制台、检查 DOM、分析事件绑定 → 直接给出修复方案

### 具体操作步骤

**第 1 步**：启动 Chrome 并开启远程调试

```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\temp\chrome-debug"
```

**第 2 步**：在 Chrome 中打开你的项目页面（比如 `http://localhost:3000`）

**第 3 步**：在 Claude Desktop 中输入：

```
我的网页上有一个「提交」按钮，点击后没有任何反应。
请帮我：
1. 检查控制台是否有 JavaScript 错误
2. 检查按钮的 DOM 结构，看事件监听器是否正确绑定
3. 如果有错误，告诉我具体是哪一行代码的问题
```

**第 4 步**：Claude 会自动调用以下 MCP 工具：
- `chrome-list-tabs`：找到你的标签页
- `chrome-console-messages`：读取控制台消息
- `chrome-inspect-element`：检查按钮元素
- `chrome-evaluate`：在页面中执行 JavaScript 来调试

**第 5 步**：Claude 给出修复方案，你确认后可以直接让它改代码（如果你同时配了文件系统 MCP）。

### 效率对比

| 方式 | 发现问题 | 定位问题 | 修复验证 | 总计 |
|------|---------|---------|---------|------|
| 传统方式 | 人工（10秒） | 人工（2分钟） | 人工（30秒） | ~3分钟 |
| DevTools MCP | AI自动（5秒） | AI自动（10秒） | 人工确认（10秒） | ~25秒 |

---

## 六、实战案例 2：自动化 UI 测试和视觉回归

如果你在做一个 Web 项目，每次改完代码都要手动测试各个页面——这个场景 DevTools MCP 也能大幅简化。

### 场景：检查页面在不同视口下的渲染问题

告诉 Claude：

```
请帮我检查 http://localhost:3000 在以下视口下的显示问题：
1. 桌面端（1920×1080）
2. 平板（768×1024）
3. 手机（375×667）

对每个视口：
- 截图保存
- 检查是否有横向滚动条
- 检查文字是否溢出容器
- 检查按钮是否可点击（没有被遮挡）
```

Claude 会依次：
1. 用 `chrome-set-device-metrics` 设置视口大小
2. 用 `chrome-screenshot` 截图
3. 用 `chrome-evaluate` 执行 JS 检查布局问题
4. 汇总所有问题并给出修复建议

### 场景：视觉回归测试（对比两次改动）

如果你重构了 CSS，想知道有没有破坏现有样式：

```
我刚刚修改了 styles/main.css，请帮我对比修改前后首页的截图差异。
```

Claude 可以配合 `chrome-screenshot` 工具，在修改前后分别截图，然后用图像对比库（需要额外配置）帮你发现视觉差异。

---

## 七、实战案例 3：用 AI 辅助爬取动态渲染的网页数据

很多现代网站用 JavaScript 动态渲染内容（比如 React/Vue 应用），传统的 HTTP 请求爬不到数据，因为内容不在 HTML 源码里。

**DevTools MCP 让 AI 能直接等页面渲染完成后再读取内容。**

### 具体操作

告诉 Claude：

```
请帮我从 https://example.com/products 这个页面提取所有产品的信息。
这个页面是用 React 渲染的，需要等 JavaScript 执行完成才能看到内容。

请：
1. 导航到这个页面
2. 等待网络请求完成（networkIdle）
3. 提取所有产品的名称、价格和链接
4. 结果以 JSON 格式输出
```

Claude 会调用：
- `chrome-navigate`：打开页面
- `chrome-wait-for`：等待特定元素出现或网络空闲
- `chrome-evaluate`：执行 JS 提取数据（`document.querySelectorAll(...)`）
- 把结果格式化为你想要的格式

### 注意事项

⚠️ **法律合规**：爬取数据前请确认网站的 `robots.txt` 和服务条款，不要爬取需要登录的隐私数据。

⚠️ **频率控制**：不要高频率请求，给目标服务器造成压力。

---

## 八、高级技巧：和文件系统 MCP 配合使用

单独用 DevTools MCP 已经很强了，但如果**同时配置文件系统 MCP**，可以实现「AI 全自动调试闭环」：

```
你：帮我修复登录页面的 Bug
↓
Claude：让我先看看控制台... 找到了，是 handleSubmit 函数里少了一个 await
↓
Claude：现在我直接修改 src/pages/Login.jsx 的第 47 行
↓（自动改代码）
Claude：代码已修改，请刷新页面验证
↓
你：刷新页面 → 问题解决！
```

### 配置文件示例（Claude Desktop）

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["@google/chrome-devtools-mcp"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem", "/path/to/your/project"]
    }
  }
}
```

这样 Claude 就能**同时**操作浏览器和读写你的代码文件，实现真正的全自动调试。

---

## 九、常见问题与踩坑记录

### Q1：MCP Server 启动后 Claude 识别不到？

**可能原因**：
1. `npx` 的缓存问题：尝试 `npx -y @google/chrome-devtools-mcp`（`-y` 强制使用最新版）
2. 防火墙拦截：检查是否有安全软件拦截了本地端口
3. Claude Desktop 版本太旧：更新到最新版

### Q2：Chrome 远程调试端口被占用？

```bash
# 查看哪个进程占用了 9222 端口
# Windows
netstat -ano | findstr 9222

# macOS/Linux
lsof -i :9222

# 然后换一个端口，比如 9223
chrome.exe --remote-debugging-port=9223
```

### Q3：AI 调用工具时超时？

DevTools MCP 某些操作（比如等待网络空闲）可能需要较长时间。可以在启动 MCP Server 时设置超时参数：

```bash
npx @google/chrome-devtools-mcp --timeout 60000
```

### Q4：在 WSL2 里能用吗？

能用，但需要额外配置——WSL2 和 Windows 的 localhost 网络隔离会导致连接问题。推荐直接在 Windows 原生环境使用。

### Q5：支持 Firefox 吗？

目前不支持。Chrome DevTools MCP 基于 Chrome DevTools Protocol（CDP），Firefox 使用的是不同的调试协议。如果你需要用 Firefox 调试，可以关注 [firefox-devtools-mcp](https://github.com/)（目前还没有官方版本）。

---

## 十、总结：该不该现在就上手？

### 适合你的场景 ✅

- 你每天都在用 Claude/Cursor 写前端代码
- 你经常需要调试浏览器控制台问题
- 你在做 Web 爬虫，目标网站是 JS 动态渲染的
- 你需要做 UI 自动化测试

### 暂时不适合 ⏸️

- 你主要写后端代码，很少碰前端
- 你的项目是移动端 App（不是 Web）
- 你用的 AI 客户端还不支持 MCP（比如旧版 GitHub Copilot）

### 下一步学习资源

| 资源 | 链接 |
|------|------|
| Chrome DevTools MCP 官方仓库 | [github.com/ChromeDevTools/chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp) |
| MCP 协议官方文档 | [modelcontextprotocol.io](https://modelcontextprotocol.io) |
| Claude Desktop MCP 配置指南 | [docs.anthropic.com](https://docs.anthropic.com) |
| Awesome MCP Servers | [github.com/punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) |

---

**一句话总结**：Chrome DevTools MCP 让 AI 从「代码生成器」变成了「能自己看浏览器、自己调试的编程助手」——如果你靠写前端吃饭，这个工具现在就值得配好。

*文章更新日期：2026 年 5 月 12 日。如有配置问题，欢迎在评论区留言。*
"""
}

def main():
    articles_path = os.path.join(os.path.dirname(__file__), '../data/articles.json')
    articles_path = os.path.normpath(articles_path)
    
    print(f"读取: {articles_path}")
    with open(articles_path, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    # 检查 slug 是否已存在
    existing_slugs = [a.get('slug', '') for a in articles]
    if ARTICLE['slug'] in existing_slugs:
        print(f"ERROR: slug '{ARTICLE['slug']}' 已存在，跳过插入")
        sys.exit(1)
    
    # 追加新文章
    articles.append(ARTICLE)
    
    with open(articles_path, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    
    total = len(articles)
    print(f"✅ 文章已插入！当前总数: {total}")
    print(f"标题: {ARTICLE['title']}")
    print(f"Slug: {ARTICLE['slug']}")
    print(f"日期: {ARTICLE['date']}")

if __name__ == '__main__':
    main()

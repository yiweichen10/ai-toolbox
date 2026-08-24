# 生成文章页和工具页的HTML文件（从模板复制）
$base = "c:\Users\27040\WorkBuddy\20260321092139\seo-site"

# 文章目录列表
$articleSlugs = @(
    "chatgpt-vs-claude-vs-gemini",
    "ai-painting-guide", 
    "cursor-vs-copilot-vs-windsurf",
    "ai-self-media-guide"
)

$articleTemplate = Get-Content "$base\articles\ai-tools-2026\index.html" -Raw

foreach ($slug in $articleSlugs) {
    $dir = "$base\articles\$slug"
    if (-not (Test-Path "$dir\index.html")) {
        Copy-Item "$base\articles\ai-tools-2026\index.html" "$dir\index.html"
        Write-Host "Created: articles/$slug/index.html"
    } else {
        Write-Host "Exists: articles/$slug/index.html"
    }
}

# 工具目录列表
$toolSlugs = @(
    "claude", "midjourney", "github-copilot", "cursor",
    "kimi", "doubao", "notion-ai", "runway",
    "stable-diffusion", "suno", "canva-ai"
)

$toolTemplate = Get-Content "$base\tools\chatgpt\index.html" -Raw

foreach ($slug in $toolSlugs) {
    $dir = "$base\tools\$slug"
    if (-not (Test-Path "$dir\index.html")) {
        Copy-Item "$base\tools\chatgpt\index.html" "$dir\index.html"
        Write-Host "Created: tools/$slug/index.html"
    } else {
        Write-Host "Exists: tools/$slug/index.html"
    }
}

Write-Host "`nDone! All pages created."

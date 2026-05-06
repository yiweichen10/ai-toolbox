#!/bin/bash
# SEO批量优化脚本 - 基础版
# 使用方法：bash seo-optimize-basic.sh

echo "============================================================"
echo "SEO 网站批量优化 - 基础版"
echo "============================================================"
echo ""

SITE_DIR="C:/Users/27040/WorkBuddy/20260321092139/seo-site"

# 检查是否在正确目录
if [ ! -d "$SITE_DIR" ]; then
    echo "错误：找不到网站目录 $SITE_DIR"
    exit 1
fi

cd "$SITE_DIR" || exit 1

echo "网站目录：$SITE_DIR"
echo ""

# 计数器
count_lang=0
count_og=0
count_twitter=0

echo "开始优化..."
echo ""

# 1. 修正 lang 属性为 zh-HK
echo "[1/3] 修正 lang 属性为 zh-HK..."
find . -name "*.html" -type f ! -path "./backup-*" | while read -r file; do
    if grep -q 'lang="zh-CN"' "$file"; then
        sed -i 's/lang="zh-CN"/lang="zh-HK"/g' "$file"
        ((count_lang++))
    fi
done
echo "  ✓ 已修正 $count_lang 个文件的 lang 属性"
echo ""

# 2. 添加缺失的 OG 标签
echo "[2/3] 添加缺失的 OG 标签..."
find . -name "*.html" -type f ! -path "./backup-*" | while read -r file; do
    # 添加 og:locale
    if ! grep -q 'og:locale' "$file"; then
        sed -i '/<meta property="og:site_name"/a\    <meta property="og:locale" content="zh_HK">' "$file"
        ((count_og++))
    fi
    
    # 添加 og:image:width
    if ! grep -q 'og:image:width' "$file"; then
        sed -i '/<meta property="og:image"/a\    <meta property="og:image:width" content="1200">\n    <meta property="og:image:height" content="630">' "$file"
    fi
done
echo "  ✓ 已为 $count_og 个文件添加 OG 标签"
echo ""

# 3. 修正 Twitter Card 为 summary_large_image
echo "[3/3] 修正 Twitter Card..."
find . -name "*.html" -type f ! -path "./backup-*" | while read -r file; do
    if grep -q 'name="twitter:card" content="summary"' "$file"; then
        sed -i 's/name="twitter:card" content="summary"/name="twitter:card" content="summary_large_image"/g' "$file"
        ((count_twitter++))
    fi
done
echo "  ✓ 已修正 $count_twitter 个文件的 Twitter Card"
echo ""

echo "============================================================"
echo "基础优化完成！"
echo ""
echo "下一步建议："
echo "1. 检查优化结果：git diff"
echo "2. 手动优化关键页面的 JSON-LD 结构化数据"
echo "3. 参考 SEO-OPTIMIZATION-GUIDE.md 完成高级优化"
echo "============================================================"

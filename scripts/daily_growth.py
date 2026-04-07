import os
import json
import subprocess
import sys
import time
from datetime import datetime

# 配置路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts')

# 定义要顺序执行的任务
STEPS = [
    {
        "name": "1. 维护工具库与自动补货",
        "cmd": [sys.executable, os.path.join(SCRIPTS_DIR, 'auto_tool_maintenance.py')]
    },
    {
        "name": "2. 产出下一篇 SEO 文章草稿 (E-A-B-C-D 轮替)",
        "cmd": [sys.executable, os.path.join(BASE_DIR, 'generate_articles.py')]
    },
    {
        "name": "3. 去 AI 味处理",
        "cmd": [sys.executable, os.path.join(BASE_DIR, 'humanize_articles.py')]
    },
    {
        "name": "4. 将新文章入库 (articles.json)",
        "cmd": [sys.executable, os.path.join(BASE_DIR, 'add_articles.py')]
    },
    {
        "name": "5. 为新文章生成 OG 封面图",
        "cmd": [sys.executable, os.path.join(BASE_DIR, 'gen_single_og.py')]
    },
    {
        "name": "6. 全站静态化构建 (SSG)",
        "cmd": [sys.executable, os.path.join(SCRIPTS_DIR, 'build.py')]
    },
    {
        "name": "7. Git 提交并推送部署 (Vercel)",
        "cmd": ["git", "add", "."] # git add will be followed by commit/push
    }
]

def run_cmd(cmd):
    print(f"\n[RUNNING] {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=BASE_DIR)
    return result.returncode == 0

def main():
    print(f"\n{'='*60}")
    print(f"[{datetime.now()}] 启动 aitoolbox.hk 每日自动化增长流程")
    print(f"{'='*60}")

    for step in STEPS[:6]: # Run first 6 steps normally
        if not run_cmd(step["cmd"]):
            print(f"❌ 步骤 '{step['name']}' 失败，任务中止。")
            sys.exit(1)

    # Git Push logic
    print("\n>>> 正在准备 Git 提交与推送...")
    run_cmd(["git", "add", "."])
    
    # 尝试获取最近增加的文章标题作为 commit message
    commit_msg = f"[auto-grow] {datetime.now().strftime('%Y-%m-%d')} content update"
    try:
        with open(os.path.join(BASE_DIR, 'data', 'articles.json'), 'r', encoding='utf-8') as f:
            articles = json.load(f)
            if articles:
                commit_msg = f"[article] {articles[0].get('title', 'Daily Update')}"
    except:
        pass

    run_cmd(["git", "commit", "-m", commit_msg])
    if run_cmd(["git", "push", "origin", "main"]):
        print(f"\n✅ 全部任务执行成功！网站已推送到 GitHub 并触发 Vercel 部署。")
    else:
        print(f"\n⚠️ 内容已生成但 Git 推送失败，请手动检查。")

if __name__ == "__main__":
    main()

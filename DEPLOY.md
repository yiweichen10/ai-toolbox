# AI工具宝箱 - Vercel 一键部署指南

## 方式一：网页一键部署（推荐，30秒搞定）

1. 打开 Vercel 官网：https://vercel.com
2. 用 GitHub 账号登录
3. 点击 **"Add New Project"**
4. 找到并选择 **ai-toolbox** 仓库
5. 配置如下：
   - Framework Preset: **Other**
   - Root Directory: **/** (默认)
   - Build Command: （留空，纯静态不需要）
   - Output Directory: **.** (当前目录)
6. 点击 **Deploy**
7. 等待30秒，部署完成！

部署成功后你会得到一个地址，类似：`https://ai-toolbox-xxx.vercel.app`

## 方式二：绑定自定义域名（可选）

在 Vercel 项目设置 → Domains → 添加你的域名。

推荐域名（可以去阿里云/腾讯云注册）：
- aibox.cn
- aitoolbox.cn
- ai-tool.cn

# AI 工具每日发布自动化任务执行记录

## 2026-05-13 13:00
- **执行结果**: 成功。发布 3 个工具，构建成功，阿里云部署成功，Git push 重试后成功。
- **发布工具**: 灵办AI (lingban-ai), Devin AI (devin-ai), Ironclad AI (ironclad-ai)
- **库存状态**: 已发布 195 个, 未发布 39 个, 总计 231 个（总工具数从197→231，有人补充了新数据）
- **库存补充**: 无需补充，39个未发布库存充足
- **构建**: 成功构建（修复了 badge=None bug：23个工具 badge=null 导致 build.py 崩溃）
- **修复**: 
  - tools.json: 23个工具 badge=null → badge={}
  - build.py line 2967: `t.get('badge', {}).get('type')` → `(t.get('badge') or {}).get('type')` 
  - 已创建备份: tools.json.20260513.bak, build.py.20260513.bak
- **部署**: 增量部署到阿里云成功（17个变化文件）
- **推送**: IndexNow 成功(3 URLs), 百度推送跳过（未配置token）
- **Git**: commit cfa8546b，首次 push 失败(OpenSSL TLS)，重试后成功
- **库存充足**: 39个未发布约够13天

## 2026-05-12 13:00
- **执行结果**: 部分成功。实际发布 6 个工具（deploy.sh --publish 会重复执行 publish_new_tools.py），构建成功，阿里云部署成功，Git push 失败（TLS 错误）。
- **发布工具**: Lumen5, Coda AI, Monica AI, 紫东太初, 万兴播爆, Pencil AI
- **库存状态**: 已发布 192 个, 未发布 5 个, 总计 197 个
- **库存补充**: ❌ 失败——预设列表已完全耗尽，generate_tools.py --count 20 产出 0 个新工具（5个去重跳过）
- **构建**: 313 个 HTML 文件生成成功（192 tools + 68 articles + 其他）
- **部署**: 增量部署到阿里云成功（1个变化文件 index.html）
- **推送**: IndexNow 成功(3 URLs), 百度推送失败（已知问题）
- **Git**: commit 97a46d97 + 822fcb2f + 6baa5fe1，push 失败（OpenSSL TLS error，持续故障）
- **⚠️ 紧急**: 未发布仅剩5个，不够1天。DEFAULT_TOOL_NAMES 预设列表已完全耗尽，需手动更新为2026年5月热门AI工具

## 2026-05-11 13:00
- **执行结果**: 部分成功。发布 3 个工具，构建成功，阿里云部署成功，Git push 失败（GitHub TLS 连接错误）。
- **发布工具**: Beatoven.ai (beatoven-ai), Mureka (mureka), 通义万相 (tongyi-wanxiang)
- **库存状态**: 已发布 186 个, 未发布 11 个, 总计 197 个
- **库存补充**: 触发补充，但预设列表基本用完，仅生成 3 个新工具（灵办AI/夸克AI/腾讯文档AI），去重跳过 17 个
- **构建**: 306 个 HTML 文件生成成功（186 tools + 67 articles + 其他）
- **部署**: 增量部署到阿里云成功（9个变化文件）
- **推送**: IndexNow 成功(295 URLs), 百度推送失败（已知问题）
- **Git**: commit 76147cba（发布）+ 3ff78fef（部署），push 失败（GitHub TLS 错误，3次重试均失败）
- **库存预警**: ⚠️ 预设工具名列表已基本用完，generate_tools.py 生成效率极低（20个请求只产3个新工具）。需手动更新预设列表为2026年5月热门AI工具

## 2026-05-10 13:00
- **执行结果**: 成功。发布 6 个工具（publish_new_tools.py 3个 + deploy.sh 内部 3个）。
- **发布工具**: Glean (glean), SlidesAI (slidesai), Resemble AI (resemble-ai), LanguageTool (language-tool), Buffer AI (buffer-ai), ChatPDF (chatpdf)
- **库存状态**: 已发布 183 个, 未发布 11 个, 总计 194 个
- **构建**: 302 个 HTML 文件生成成功（183 tools + 66 articles + 其他）
- **部署**: 增量部署到阿里云成功（1个变化文件 index.html）
- **推送**: IndexNow 403（SiteVerificationNotCompleted），百度推送跳过（未配置token）
- **Git**: commit e3168fa6（发布）+ 46326ae7（部署），push 成功
- **库存预警**: 11个未发布，约够3.7天，建议下次补充
- **注意**: deploy.sh --publish 会再次执行 publish_new_tools.py，导致本日实际发布6个工具。若只想发布3个应直接用 deploy.sh 不带 --publish

## 2026-05-09 13:00
- **执行结果**: 成功。发布 3 个工具。
- **发布工具**: Predis AI (predis-ai), Aider (aider), Scalenut (scalenut)
- **库存状态**: 已发布 177 个, 未发布 17 个, 总计 194 个
- **构建**: 295 个 HTML 文件生成成功（177 tools + 65 articles + 其他）
- **推送**: IndexNow 成功(3 URLs), 百度推送失败(over quota，已知问题)
- **Git**: commit 842df0d, push 成功
- **库存补充**: 无需补充，17个未发布库存约够5.7天

## 2026-05-08 13:00
- **执行结果**: 部分成功。发布 3 个工具，构建成功，Git push 失败（GitHub 连接被重置）。
- **发布工具**: LingoAI (lingoai), 星火认知大模型 (xinghuo-cognitive-model), Humata AI (humata-ai)
- **库存状态**: 已发布 174 个, 未发布 20 个, 总计 194 个
- **构建**: 291 个 HTML 文件生成成功（174 tools + 64 articles + 其他）
- **推送**: IndexNow 成功(3 URLs), 百度推送失败(over quota，已知问题)
- **Git**: commit 63fc133 已创建，push 失败（GitHub 连接重置/超时，3次尝试均失败）。需手动 push
- **库存补充**: 无需补充，20个未发布库存约够6.7天

## 2026-05-07 13:00
- **执行结果**: 成功。发布 3 个工具。
- **发布工具**: Zety AI (zety-ai), Semrush AI (semrush-ai), HappyHorse (happy-horse)
- **库存状态**: 已发布 171 个, 未发布 23 个, 总计 194 个
- **构建**: 287 个 HTML 文件生成成功（171 tools + 63 articles + 其他）
- **推送**: IndexNow 成功(3 URLs), 百度推送失败(over quota，已知问题)
- **Git**: commit ba27f18, push 成功
- **库存补充**: 无需补充，23个未发布库存约够7.7天

## 2026-05-06 13:00
- **执行结果**: 成功。发布 3 个工具。
- **发布工具**: Trae (trae), ProWritingAid (prowritingaid), Smartcat (smartcat)
- **库存状态**: 已发布 168 个, 未发布 26 个, 总计 194 个
- **构建**: 283 个 HTML 文件生成成功（168 tools + 62 articles + 其他）
- **推送**: IndexNow 成功(3 URLs), 百度推送失败(over quota，已知问题)
- **Git**: commit 187cc25, push 成功
- **库存补充**: 无需补充，26个未发布库存约够8.7天

## 2026-05-05 16:07
- **执行结果**: 成功。发布 3 个工具。
- **发布工具**: AdCreative AI (adcreative-ai), 书生浦语 (internlm), 即梦AI (jimeng-ai)
- **库存状态**: 已发布 165 个, 未发布 29 个, 总计 194 个
- **构建**: 279 个 HTML 文件生成成功（165 tools + 61 articles + 其他）
- **推送**: IndexNow 成功(3 URLs), 百度推送失败(over quota，已知问题)
- **Git**: commit c6e5657, push 成功
- **库存补充**: 预设列表已用完，新增22个工具名（Perplexity Comet/Aider/Trae/SlidesAI/Mureka等）。实际生成8/11个成功（3个超时）。最终29个未发布库存约够10天
- **注意**: build.py 2776/2781行有 datetime.strptime DeprecationWarning，Python 3.15 将 breaking change

## 2026-05-04 15:57
- **执行结果**: 成功。发布 3 个工具。
- **发布工具**: 面壁智能 (modelbest), Surfer SEO (surfer-seo), Frase (frase)
- **库存状态**: 已发布 162 个, 未发布 15 个, 总计 177 个
- **构建**: 274 个 HTML 文件生成成功（162 tools + 60 articles + 6 quizzes + 16 rankings + 5 live + 12 categories + 其他）
- **推送**: IndexNow 成功(3 URLs), 百度推送失败(over quota，已知问题)
- **Git**: commit 140fdbb, push 成功（首次超时，重试后成功）
- **库存补充**: API超时3次才补满18个（SiliconFlow不稳定），实际生成20个中有2个重试失败已跳过
- **脚本修复**: generate_tools.py 改为逐个保存（防中途超时丢失数据）
- **库存预警**: 无，15个未发布库存约够5天
- **注意**: DEFAULT_TOOL_NAMES 预设列表已用完，下次补充需新增工具名列表

## 2026-05-02 13:00
- **执行结果**: 成功。发布 3 个工具。
- **发布工具**: 文心一言 (wenxin-yiyan), Anyword (anyword), Replicate (replicate)
- **库存状态**: 已发布 142 个, 未发布 17 个, 总计 159 个
- **构建**: 252 个 HTML 文件生成成功（142 tools + 58 articles + 6 quizzes + 16 rankings + 5 live + 12 categories + 其他）
- **推送**: IndexNow 成功(3 URLs), 百度推送失败(over quota，已知问题)
- **Git**: commit fa298a5, push 成功
- **库存预警**: 无（发布前20个未触发<10阈值），发布后剩余17个，约够5.6天
- **注意**: 下次发布后库存将降至14个，建议关注

## 2026-05-01 13:00
- **执行结果**: 成功。发布 3 个工具。
- **发布工具**: Elicit (elicit), LottieFiles AI (lottiefiles-ai), Fooocus (fooocus)
- **库存状态**: 已发布 139 个, 未发布 20 个, 总计 159 个
- **构建**: 248 个 HTML 文件生成成功（139 tools + 57 articles + 6 quizzes + 16 rankings + 5 live + 12 categories + 其他）
- **推送**: IndexNow 成功(3 URLs), 百度推送失败(over quota，已知问题)
- **Git**: commit 4abffc1, push 成功（首次连接 reset，重试后成功）
- **库存预警**: 无，20个未发布库存约够7天

## 2026-04-30 13:00
- **执行结果**: 成功。发布 3 个工具。
- **发布工具**: Activepieces (activepieces), 阶跃星辰 (stepfun), InVideo AI (invideo-ai)
- **库存状态**: 已发布 133 个, 未发布 26 个, 总计 159 个
- **构建**: 161 个 HTML 文件生成成功（136 tools + 56 articles + 6 quizzes + 16 rankings + 5 live）
- **推送**: IndexNow 成功(3 URLs), 百度推送失败(over quota，已知问题)
- **Git**: commit 3f5e283, push 成功
- **库存预警**: 无，26个未发布库存约够8天

## 2026-04-10 13:00
- **执行结果**: 成功。发布 3 个工具。
- **发布工具**: Flux, Grok, Napkin AI
- **库存状态**: 已发布 75 个, 未发布 29 个, 总计 101 个
- **构建**: 161 个 HTML 文件生成成功
- **推送**: IndexNow 成功(3 URLs), 百度推送失败(over quota，已知问题)
- **Git**: commit 07566ae, push 成功

## 2026-03-25 13:00
- **执行结果**: 成功。没有未发布的工具。
- **输出**:
  ```
  [2026-03-25 13:00:26.399617] 正在尝试发布 3 个新工具...

  没有未发布的工具了，任务结束。
  ```

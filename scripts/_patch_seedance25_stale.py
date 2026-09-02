#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""定点同步 seedance 长文/FAQ 中残留的 2.0 口径事实。

只做事实句替换，不重写全文、不删 H2/FAQ 区块（避免重蹈 2026-08-01 长文覆盖事故）。
事实来源：官方博客 https://seed.bytedance.com/zh/blog/one-take-creation-flexible-referencing-introducing-seedance-2-5
        + 火山方舟/CapCut 上线时间等二手源（已在文案中标注）
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_store import load_all_tools, save_tool

SLUG = 'seedance'

REPL = [
    # H2
    ('## Seedance 2.0 是什么？',
     '## Seedance 2.5 是什么？'),
    # 首段：补 2.5 定位与发布信息
    ('它支持文本、图片、音频、视频多种输入，并生成带原生音频的 1080p 视频，'
     '这对需要"画面+声音一次成片"的短视频和广告场景很实用。',
     '它支持文本、图片、音频、视频多种输入，并生成带原生音频的高质量视频，'
     '这对需要"画面+声音一次成片"的短视频和广告场景很实用。'
     '2026 年 7 月 31 日，Seed 团队发布 Seedance 2.5：单次生成时长从 15 秒提升到 30 秒并支持多轮延长，'
     '多模态参考上限从 15 个（9 图 + 3 视频 + 3 音频）提升到 50 个（30 图 + 10 视频 + 10 音频），'
     '并新增时间戳级定向编辑、白模参考与光照控制，定位从"生成一个片段"升级为"完成一段创作"。'),
    # 核心功能：参考素材数量
    ('你可以同时喂入最多 9 张图片、3 个视频片段、3 个音频片段，再加上自然语言指令，'
     '模型会引用这些素材里的构图、运动、镜头、视觉效果和声音元素来生成新内容。',
     '2.5 版本起你可以同时喂入最多 30 张图片、10 段视频、10 段音频（2.0 为 9 图 / 3 视频 / 3 音频），'
     '再加上自然语言指令，模型会引用这些素材里的构图、运动、镜头、视觉效果和声音元素来生成新内容；'
     '在多人同框、群像叙事这类复杂场景里，也能同时还原多个人物的形象与声音。'),
    # 核心功能：编辑能力
    ('视频编辑与延伸能力支持针对指定片段、角色或动作做定向修改，也能基于提示"续拍"出连贯的后续镜头，'
     '把生成从一次性产出变成可迭代的创作。',
     '视频编辑与延伸能力支持针对指定片段、角色或动作做定向修改——2.5 起可用时间戳精确指定"第几秒改哪里"，'
     '只重生成那一段而不是整条重来；也能基于提示"续拍"出连贯的后续镜头（多轮延长可达数分钟，官方标注 Beta，'
     '正式出片仍建议以单次 30 秒为准）。此外还强化了绿幕替换、视角与运镜编辑，'
     '并新增白模（无纹理 3D 几何）参考与光照控制，可用 3D 白模先搭好空间结构、机位与运动轨迹再渲染成片。'
     '这些能力把生成从一次性产出变成可迭代的创作。'),
    # 价格与平台
    ('Seedance 本身是一个云端模型，通过即梦（jimeng.jianying.com）/Dreamina 的网页端，'
     '以及火山引擎等平台使用，按各平台各自的计费方式收费，模型价格暂未单独公开。',
     'Seedance 本身是一个云端模型，可通过即梦 AI（jimeng.jianying.com）/Dreamina 网页端、豆包专业版使用；'
     '开发者 API 于 2026 年 8 月 7 日上线火山方舟，2026 年 8 月 10 日接入剪映 CapCut。'
     '按各平台各自的计费方式收费，模型价格官方暂未单独公开'
     '（第三方报道称 2.5 生成一段 30 秒视频约 ¥80、较 2.0 上涨约 50%–86%，未经官方确认，以平台实际计费为准）。'),
    ('普通用户通常不直接和它打交道，而是通过即梦、Dreamina 或火山引擎这类前端去用',
     '普通用户通常不直接和它打交道，而是通过即梦、Dreamina、豆包、剪映或火山方舟这类前端去用'),
    # 最终结论
    ('从工作流角度，Seedance 更适合作为"成片引擎"嵌进你的创作流程',
     '从工作流角度，Seedance 2.5 更适合作为"成片引擎"嵌进你的创作流程'),
]

FAQ_NEW = [
    {"q": "Seedance 2.5 免费吗？",
     "a": "Seedance 2.5 通过即梦 AI、豆包专业版等平台提供免费额度，同时也有付费版本解锁更多功能和高频使用权限；"
          "开发者可走火山方舟 API（2026-08-07 上线），按平台/API 各自计费，模型本身定价官方未单独公开。"},
    {"q": "如何体验 Seedance 2.5？",
     "a": "可在即梦（jimeng.jianying.com）网页端、豆包专业版或 Dreamina 平台选择 Seedance 2.5 模型；"
          "开发者 API 已上线火山方舟，剪映 CapCut 于 2026-08-10 接入。"},
    {"q": "Seedance 2.5 支持哪些输入方式？",
     "a": "支持文字、图片、音频、视频四种输入方式；2.5 起单次最多可喂入 30 张图片、10 段视频、10 段音频（共 50 个全模态参考），"
          "2.0 为 9 图 / 3 视频 / 3 音频（共 15 个）。"},
    {"q": "生成的视频画质和时长如何？",
     "a": "2.5 单次可生成 30 秒高质量视频（2.0 为 15 秒），支持多轮延长可达数分钟（官方标注 Beta）；"
          "原生音画同步，并对材质、肤质与眼神、光影、饱和度做了系统优化以弱化常见的「油腻感」。"},
]


def main():
    tools = load_all_tools()
    t = next((x for x in tools if x.get('slug') == SLUG), None)
    if not t:
        print('未找到', SLUG); sys.exit(1)
    c = t.get('content', '')
    hit, miss = 0, []
    for old, new in REPL:
        if old in c:
            c = c.replace(old, new, 1)
            hit += 1
        else:
            miss.append(old[:50])
    t['content'] = c
    t['name'] = 'Seedance 2.5'
    t['faq'] = FAQ_NEW
    t['verified_faq'] = FAQ_NEW
    t['content_flags'] = ('已于 2026-09-03 同步：长文/FAQ 的 Seedance 2.0 口径（15 秒、15 个参考素材、无时间戳编辑）'
                          '已更新为 2.5 口径，并在文末新增「Seedance 版本演进对比」小节')
    t['content_blocked'] = False
    t['updated_date'] = '2026-09-03'
    t['last_verified'] = '2026-09-03'
    t['source_urls'] = [
        'https://seed.bytedance.com/zh/blog/one-take-creation-flexible-referencing-introducing-seedance-2-5',
        'https://seed.bytedance.com/seedance2_5',
        'https://seed.bytedance.com/seedance2_0',
        'https://www.toutiao.com/w/1875177129782532/',
    ]
    save_tool(t)
    print(f'替换命中 {hit}/{len(REPL)}，content {len(c)} 字')
    if miss:
        print('未命中(需人工确认):')
        for m in miss:
            print('  -', m)


if __name__ == '__main__':
    main()

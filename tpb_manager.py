# -*- coding: utf-8 -*-
"""tpb_manager.py — 顶部推广横幅运营台（本地服务，端口 8898）

管理 ads/tpb-config.json（顶部横幅的开关/形态/文案/链接），支持：
  - 表单编辑 + 实时预览（胶囊 pill / 全屏 full 双形态）
  - 保存本地真源（自动时间戳备份）
  - 一键部署：scp 上传服务器 + ssh 远端校验（fetch no-store，全站秒级生效，无需构建）

用法：python tpb_manager.py  →  浏览器打开 http://127.0.0.1:8898
架构与 affiliate_manager.py 一致：标准库 http.server + 内嵌单页 UI。
前端横幅逻辑见 scripts/build_lib/injectors.py（inject_promo_banner）。
"""
import http.server
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime

# Windows 编码兜底（AGENTS.md 铁律：控制台 GBK 打印中文/emoji 会崩）
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'ads', 'tpb-config.json')

SERVER_HOST = '121.43.144.99'
SERVER_PATH = '/var/www/aitoollab/html/ads/tpb-config.json'
SSH_KEY = os.path.expanduser('~/.ssh/id_ed25519_aitoollab')

PORT = 8898
VALID_STYLES = ('pill', 'full')
COOLDOWN_DEFAULT = 6          # 关闭横幅后默认冷却小时数（可被 tpb-config.json 的 cooldownHours 覆盖）
COOLDOWN_CHOICES = (1, 2, 4, 6, 12, 24)


def _parse_hours(v):
    """把前端传来的冷却小时数转成数字；空值用默认值，非法值原样返回交给 validate 报错。"""
    if v is None or str(v).strip() in ('', 'None'):
        return COOLDOWN_DEFAULT
    try:
        return float(v)
    except (TypeError, ValueError):
        return v


def load_config():
    """读本地配置；文件缺失/损坏时返回安全默认值。"""
    try:
        with open(CONFIG_PATH, encoding='utf-8') as f:
            cfg = json.load(f)
        if isinstance(cfg, dict):
            return cfg
    except Exception as e:
        print(f'[tpb] 配置读取失败，使用默认值: {e}')
    return {"enabled": True, "style": "pill", "cooldownHours": 6,
            "text": "一个免费白嫖 GLM 5.3 Flash 牛来 + Codex 的宝藏入口 →",
            "url": "https://teamorouter.cn/?i=bf8975d059"}


def validate(cfg):
    """表单校验，返回错误信息列表（空列表=通过）。"""
    errs = []
    if not isinstance(cfg.get('enabled'), bool):
        errs.append('enabled 必须是 true/false')
    if cfg.get('style') not in VALID_STYLES:
        errs.append('style 只能是 pill 或 full')
    text = (cfg.get('text') or '').strip()
    if not text:
        errs.append('广告词不能为空')
    elif len(text) > 100:
        errs.append(f'广告词过长（{len(text)} 字，上限 100，太长移动端会换行）')
    url = (cfg.get('url') or '').strip()
    if not url.startswith(('http://', 'https://')):
        errs.append('跳转链接必须以 http:// 或 https:// 开头')
    cd = cfg.get('cooldownHours')
    if cd is not None:
        if isinstance(cd, bool) or not isinstance(cd, (int, float)):
            errs.append('冷却时间必须是数字（小时）')
        elif cd < 0 or cd > 168:
            errs.append('冷却时间需在 0~168 小时之间（0 = 每次刷新都显示）')
    return errs


def save_config(cfg):
    """原子保存：先写时间戳备份，再写正式文件（UTF-8 无 ASCII 转义）。"""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    if os.path.isfile(CONFIG_PATH):
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        shutil.copy2(CONFIG_PATH, f'{CONFIG_PATH}.bak-{stamp}')
    tmp = CONFIG_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(tmp, CONFIG_PATH)


def deploy():
    """scp 上传到服务器并 ssh 回读校验，返回 (ok, message)。"""
    if not os.path.isfile(SSH_KEY):
        return False, f'未找到 SSH 私钥：{SSH_KEY}'
    try:
        r = subprocess.run(
            ['scp', '-i', SSH_KEY, '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=no',
             CONFIG_PATH, f'root@{SERVER_HOST}:{SERVER_PATH}'],
            capture_output=True, text=True, timeout=60, encoding='utf-8', errors='replace')
        if r.returncode != 0:
            return False, f'scp 失败：{(r.stderr or r.stdout or "").strip()[:300]}'
    except subprocess.TimeoutExpired:
        return False, 'scp 超时（60s）'
    except Exception as e:
        return False, f'scp 异常：{e}'
    # 回读校验：远端内容必须与本地一致
    try:
        v = subprocess.run(
            ['ssh', '-i', SSH_KEY, '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=no',
             f'root@{SERVER_HOST}', f'cat {SERVER_PATH}'],
            capture_output=True, text=True, timeout=30, encoding='utf-8', errors='replace')
        if v.returncode != 0:
            return False, f'远端校验失败：{(v.stderr or "").strip()[:300]}'
        local = json.load(open(CONFIG_PATH, encoding='utf-8'))
        remote = json.loads(v.stdout)
        if local == remote:
            return True, '部署成功，远端校验一致，全站秒级生效'
        return False, f'远端内容不一致！本地={json.dumps(local, ensure_ascii=False)} 远端={v.stdout[:300]}'
    except json.JSONDecodeError:
        return False, '远端返回的不是合法 JSON（可能上传不完整）'
    except Exception as e:
        return False, f'校验异常：{e}'


HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>顶部横幅运营台 - AI工具宝箱</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0f1117;color:#e2e8f0;font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;min-height:100vh}
.wrap{max-width:1080px;margin:0 auto;padding:24px 20px 60px}
.topbar{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:18px 22px;background:#151823;border:1px solid #252b3b;border-radius:14px;margin-bottom:22px;position:sticky;top:12px;z-index:10;backdrop-filter:blur(8px)}
.topbar h1{font-size:19px;font-weight:800;display:flex;align-items:center;gap:10px}
.topbar h1 .dot{width:9px;height:9px;border-radius:50%;background:#4ade80;box-shadow:0 0 8px #4ade80}
.topbar .sub{font-size:12px;color:#64748b;margin-top:3px}
.state-badge{font-size:12px;font-weight:700;padding:5px 13px;border-radius:999px;border:1px solid}
.state-on{color:#4ade80;border-color:rgba(74,222,128,.4);background:rgba(74,222,128,.08)}
.state-off{color:#f87171;border-color:rgba(248,113,113,.4);background:rgba(248,113,113,.08)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;align-items:start}
.card{background:#151823;border:1px solid #252b3b;border-radius:14px;padding:20px 22px}
.card h2{font-size:13px;color:#4a9eff;text-transform:uppercase;letter-spacing:1px;margin-bottom:16px;display:flex;align-items:center;gap:8px}
.card h2::before{content:'';width:3px;height:14px;background:#4a9eff;border-radius:2px}
.field{margin-bottom:18px}
.field label{display:block;font-size:12.5px;color:#94a3b8;margin-bottom:7px;font-weight:600}
.field input[type=text],.field textarea,.field select{width:100%;background:#0f1117;border:1px solid #2a3040;border-radius:9px;padding:10px 13px;color:#e2e8f0;font-size:13.5px;font-family:inherit;transition:border-color .15s}
.field select{cursor:pointer;appearance:none;background-image:linear-gradient(45deg,transparent 50%,#64748b 50%),linear-gradient(135deg,#64748b 50%,transparent 50%);background-position:calc(100% - 18px) 50%,calc(100% - 13px) 50%;background-size:5px 5px,5px 5px;background-repeat:no-repeat;padding-right:36px}
.field select option{background:#0f1117;color:#e2e8f0}
.field textarea{resize:vertical;min-height:66px;line-height:1.55}
.field input:focus,.field textarea:focus{outline:none;border-color:#4a9eff}
.field .hint{font-size:11.5px;color:#54627a;margin-top:5px}
.field .count{float:right;color:#54627a;font-weight:400}
/* 开关 */
.toggle-row{display:flex;align-items:center;justify-content:space-between;background:#0f1117;border:1px solid #2a3040;border-radius:9px;padding:12px 14px}
.toggle-row .tl{font-size:13.5px;font-weight:600}
.toggle-row .td{font-size:11.5px;color:#64748b;margin-top:2px}
.switch{position:relative;width:46px;height:25px;flex:none;cursor:pointer}
.switch input{opacity:0;width:0;height:0}
.switch .track{position:absolute;inset:0;background:#2a3040;border-radius:999px;transition:.2s}
.switch .track::after{content:'';position:absolute;left:3px;top:3px;width:19px;height:19px;border-radius:50%;background:#94a3b8;transition:.2s}
.switch input:checked + .track{background:#4a9eff}
.switch input:checked + .track::after{transform:translateX(21px);background:#fff}
/* 形态选择卡片 */
.style-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.style-opt{position:relative;cursor:pointer}
.style-opt input{position:absolute;opacity:0}
.style-opt .box{border:1.5px solid #2a3040;border-radius:11px;padding:12px;transition:.15s;background:#0f1117}
.style-opt input:checked + .box{border-color:#4a9eff;background:rgba(74,158,255,.07)}
.style-opt .box b{font-size:13px;display:block;margin-bottom:8px}
.style-opt .demo{height:26px;border-radius:6px;background:#f8fafc;position:relative;overflow:hidden}
.style-opt .demo i{position:absolute;top:6px;left:8%;width:84%;height:13px;background:linear-gradient(135deg,#00853A,#10B981);display:block}
.style-opt .demo.pill i{border-radius:999px;left:16%;width:68%}
.style-opt .demo.full i{border-radius:0;left:0;width:100%}
.style-opt .box .desc{font-size:11px;color:#64748b;margin-top:8px;line-height:1.5}
/* 按钮 */
.btnrow{display:flex;gap:10px;margin-top:6px}
button{font-family:inherit;cursor:pointer;border:none;border-radius:9px;font-size:13.5px;font-weight:700;padding:11px 18px;transition:.15s}
.btn-save{background:#1d2536;color:#4a9eff;border:1px solid #2f3d57;flex:1}
.btn-save:hover{background:#232d44}
.btn-deploy{background:#4a9eff;color:#fff;flex:1.4}
.btn-deploy:hover{background:#5cabff;box-shadow:0 4px 14px rgba(74,158,255,.3)}
button:disabled{opacity:.45;cursor:not-allowed}
/* 预览 */
.preview-bg{background:#f8fafc;border-radius:11px;padding:0 0 14px;overflow:hidden}
.preview-head{background:#fff;border-bottom:1px solid #e2e8f0;padding:10px 14px;display:flex;align-items:center;gap:7px}
.preview-head .logo-dot{width:18px;height:18px;border-radius:5px;background:linear-gradient(135deg,#00853A,#059669)}
.preview-head span{font-size:12px;font-weight:800;color:#0f172a}
.preview-head small{color:#94a3b8;font-size:10px}
#pvBanner{margin:0;transition:all .25s;background:#0f1117}
#pvBanner.pv-full{padding:0}
#pvInner{display:flex;align-items:center;justify-content:center;gap:8px;margin:8px auto 0;max-width:78%;border-radius:999px;padding:8px 10px 8px 15px;background:linear-gradient(135deg,rgba(0,133,58,.93),rgba(5,150,105,.90) 55%,rgba(16,185,129,.86))}
#pvBanner.pv-full #pvInner{max-width:100%;border-radius:0;margin:0;padding:9px 14px;box-shadow:none}
#pvIcon{font-size:13px;flex:none}
#pvText{font-size:12px;font-weight:500;color:#fff;letter-spacing:.2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#pvClose{flex:none;width:17px;height:17px;border-radius:50%;background:rgba(255,255,255,.16);color:rgba(255,255,255,.9);font-size:10px;display:flex;align-items:center;justify-content:center}
.preview-note{font-size:11px;color:#54627a;margin-top:10px;line-height:1.6}
/* 部署状态 */
.deploy-state{margin-top:14px;padding:12px 14px;border-radius:9px;font-size:12.5px;line-height:1.7;display:none;border:1px solid}
.deploy-state.ok{display:block;color:#4ade80;border-color:rgba(74,222,128,.35);background:rgba(74,222,128,.06)}
.deploy-state.err{display:block;color:#f87171;border-color:rgba(248,113,113,.35);background:rgba(248,113,113,.06)}
.deploy-state.info{display:block;color:#fbbf24;border-color:rgba(251,191,36,.35);background:rgba(251,191,36,.06)}
/* 说明 */
.guide{margin-top:20px;background:#151823;border:1px solid #252b3b;border-radius:14px;padding:18px 22px}
.guide h2{font-size:13px;color:#fbbf24;margin-bottom:12px;display:flex;align-items:center;gap:8px}
.guide h2::before{content:'';width:3px;height:14px;background:#fbbf24;border-radius:2px}
.guide ol{margin-left:18px;font-size:12.5px;color:#94a3b8;line-height:2}
.guide code{background:#0f1117;border:1px solid #2a3040;border-radius:5px;padding:1px 7px;font-family:"SF Mono",Consolas,monospace;font-size:11.5px;color:#7dd3fc}
.toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(80px);background:#1e293b;border:1px solid #334155;color:#fff;padding:11px 22px;border-radius:10px;font-size:13px;z-index:99;opacity:0;transition:.25s;box-shadow:0 8px 24px rgba(0,0,0,.4)}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
@media (max-width:820px){.grid{grid-template-columns:1fr}.topbar{flex-direction:column;align-items:flex-start}}
</style>
</head>
<body>
<div class="wrap">
    <div class="topbar">
        <div>
            <h1><span class="dot"></span>顶部推广横幅 · 运营台</h1>
            <div class="sub">aitoollab.cn · ads/tpb-config.json · 全站 fetch no-store 秒级生效，无需构建</div>
        </div>
        <span id="stateBadge" class="state-badge state-on">显示中</span>
    </div>

    <div class="grid">
        <div class="card">
            <h2>配置编辑</h2>
            <div class="field">
                <div class="toggle-row">
                    <div>
                        <div class="tl">横幅显示</div>
                        <div class="td">关闭 = enabled:false，全站横幅下架（约1秒内生效）</div>
                    </div>
                    <label class="switch"><input type="checkbox" id="fEnabled"><span class="track"></span></label>
                </div>
            </div>
            <div class="field">
                <label>横幅形态</label>
                <div class="style-grid">
                    <label class="style-opt">
                        <input type="radio" name="fStyle" value="pill" checked>
                        <div class="box"><b>💊 胶囊 pill</b><div class="demo pill"><i></i></div><div class="desc">720px 居中悬浮，与站点绿系一体（日常推荐）</div></div>
                    </label>
                    <label class="style-opt">
                        <input type="radio" name="fStyle" value="full">
                        <div class="box"><b>📐 全屏 full</b><div class="demo full"><i></i></div><div class="desc">通栏渐变条，曝光最大化（大促活动用）</div></div>
                    </label>
                </div>
            </div>
            <div class="field">
                <label>广告词 <span class="count" id="textCount">0/100</span></label>
                <textarea id="fText" maxlength="100" placeholder="例：⚡ 新工具上线，限时免费体验 →"></textarea>
                <div class="hint">展示在横幅中央，建议 ≤40 字；带箭头 → 引导点击</div>
            </div>
            <div class="field">
                <label>跳转链接</label>
                <input type="text" id="fUrl" placeholder="https://...">
                <div class="hint">自动带 target=_blank + nofollow noopener，不影响 SEO</div>
            </div>
            <div class="field">
                <label>关闭后多久再显示</label>
                <select id="fCooldown">__COOLDOWN_OPTIONS__</select>
                <div class="hint">用户点 × 后的冷却时间（原先硬编码 24 小时）。文案或链接一旦变更，视为新广告，立即重新显示，不受冷却限制。</div>
            </div>
            <div class="btnrow">
                <button class="btn-save" id="btnSave" onclick="doSave(false)">💾 保存到本地</button>
                <button class="btn-deploy" id="btnDeploy" onclick="doSave(true)">🚀 保存并部署上线</button>
            </div>
            <div id="deployState" class="deploy-state"></div>
        </div>

        <div>
            <div class="card">
                <h2>实时预览（随表单变化）</h2>
                <div class="preview-bg">
                    <div class="preview-head"><div class="logo-dot"></div><span>AI工具宝箱</span><small>每日更新 · 已收录数百款工具</small></div>
                    <div id="pvBanner">
                        <div id="pvInner"><span id="pvIcon">⚡</span><span id="pvText"></span><span id="pvClose">×</span></div>
                    </div>
                </div>
                <div class="preview-note" id="pvNote">预览为示意：线上横幅随 header 粘顶，滚动 80px 自动收起，回顶恢复；用户点 × 后 6 小时内不再显示。</div>
            </div>
            <div class="card" style="margin-top:20px">
                <h2>部署状态</h2>
                <div style="font-size:12.5px;color:#64748b;line-height:2" id="deployMeta">尚未在本次会话部署。部署动作 = scp 上传 ads/tpb-config.json 到服务器 + ssh 回读校验一致性。</div>
            </div>
        </div>
    </div>

    <div class="guide">
        <h2>📘 使用说明</h2>
        <ol>
            <li>「保存到本地」只更新仓库真源 <code>ads/tpb-config.json</code>（自动留 <code>.bak-时间戳</code> 备份），线上暂不生效；</li>
            <li>「保存并部署上线」= 保存 + scp 上传服务器 + ssh 回读校验，全站所有页面 <code>fetch no-store</code> 拉新配置，约 1 秒内生效，<b>无需任何构建</b>；</li>
            <li><b>关闭冷却</b>：用户点 × 后按「关闭后多久再显示」的小时数静默；<b>改文案或链接即视为新广告，立即重新显示</b>（所以改了配置自己刷新就能看到）；</li>
            <li>线上配置 URL 是 <code>/reco/tpb.json</code>（nginx 映射到同一物理文件 <code>ads/tpb-config.json</code>）。<b>不要改回 <code>/ads/</code> 前缀</b>——该前缀命中 uBlock/AdGuard 默认规则，实测约 70% 请求被拦，是"后台改了线上不更新"的老根因；</li>
            <li>前端横幅行为（sticky/滚动收起/关闭记忆/双形态 CSS）由构建注入器 <code>scripts/build_lib/injectors.py</code> 管理，改那里才需要重跑构建；</li>
            <li>SEO 安全：横幅链接固定 nofollow，文案属模板内容，动态替换不影响 SEO/GEO；正文内容不走此通道；</li>
            <li>内页横幅铺开依赖 <code>bash deploy.sh</code> 全量部署（注入器已就位）。</li>
        </ol>
    </div>
</div>
<div class="toast" id="toast"></div>

<script>
var $ = function(id){ return document.getElementById(id); };
var state = { enabled: true, style: 'pill', cooldownHours: 6, text: '', url: '' };

function toast(msg){
  var t = $('toast'); t.textContent = msg; t.classList.add('show');
  setTimeout(function(){ t.classList.remove('show'); }, 2400);
}
function syncPreview(){
  $('pvText').textContent = state.text || '（广告词预览）';
  $('pvBanner').classList.toggle('pv-full', state.style === 'full');
  var badge = $('stateBadge');
  badge.textContent = state.enabled ? '显示中' : '已下架';
  badge.className = 'state-badge ' + (state.enabled ? 'state-on' : 'state-off');
  var note = $('pvNote');
  if (note) {
    var h = Number(state.cooldownHours);
    note.textContent = '预览为示意：线上横幅随 header 粘顶，滚动 80px 自动收起，回顶恢复；用户点 × 后 '
      + (h > 0 ? h + ' 小时' : '不再') + '内不再显示（广告词/链接有变更时立即重新显示）。';
  }
}
function syncCount(){ $('textCount').textContent = $('fText').value.length + '/100'; }
function collect(){
  state.enabled = $('fEnabled').checked;
  state.style = document.querySelector('input[name=fStyle]:checked').value;
  state.cooldownHours = Number($('fCooldown').value);
  state.text = $('fText').value.trim();
  state.url = $('fUrl').value.trim();
}
function fill(cfg){
  state = { enabled: !!cfg.enabled, style: cfg.style === 'full' ? 'full' : 'pill',
            cooldownHours: (cfg.cooldownHours == null ? 6 : Number(cfg.cooldownHours)),
            text: cfg.text || '', url: cfg.url || '' };
  $('fEnabled').checked = state.enabled;
  document.querySelector('input[name=fStyle][value="' + state.style + '"]').checked = true;
  $('fCooldown').value = String(state.cooldownHours);
  $('fText').value = state.text;
  $('fUrl').value = state.url;
  syncPreview(); syncCount();
}
['fText','fUrl'].forEach(function(id){
  $(id).addEventListener('input', function(){ collect(); syncPreview(); if(id==='fText') syncCount(); });
});
$('fCooldown').addEventListener('change', function(){ collect(); syncPreview(); });
document.querySelectorAll('input[name=fStyle]').forEach(function(r){
  r.addEventListener('change', function(){ collect(); syncPreview(); });
});
$('fEnabled').addEventListener('change', function(){ collect(); syncPreview(); });

function setState(el, cls, html){ el.className = 'deploy-state ' + cls; el.innerHTML = html; }

function doSave(alsoDeploy){
  collect();
  if (!state.text) { toast('⚠️ 广告词不能为空'); return; }
  if (!/^https?:\/\//.test(state.url)) { toast('⚠️ 链接必须以 http(s):// 开头'); return; }
  var btn = alsoDeploy ? $('btnDeploy') : $('btnSave');
  var btnText = btn.textContent;
  btn.disabled = true; btn.textContent = '处理中…';
  var st = $('deployState');
  if (alsoDeploy) setState(st, 'info', '⏳ 正在保存并部署（scp → ssh 校验）…');
  fetch('/api/save', { method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify(state) })
  .then(function(r){ return r.json(); })
  .then(function(res){
    if (!res.success) throw new Error(res.errors ? res.errors.join('；') : '保存失败');
    if (!alsoDeploy) { toast('✅ 已保存到本地（线上未生效）'); btn.disabled = false; btn.textContent = btnText; return; }
    return fetch('/api/deploy', { method:'POST' }).then(function(r){ return r.json(); });
  })
  .then(function(res){
    if (!res) return;
    if (res.success) {
      setState(st, 'ok', '✅ ' + res.message + '<br><span style="color:#64748b">' + new Date().toLocaleTimeString() + ' · root@121.43.144.99:/var/www/aitoollab/html/ads/tpb-config.json</span>');
      $('deployMeta').textContent = '上次部署：' + new Date().toLocaleString() + '（校验通过）';
      toast('🚀 部署成功，全站生效');
    } else {
      setState(st, 'err', '❌ ' + (res.message || '部署失败'));
      toast('❌ 部署失败，详见状态区');
    }
  })
  .catch(function(e){
    setState(st, 'err', '❌ ' + (e.message || e));
    toast('❌ 操作失败');
  })
  .finally(function(){ btn.disabled = false; btn.textContent = btnText; });
}

fetch('/api/config').then(function(r){ return r.json(); }).then(fill).catch(function(){ toast('⚠️ 配置加载失败'); });
</script>
</body>
</html>
'''


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # 静默访问日志

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            opts = ''.join(
                '<option value="%d"%s>%s</option>' % (
                    h, ' selected' if h == COOLDOWN_DEFAULT else '',
                    ('%d 小时' % h) if h > 0 else '关闭后仅本次会话不再显示')
                for h in COOLDOWN_CHOICES)
            body = HTML_TEMPLATE.replace('__COOLDOWN_OPTIONS__', opts).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == '/api/config':
            self._json(load_config())
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path == '/api/save':
            try:
                length = int(self.headers.get('Content-Length') or 0)
                cfg = json.loads(self.rfile.read(length).decode('utf-8'))
                cfg = {
                    "enabled": bool(cfg.get('enabled')),
                    "style": cfg.get('style') if cfg.get('style') in VALID_STYLES else 'pill',
                    "cooldownHours": _parse_hours(cfg.get('cooldownHours')),
                    "text": str(cfg.get('text') or '').strip()[:100],
                    "url": str(cfg.get('url') or '').strip(),
                }
                errs = validate(cfg)
                if errs:
                    self._json({"success": False, "errors": errs})
                    return
                save_config(cfg)
                print(f"[tpb] 已保存: enabled={cfg['enabled']} style={cfg['style']} text={cfg['text'][:30]}…")
                self._json({"success": True})
            except Exception as e:
                self._json({"success": False, "errors": [f'保存异常: {e}']})
        elif self.path == '/api/deploy':
            ok, msg = deploy()
            print(f"[tpb] 部署: {'OK' if ok else 'FAIL'} - {msg}")
            self._json({"success": ok, "message": msg})
        else:
            self._json({"error": "not found"}, 404)


def main():
    port = PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print(f'[tpb] 顶部横幅运营台已启动: http://127.0.0.1:{port}')
    print(f'[tpb] 配置文件: {CONFIG_PATH}')
    print(f'[tpb] 部署目标: root@{SERVER_HOST}:{SERVER_PATH}')
    print('[tpb] Ctrl+C 停止')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\n[tpb] 已停止')


if __name__ == '__main__':
    main()
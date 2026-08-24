#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
站点健康自查 + 告警（P3-10）

由 cron 每 5 分钟调用一次（/etc/cron.d/aitoollab-health）：
  1. 检查 https://www.aitoollab.cn/api/health（覆盖 nginx + SSL + 反代 + 助手服务）
     连续失败 3 次 -> 钉钉告警；期间每 30 分钟重复提醒；恢复后发"已恢复"。
  2. 检查 SSL 证书剩余天数（优先读 certbot 本地证书），剩余 <14 天 -> 每天提醒一次。

配置（/etc/aitoollab/health-alert.env，权限 600）：
  DINGTALK_WEBHOOK   钉钉群机器人 Webhook（必填才推送，否则仅本地日志）
  DINGTALK_SECRET    可选：机器人加签密钥（勾选"加签"时填）
  HEALTH_CHECK_URL   默认 https://www.aitoollab.cn/api/health
  SSL_CERT_FILE      默认自动探测 certbot 证书路径
  STATE_FILE         默认 /var/www/aitoollab/data/health_alert_state.json
  LOG_FILE           默认 /var/www/aitoollab/logs/health_alert.log

零第三方依赖，Python 3.6+。
"""

from __future__ import print_function

import base64
import hashlib
import hmac
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request


def _load_env(path):
    out = {}
    try:
        with io.open(path, 'r', encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, _, v = line.partition('=')
                out[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


_ENV = {}
for _p in ('/etc/aitoollab/health-alert.env', '/etc/aitoollab/ai-assistant.env'):
    _ENV.update(_load_env(_p))


def _cfg(name, default=None):
    return os.environ.get(name) or _ENV.get(name) or default


WEBHOOK = (_cfg('DINGTALK_WEBHOOK') or '').strip()
SECRET = (_cfg('DINGTALK_SECRET') or '').strip()
CHECK_URL = _cfg('HEALTH_CHECK_URL', 'https://www.aitoollab.cn/api/health')
CERT_FILE = (_cfg('SSL_CERT_FILE') or '').strip()
STATE_FILE = _cfg('STATE_FILE', '/var/www/aitoollab/data/health_alert_state.json')
LOG_FILE = _cfg('LOG_FILE', '/var/www/aitoollab/logs/health_alert.log')

FAIL_THRESHOLD = 3          # 连续失败次数达到后告警
REALERT_SECONDS = 1800      # 持续故障时每 30 分钟重复提醒
SSL_WARN_DAYS = 14          # 证书剩余天数阈值
SSL_DAILY_ALERT = True      # 证书告警每天最多一次

_CERT_CANDIDATES = (
    '/etc/letsencrypt/live/www.aitoollab.cn/cert.pem',
    '/etc/letsencrypt/live/aitoollab.cn/cert.pem',
    '/etc/ssl/certs/ssl-cert-snakeoil.pem',
)


def _find_openssl():
    for cand in (
        shutil.which('openssl'),
        '/usr/bin/openssl',
        'C:/Program Files/Git/usr/bin/openssl.exe',
        'C:/Program Files/Git/bin/openssl.exe',
    ):
        if cand and os.path.isfile(cand):
            return cand
    return 'openssl'


_OPENSSL = _find_openssl()


def log_event(evt):
    try:
        d = os.path.dirname(LOG_FILE)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        with io.open(LOG_FILE, 'a', encoding='utf-8') as fh:
            evt['ts'] = time.strftime('%Y-%m-%d %H:%M:%S')
            fh.write(json.dumps(evt, ensure_ascii=False) + '\n')
    except Exception:
        pass


def load_state():
    try:
        with io.open(STATE_FILE, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_state(st):
    try:
        d = os.path.dirname(STATE_FILE)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        with io.open(STATE_FILE, 'w', encoding='utf-8') as fh:
            json.dump(st, fh, ensure_ascii=False)
        try:
            os.chmod(STATE_FILE, 0o600)
        except OSError:
            pass
    except Exception:
        pass


def check_health():
    """返回 (ok, detail)。detail 用于告警文案。"""
    req = urllib.request.Request(CHECK_URL, headers={'User-Agent': 'health-alert/1.0'})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        code = resp.status
        raw = resp.read(4096).decode('utf-8', errors='replace')
        try:
            obj = json.loads(raw)
            ok = bool(obj.get('ok'))
        except ValueError:
            ok = False
        detail = 'HTTP %s, ok=%s' % (code, ok)
        return (code == 200 and ok), detail
    except Exception as e:
        return False, '请求失败: %s' % str(e)[:120]


def _cert_path():
    if CERT_FILE and os.path.isfile(CERT_FILE):
        return CERT_FILE
    for p in _CERT_CANDIDATES:
        if os.path.isfile(p):
            return p
    return None


def parse_notafter(text):
    """解析 openssl -enddate 输出，返回 (datetime, days_left)"""
    m = re.search(r'notAfter=([^\n\r]+)', text or '')
    if not m:
        return None, None
    try:
        import datetime
        # 兼容 'MMM DD HH:MM:SS YYYY GMT' 与 'YYYY-MM-DD HH:MM:SS GMT' 两种格式
        s = m.group(1).strip()
        dt = None
        for fmt in ('%b %d %H:%M:%S %Y %Z', '%Y-%m-%d %H:%M:%S %Z'):
            try:
                dt = datetime.datetime.strptime(s, fmt)
                break
            except ValueError:
                continue
        if dt is None:
            return None, None
        days = (dt - datetime.datetime.utcnow()).days
        return dt, days
    except Exception:
        return None, None


def check_ssl_days():
    """返回 (notafter_str, days_left) 或 (None, None)。"""
    path = _cert_path()
    if path:
        try:
            out = subprocess.check_output(
                [_OPENSSL, 'x509', '-enddate', '-noout', '-in', path],
                stderr=subprocess.STDOUT,
            ).decode('utf-8', errors='replace')
            dt, days = parse_notafter(out)
            return (dt.strftime('%Y-%m-%d') if dt else None), days
        except Exception:
            pass
    # 兜底：走 s_client 拉取线上证书
    try:
        import ssl
        import socket
        host = CHECK_URL.split('://', 1)[-1].split('/')[0].split(':')[0]
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
        not_after = cert.get('notAfter', '')
        dt, days = parse_notafter('notAfter=' + not_after)
        return (dt.strftime('%Y-%m-%d') if dt else not_after), days
    except Exception as e:
        log_event({'check': 'ssl', 'ok': False, 'detail': '证书检查失败: %s' % str(e)[:120]})
        return None, None


def _sign_url(webhook, secret):
    ts = str(int(time.time() * 1000))
    string_to_sign = '%s\n%s' % (ts, secret)
    digest = hmac.new(
        secret.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        hashlib.sha256,
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(digest))
    sep = '&' if '?' in webhook else '?'
    return webhook + sep + 'timestamp=' + ts + '&sign=' + sign


def send_dingtalk(text):
    """发送钉钉文本消息；返回 'sent' / 'noop' / 'failed'。"""
    if not WEBHOOK:
        log_event({'action': 'alert', 'ok': False, 'detail': '未配置 DINGTALK_WEBHOOK，仅记录日志'})
        return 'noop'
    url = _sign_url(WEBHOOK, SECRET) if SECRET else WEBHOOK
    body = json.dumps({'msgtype': 'text', 'text': {'content': text}}).encode('utf-8')
    last_err = ''
    for attempt in range(2):
        try:
            req = urllib.request.Request(
                url,
                data=body,
                headers={'Content-Type': 'application/json'},
            )
            resp = urllib.request.urlopen(req, timeout=10)
            raw = resp.read(1024).decode('utf-8', errors='replace')
            obj = json.loads(raw) if raw else {}
            if obj.get('errcode') == 0:
                return 'sent'
            last_err = 'errcode=%s errmsg=%s' % (obj.get('errcode'), obj.get('errmsg'))
        except Exception as e:
            last_err = str(e)[:120]
        time.sleep(2)
    log_event({'action': 'alert', 'ok': False, 'detail': '钉钉发送失败: %s' % last_err})
    return 'failed'


def main():
    if '--test' in sys.argv:
        r = send_dingtalk('【站点告警】测试消息：AI工具宝箱 健康告警链路正常 ✓（本条为手动测试，可忽略）')
        print('test send result: %s' % r)
        return 0 if r == 'sent' else 1

    st = load_state()
    st.setdefault('health_fails', 0)
    st.setdefault('down_alerted', False)
    st.setdefault('last_down_alert_ts', 0)
    st.setdefault('last_ssl_alert_date', '')
    st.setdefault('last_ssl_days', None)

    # ---- 1. 健康检查 ----
    ok, detail = check_health()
    log_event({'check': 'health', 'ok': ok, 'detail': detail})
    if ok:
        if st['down_alerted']:
            send_dingtalk('【站点告警】AI工具宝箱 已恢复正常，健康检查通过 ✓')
        st['health_fails'] = 0
        st['down_alerted'] = False
        st['last_down_alert_ts'] = 0
    else:
        st['health_fails'] = st.get('health_fails', 0) + 1
        if (st['health_fails'] >= FAIL_THRESHOLD
                and (not st['down_alerted']
                     or time.time() - st['last_down_alert_ts'] >= REALERT_SECONDS)):
            now = time.time()
            msg = ('【站点告警】AI工具宝箱 健康检查连续失败 %d 次\n'
                   '检查地址：%s\n'
                   '错误：%s\n'
                   '时间：%s'
                   % (st['health_fails'], CHECK_URL, detail,
                      time.strftime('%Y-%m-%d %H:%M:%S')))
            send_dingtalk(msg)
            st['down_alerted'] = True
            st['last_down_alert_ts'] = now

    # ---- 2. SSL 证书剩余天数 ----
    not_after, days = check_ssl_days()
    st['last_ssl_days'] = days
    today = time.strftime('%Y-%m-%d')
    if days is not None and days < SSL_WARN_DAYS:
        if st.get('last_ssl_alert_date') != today:
            msg = ('【站点告警】AI工具宝箱 SSL 证书将于 %s 到期（剩余 %d 天），'
                   '请检查 certbot 自动续签是否正常。'
                   % (not_after or '未知', days))
            send_dingtalk(msg)
            st['last_ssl_alert_date'] = today
            log_event({'check': 'ssl', 'ok': True,
                       'detail': '证书剩余 %d 天，已发送告警' % days})
    elif days is not None:
        st['last_ssl_alert_date'] = ''

    save_state(st)
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aitoollab TTS 服务（独立进程，不依赖 AI 助手）
- 端点: GET /tts?text=...&voice=zh-CN-XiaoxiaoNeural
- 模块: edge-tts (微软神经网络语音, 免费)
- 缓存: 同 (text, voice) 合成结果落盘 MP3, 避免重复合成
- 安全: text 长度限制 + 仅允许中文相关 voice, 防滥用
运行: uv run uvicorn tts_server:app --host 127.0.0.1 --port 8088
"""
import os
import hashlib
import asyncio
import logging
from pathlib import Path

import edge_tts
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("tts")

CACHE_DIR = Path(os.environ.get("TTS_CACHE_DIR", "/opt/aitoollab-tts/cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 允许的语音白名单（微软中文神经网络语音，免费档）
ALLOWED_VOICES = {
    "zh-CN-XiaoxiaoNeural",   # 女声（默认，最自然）
    "zh-CN-YunxiNeural",      # 男声
    "zh-CN-YunjianNeural",    # 男声（沉稳）
    "zh-CN-XiaoyiNeural",     # 女声（温柔）
    "zh-CN-XiaohanNeural",    # 女声
    "zh-CN-XiaomengNeural",   # 女声（甜美）
    "zh-CN-YunyangNeural",    # 男声（新闻）
}
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
MAX_TEXT_LEN = 2000  # 单段上限，前端按段落切分

app = FastAPI(title="aitoollab TTS", version="1.0.0")


def _cache_key(text: str, voice: str) -> str:
    h = hashlib.sha256(f"{voice}::{text}".encode("utf-8")).hexdigest()
    return h


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/tts")
async def tts(
    text: str = Query(..., min_length=1, max_length=MAX_TEXT_LEN),
    voice: str = Query(DEFAULT_VOICE),
):
    if voice not in ALLOWED_VOICES:
        raise HTTPException(status_code=400, detail=f"voice not allowed: {voice}")
    if len(text.strip()) == 0:
        raise HTTPException(status_code=400, detail="empty text")

    key = _cache_key(text, voice)
    mp3 = CACHE_DIR / f"{key}.mp3"

    # 缓存命中校验：文件存在且非空（>=500字节），防止合成中断残留的0字节空文件污染缓存
    if not mp3.exists() or mp3.stat().st_size == 0:
        # 先写临时文件，成功后再原子 rename，避免中断留下半成品/空文件
        if mp3.exists() and mp3.stat().st_size == 0:
            mp3.unlink(missing_ok=True)
        tmp = mp3.with_suffix(".tmp")
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(tmp))
            if tmp.stat().st_size == 0:
                tmp.unlink(missing_ok=True)
                raise RuntimeError("edge-tts returned empty audio")
            tmp.replace(mp3)  # 原子替换，确保缓存里永远是可用的文件
        except Exception as e:  # noqa: BLE001
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            log.exception("edge-tts failed")
            raise HTTPException(status_code=502, detail=f"tts synthesis failed: {e}")

    # 2026-08-23 修复：FileResponse 会对 Range 请求返回 206，经 nginx 反代后
    # Content-Range 头被剥掉 → 浏览器 <audio> 播放失败（进度条不显示）。
    # 改为始终返回 200 完整文件，由 nginx 的 range filter 负责切片（其生成的
    # Content-Range 头正确），audio 播放/进度条恢复正常。
    return Response(
        content=mp3.read_bytes(),
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-store", "X-TTS-Voice": voice},
    )


@app.get("/tts/voices")
async def voices():
    return {"default": DEFAULT_VOICE, "voices": sorted(ALLOWED_VOICES)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8088)

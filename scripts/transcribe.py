"""
下載一集節目的音檔並轉錄成文字稿 (speech-to-text)。

用 faster-whisper（開源、免費、可在 GitHub Actions 的 CPU runner 上跑），
避免每天都要付費呼叫語音辨識 API。缺點是速度比雲端 API 慢一些，
一集 30 分鐘的節目用 base model 大約要 15-30 分鐘處理。

如果之後想換成更快/更準的雲端服務（例如 OpenAI Whisper API），
只要改寫這個檔案裡的 transcribe_audio() 就好，其他腳本不用動。
"""
import shutil
import uuid
from pathlib import Path

import requests
from faster_whisper import WhisperModel

import config

_MODEL = None  # 延遲載入，避免只是 import 這個檔案就觸發下載模型


def _get_model() -> WhisperModel:
    global _MODEL
    if _MODEL is None:
        # int8 量化在 CPU 上明顯比較快，準確度差異對「摘要用途」可以接受
        _MODEL = WhisperModel(config.WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    return _MODEL


def download_audio(audio_url: str) -> Path:
    config.AUDIO_TMP_DIR.mkdir(parents=True, exist_ok=True)
    dest = config.AUDIO_TMP_DIR / f"{uuid.uuid4().hex}.mp3"
    with requests.get(audio_url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            shutil.copyfileobj(resp.raw, f)
    return dest


def transcribe_audio(audio_path: Path) -> dict:
    """
    回傳:
        {
            "text": 完整逐字稿（無時間戳），
            "segments": [{"start": 秒數, "end": 秒數, "text": "..."}],
            "language": 偵測到的語言代碼,
        }
    """
    model = _get_model()
    segments_iter, info = model.transcribe(
        str(audio_path),
        beam_size=5,
        vad_filter=True,  # 過濾靜音/雜訊，減少幻覺文字
    )

    segments = []
    full_text_parts = []
    for seg in segments_iter:
        text = seg.text.strip()
        if not text:
            continue
        segments.append({"start": round(seg.start, 1), "end": round(seg.end, 1), "text": text})
        full_text_parts.append(text)

    return {
        "text": " ".join(full_text_parts),
        "segments": segments,
        "language": info.language,
    }


def transcribe_episode(audio_url: str) -> dict:
    """下載並轉錄一集節目，結束後清掉暫存音檔。"""
    audio_path = download_audio(audio_url)
    try:
        return transcribe_audio(audio_path)
    finally:
        audio_path.unlink(missing_ok=True)


def _fmt_ts(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def build_transcript_markdown(segments: list[dict], chunk_seconds: float = 30.0) -> str:
    """
    把帶時間戳的逐字稿片段，整理成原始英文全文的 Markdown 區塊（每隔約 chunk_seconds
    秒插入一個時間戳記，把中間的片段接成一段，避免每個 whisper 小片段各自一行、
    讀起來太破碎）。這段內容不經過 AI 改寫，是 faster-whisper 辨識出來的原文。
    """
    if not segments:
        return ""

    lines = ["## 📜 英文逐字稿全文（English Transcript）", ""]
    chunk_start = segments[0]["start"]
    chunk_texts: list[str] = []

    for seg in segments:
        if chunk_texts and (seg["start"] - chunk_start) >= chunk_seconds:
            lines.append(f"**[{_fmt_ts(chunk_start)}]** " + " ".join(chunk_texts))
            lines.append("")
            chunk_start = seg["start"]
            chunk_texts = []
        chunk_texts.append(seg["text"])

    if chunk_texts:
        lines.append(f"**[{_fmt_ts(chunk_start)}]** " + " ".join(chunk_texts))

    return "\n".join(lines)

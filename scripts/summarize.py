"""
把逐字稿丟給 Claude API，整理成結構化的繁體中文筆記
(格式參考 https://yasac.substack.com 的「股癌自動筆記」排版方式)。
"""
import json

import anthropic

import config


def _format_transcript_for_prompt(segments: list[dict], max_chars: int = 60000) -> str:
    """把帶時間戳的逐字稿片段組成給模型看的純文字，超長就均勻抽樣避免超過 context。"""
    lines = [f"[{_fmt_ts(s['start'])}] {s['text']}" for s in segments]
    joined = "\n".join(lines)
    if len(joined) <= max_chars:
        return joined
    # 太長時，保留開頭/結尾完整，中間等距抽樣，避免整段被硬切斷在句子中間
    head = lines[: len(lines) // 4]
    tail = lines[-len(lines) // 4 :]
    middle = lines[len(lines) // 4 : -len(lines) // 4 : 2]
    return "\n".join(head + ["\n...（中間內容為節錄）...\n"] + middle + tail)


def _fmt_ts(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


SYSTEM_PROMPT = """\
你是一個專門把英文新聞 podcast 逐字稿整理成繁體中文（台灣用語）重點筆記的編輯。
輸出必須是「可以直接發布的筆記全文」，用 Markdown 格式，語氣專業但好讀，不要加任何開場白或跟使用者的對話，
不要說「以下是整理」之類的話，直接輸出筆記本身。

請照這個結構輸出：

# {集數標題}

📝 **這一集在說什麼**
（2-4 句話的整體概述，讓讀者 10 秒內知道這集值得不值得聽）

📰 **重點新聞**
針對逐字稿中每一個獨立新聞主題，各自用以下格式：
### [時間戳] 主題標題
內容摘要（3-6 句話，含關鍵事實、人物、數字、地點）

（大約 3-8 個主題，依逐字稿實際內容決定數量，不要硬湊）

🔍 **背景補充 / 值得注意的點**
（1-3 點你認為讀者可能需要的背景知識或觀察，沒有就省略這節）

如果有提供「附上英文學習重點」的指示，最後再加一節：
📖 **英文學習筆記**
從逐字稿中挑 5-8 個對中階英文學習者實用的單字/片語，格式：
- **word/phrase** — 中文解釋（原句節錄，英文）

全文請用繁體中文（台灣用語，例如「影片」不是「视频」），專有名詞、人名、地名第一次出現時英文原文用括號附註。
"""


def summarize_episode(title: str, published: str, transcript: dict) -> str:
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("缺少 ANTHROPIC_API_KEY，請在環境變數 / GitHub Secrets 設定後再執行。")

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    transcript_text = _format_transcript_for_prompt(transcript["segments"])
    vocab_instruction = (
        "請附上「英文學習筆記」小節。" if config.INCLUDE_VOCAB_SECTION else "不需要附上英文學習筆記小節。"
    )

    user_prompt = f"""\
節目：{config.PODCAST_DISPLAY_NAME}
集數標題：{title}
發布時間：{published}
{vocab_instruction}

逐字稿（含時間戳，單位為 mm:ss 或 hh:mm:ss）：
---
{transcript_text}
---

請依照系統指示的結構，輸出這一集的繁體中文重點筆記。
"""

    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    return "\n".join(parts).strip()


if __name__ == "__main__":
    import sys

    payload = json.loads(sys.stdin.read())
    note = summarize_episode(payload["title"], payload["published"], payload["transcript"])
    print(note)

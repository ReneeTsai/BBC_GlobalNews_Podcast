"""
抓來源 podcast 的 RSS feed，比對 data/seen_episodes.json，找出還沒處理過的新集數。

用法:
    python scripts/fetch_new_episodes.py
輸出:
    印出一個 JSON list 到 stdout，每個元素是一集新節目的資訊，供 run_pipeline.py 使用。
"""
import json
import sys
from email.utils import parsedate_to_datetime

import feedparser
import config


def load_seen_guids() -> set:
    if not config.SEEN_EPISODES_FILE.exists():
        return set()
    try:
        data = json.loads(config.SEEN_EPISODES_FILE.read_text(encoding="utf-8"))
        return set(data.get("seen_guids", []))
    except (json.JSONDecodeError, OSError):
        return set()


def save_seen_guids(guids: set) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.SEEN_EPISODES_FILE.write_text(
        json.dumps({"seen_guids": sorted(guids)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _entry_audio_url(entry) -> str | None:
    """從 RSS entry 裡找出音檔的實際網址 (通常在 enclosure)。"""
    for link in getattr(entry, "links", []):
        if link.get("rel") == "enclosure" and "audio" in link.get("type", ""):
            return link.get("href")
    # 有些 feed 只有一個 enclosures 欄位
    for enc in getattr(entry, "enclosures", []):
        if "audio" in enc.get("type", ""):
            return enc.get("href")
    return None


def _entry_pubdate_iso(entry) -> str:
    raw = getattr(entry, "published", None) or getattr(entry, "updated", None)
    if not raw:
        return ""
    try:
        return parsedate_to_datetime(raw).isoformat()
    except (TypeError, ValueError):
        return raw


def fetch_new_episodes(max_episodes: int | None = None) -> list[dict]:
    feed = feedparser.parse(config.PODCAST_RSS_URL)
    if feed.bozo and not feed.entries:
        raise RuntimeError(f"無法解析 RSS feed: {config.PODCAST_RSS_URL} ({feed.bozo_exception})")

    seen = load_seen_guids()
    # RSS 通常新的在前面；由舊到新處理，讓 feed.xml 的發布順序比較自然
    entries = list(reversed(feed.entries))

    new_episodes = []
    for entry in entries:
        guid = getattr(entry, "id", None) or getattr(entry, "link", None)
        if not guid or guid in seen:
            continue
        audio_url = _entry_audio_url(entry)
        if not audio_url:
            # 沒有音檔的項目（例如公告類）直接跳過，但仍標記為已讀，避免每次重新檢查
            seen.add(guid)
            continue
        new_episodes.append(
            {
                "guid": guid,
                "title": getattr(entry, "title", "(無標題)"),
                "audio_url": audio_url,
                "published": _entry_pubdate_iso(entry),
                "summary_source": getattr(entry, "summary", ""),
            }
        )

    if max_episodes is not None:
        new_episodes = new_episodes[-max_episodes:]

    # 把本次「決定跳過」的（沒有音檔的）先存檔，避免重複判斷；真正處理完的集數由 run_pipeline 事後標記
    save_seen_guids(seen)
    return new_episodes


if __name__ == "__main__":
    episodes = fetch_new_episodes(max_episodes=config.MAX_EPISODES_PER_RUN)
    json.dump(episodes, sys.stdout, ensure_ascii=False, indent=2)

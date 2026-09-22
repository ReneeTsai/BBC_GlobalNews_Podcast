"""
整條流水線的入口，GitHub Actions 每天會執行這支腳本：

  1. fetch_new_episodes  -> 找出還沒處理過的新集數
  2. transcribe           -> 下載音檔、轉成逐字稿
  3. summarize             -> 用 Claude 整理成中文筆記
  4. build_feed             -> 產生 episode 頁面 + 更新 feed.xml / index.html
  5. 把這一集標記為「已處理」寫回 data/seen_episodes.json

單一集失敗不會讓整批中斷：失敗就印出錯誤、跳過這一集，留到下次排程重試
（因為失敗的集數不會被標記為已處理）。
"""
import json
import sys
import traceback

import config
import fetch_new_episodes as fe
import transcribe as tr
import summarize as sm
import build_feed as bf


def mark_processed(guid: str) -> None:
    seen = fe.load_seen_guids()
    seen.add(guid)
    fe.save_seen_guids(seen)


def process_episode(ep: dict) -> bool:
    print(f"[處理中] {ep['title']} ({ep['published']})")
    transcript = tr.transcribe_episode(ep["audio_url"])
    print(f"  轉錄完成，共 {len(transcript['segments'])} 段，語言：{transcript['language']}")

    note_markdown = sm.summarize_episode(ep["title"], ep["published"], transcript)
    print("  摘要完成")

    bf.build_all(
        new_item={
            "guid": ep["guid"],
            "title": ep["title"],
            "published": ep["published"],
            "note_markdown": note_markdown,
            "source_link": ep["audio_url"],
        }
    )
    print("  已更新 feed.xml / index.html")

    mark_processed(ep["guid"])
    return True


def main() -> int:
    try:
        episodes = fe.fetch_new_episodes(max_episodes=config.MAX_EPISODES_PER_RUN)
    except Exception:
        print("抓取 RSS feed失敗：", file=sys.stderr)
        traceback.print_exc()
        return 1

    if not episodes:
        print("沒有新集數，結束。")
        return 0

    print(f"發現 {len(episodes)} 集新節目")
    success_count = 0
    for ep in episodes:
        try:
            if process_episode(ep):
                success_count += 1
        except Exception:
            print(f"[失敗，跳過，下次排程會重試] {ep['title']}", file=sys.stderr)
            traceback.print_exc()

    print(f"完成，成功處理 {success_count}/{len(episodes)} 集")
    return 0 if success_count > 0 or len(episodes) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

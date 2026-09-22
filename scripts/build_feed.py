"""
把已經產生好的筆記，組成：
  1. 每一集一個 HTML 頁面 (docs/episodes/xxx.html)
  2. 一份給 RSS reader 訂閱的 docs/feed.xml
  3. 一個簡單的 docs/index.html 目錄頁

這三個檔案都在 docs/ 底下，對應 GitHub Pages 設定成「從 main branch 的 /docs 資料夾部署」。
"""
import html
import json
import re
from datetime import datetime, timezone
from email.utils import format_datetime

import markdown as md

import config

PUBLISHED_INDEX_FILE = config.DATA_DIR / "published_episodes.json"


def _slugify(guid: str, title: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9]+", "-", title).strip("-").lower()
    base = base[:60] if base else "episode"
    short_hash = str(abs(hash(guid)) % 100000)
    return f"{base}-{short_hash}"


def load_published_index() -> list[dict]:
    if not PUBLISHED_INDEX_FILE.exists():
        return []
    try:
        return json.loads(PUBLISHED_INDEX_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_published_index(items: list[dict]) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    PUBLISHED_INDEX_FILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )


EPISODE_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} | {feed_title}</title>
<style>
  body {{ font-family: -apple-system, "Noto Sans TC", sans-serif; max-width: 720px; margin: 40px auto; padding: 0 20px; line-height: 1.75; color: #222; }}
  h1 {{ font-size: 1.5rem; }}
  h3 {{ margin-top: 1.6em; }}
  .meta {{ color: #888; font-size: 0.9rem; margin-bottom: 2em; }}
  a.back {{ display: inline-block; margin-bottom: 1.5em; }}
  blockquote {{ border-left: 3px solid #ddd; margin-left: 0; padding-left: 1em; color: #555; }}
</style>
</head>
<body>
<a class="back" href="../index.html">&larr; 回筆記列表</a>
<div class="meta">{published_display} ・ 來源：{podcast_name}</div>
{body_html}
</body>
</html>
"""

INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{feed_title}</title>
<link rel="alternate" type="application/rss+xml" title="{feed_title}" href="feed.xml">
<style>
  body {{ font-family: -apple-system, "Noto Sans TC", sans-serif; max-width: 720px; margin: 40px auto; padding: 0 20px; line-height: 1.6; color: #222; }}
  h1 {{ font-size: 1.6rem; }}
  p.desc {{ color: #555; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ padding: 14px 0; border-bottom: 1px solid #eee; }}
  li a {{ font-weight: 600; text-decoration: none; color: #1a1a1a; }}
  li .date {{ color: #888; font-size: 0.85rem; }}
  .rss-link {{ display: inline-block; margin-top: 10px; font-size: 0.9rem; }}
</style>
</head>
<body>
<h1>{feed_title}</h1>
<p class="desc">{feed_description}</p>
<a class="rss-link" href="feed.xml">📡 訂閱 RSS feed</a>
<ul>
{items}
</ul>
</body>
</html>
"""


def render_episode_html(item: dict) -> str:
    body_html = md.markdown(item["note_markdown"], extensions=["extra"])
    return EPISODE_PAGE_TEMPLATE.format(
        title=html.escape(item["title"]),
        feed_title=html.escape(config.OUTPUT_FEED_TITLE),
        published_display=item["published"][:10] if item["published"] else "",
        podcast_name=html.escape(config.PODCAST_DISPLAY_NAME),
        body_html=body_html,
    )


def build_all(new_item: dict | None = None) -> None:
    """
    new_item（若提供）會被加入已發布清單，然後重新產生 index.html / feed.xml / 該集的 html 頁面。
    new_item 格式: {guid, title, published (ISO8601 str), note_markdown, source_link}
    """
    items = load_published_index()

    if new_item is not None:
        slug = _slugify(new_item["guid"], new_item["title"])
        new_item = {**new_item, "slug": slug}
        items = [i for i in items if i["guid"] != new_item["guid"]] + [new_item]
        items.sort(key=lambda i: i.get("published") or "")

    config.EPISODES_DIR.mkdir(parents=True, exist_ok=True)
    config.DOCS_DIR.mkdir(parents=True, exist_ok=True)

    # 只保留最新 N 篇在 feed.xml / index.html，但已發布過的 html 頁面全部保留（舊連結不失效）
    for item in items:
        page_html = render_episode_html(item)
        (config.EPISODES_DIR / f"{item['slug']}.html").write_text(page_html, encoding="utf-8")

    recent_items = list(reversed(items))[: config.MAX_ITEMS_IN_FEED]

    _write_index_html(recent_items)
    _write_feed_xml(recent_items)
    save_published_index(items)


def _write_index_html(recent_items: list[dict]) -> None:
    li_html = "\n".join(
        f'<li><a href="episodes/{i["slug"]}.html">{html.escape(i["title"])}</a><br>'
        f'<span class="date">{i["published"][:10] if i["published"] else ""}</span></li>'
        for i in recent_items
    )
    content = INDEX_TEMPLATE.format(
        feed_title=html.escape(config.OUTPUT_FEED_TITLE),
        feed_description=html.escape(config.OUTPUT_FEED_DESCRIPTION),
        items=li_html or "<li>目前還沒有筆記，等第一次排程執行後就會出現。</li>",
    )
    config.INDEX_OUTPUT_FILE.write_text(content, encoding="utf-8")


def _rfc822(iso_str: str) -> str:
    if not iso_str:
        return format_datetime(datetime.now(timezone.utc))
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return format_datetime(dt)
    except ValueError:
        return format_datetime(datetime.now(timezone.utc))


def _write_feed_xml(recent_items: list[dict]) -> None:
    base = config.SITE_BASE_URL.rstrip("/")
    items_xml = []
    for i in recent_items:
        link = f"{base}/episodes/{i['slug']}.html"
        # description 用轉成 HTML 後的筆記全文，讓大部分 RSS reader 可以直接閱讀（像參考的 substack 網站一樣）
        description_html = md.markdown(i["note_markdown"], extensions=["extra"])
        items_xml.append(
            f"""  <item>
    <title>{_xml_escape(i['title'])}</title>
    <link>{html.escape(link)}</link>
    <guid isPermaLink="false">{_xml_escape(i['guid'])}</guid>
    <pubDate>{_rfc822(i['published'])}</pubDate>
    <description><![CDATA[{description_html}]]></description>
  </item>"""
        )

    feed_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>{_xml_escape(config.OUTPUT_FEED_TITLE)}</title>
  <link>{html.escape(base)}/index.html</link>
  <description>{_xml_escape(config.OUTPUT_FEED_DESCRIPTION)}</description>
  <language>{config.OUTPUT_FEED_LANGUAGE}</language>
  <lastBuildDate>{format_datetime(datetime.now(timezone.utc))}</lastBuildDate>
{chr(10).join(items_xml)}
</channel>
</rss>
"""
    config.FEED_OUTPUT_FILE.write_text(feed_xml, encoding="utf-8")


def _xml_escape(s: str) -> str:
    return html.escape(s, quote=True)


if __name__ == "__main__":
    build_all()
    print(f"已重新產生 {config.FEED_OUTPUT_FILE} 與 {config.INDEX_OUTPUT_FILE}")

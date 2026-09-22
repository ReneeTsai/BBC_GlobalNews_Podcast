"""
共用設定值。要換成別的 podcast，改 PODCAST_RSS_URL 跟下面幾個名稱/顏色即可。
"""
import os
from pathlib import Path

# ------------------------------------------------------------------
# 來源 podcast
# ------------------------------------------------------------------
PODCAST_RSS_URL = "https://podcasts.files.bbci.co.uk/p02nq0gn.rss"
PODCAST_DISPLAY_NAME = "BBC Global News Podcast"

# 每次最多處理幾集新節目（避免第一次執行時因為「全部都是新的」被巨量任務淹沒）
MAX_EPISODES_PER_RUN = int(os.environ.get("MAX_EPISODES_PER_RUN", "3"))

# ------------------------------------------------------------------
# 你自己輸出的 feed 相關設定
# ------------------------------------------------------------------
# 部署到 GitHub Pages 後，這個 repo 對外的網址（設定完 Pages 後改成實際網址）
# 例如: https://yourname.github.io/bbc-podcast-notes
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://REPLACE_ME.github.io/bbc-podcast-notes")

OUTPUT_FEED_TITLE = "BBC Global News 每日中文筆記"
OUTPUT_FEED_DESCRIPTION = "自動擷取 BBC Global News Podcast 最新集數，轉錄並用 AI 整理成中文重點筆記。"
OUTPUT_FEED_LANGUAGE = "zh-tw"
OUTPUT_FEED_AUTHOR = "Rachel"

# feed.xml 最多保留幾則最新集數（避免 feed 檔案無限增長）
MAX_ITEMS_IN_FEED = int(os.environ.get("MAX_ITEMS_IN_FEED", "60"))

# ------------------------------------------------------------------
# 轉錄 (speech-to-text) 設定
# ------------------------------------------------------------------
# faster-whisper 模型大小: tiny / base / small / medium
# base 在 GitHub Actions 的免費 CPU runner 上，處理 30 分鐘節目大約 15-30 分鐘，準確度足夠拿來摘要
WHISPER_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "base")

# ------------------------------------------------------------------
# 摘要 (Claude API) 設定
# ------------------------------------------------------------------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5")

# 是否在筆記裡附上英文單字/片語小整理（給英文學習用）
INCLUDE_VOCAB_SECTION = os.environ.get("INCLUDE_VOCAB_SECTION", "true").lower() == "true"

# ------------------------------------------------------------------
# 路徑
# ------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DOCS_DIR = PROJECT_ROOT / "docs"
EPISODES_DIR = DOCS_DIR / "episodes"
AUDIO_TMP_DIR = PROJECT_ROOT / ".tmp_audio"
SEEN_EPISODES_FILE = DATA_DIR / "seen_episodes.json"
FEED_OUTPUT_FILE = DOCS_DIR / "feed.xml"
INDEX_OUTPUT_FILE = DOCS_DIR / "index.html"

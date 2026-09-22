# BBC Global News Podcast → 每日中文筆記 RSS

自動把 [BBC Global News Podcast](https://podcasts.apple.com/us/podcast/global-news-podcast/id135067274)
的最新集數：抓取 → 轉錄逐字稿 → 用 Claude 整理成繁體中文重點筆記 → 產生一份你自己的 RSS feed，
讓你可以直接用 RSS reader（Feedly、NetNewsWire、Reeder…）訂閱，天天自動更新，不用手動做任何事。

運作方式跟開頭提到的 `yasac.substack.com`（股癌自動筆記）概念一樣，只是：
- 來源換成 BBC Global News Podcast（可自行換成別的 podcast，見下方「換成別的 podcast」）
- 輸出不是發到 Substack，而是產生一份純 RSS feed + 靜態網頁，架在你自己的 GitHub Pages 上
- 全部用免費服務：GitHub Actions（排程執行）+ GitHub Pages（免費架站）+ faster-whisper（免費開源語音辨識）
  唯一要花錢的是 Claude API 的摘要費用，一集大約幾分錢台幣等級，一個月抓 30 集大概落在幾十到一百多元台幣

---

## 整體架構

```
每天 GitHub Actions 排程觸發
  → fetch_new_episodes.py   抓 BBC RSS，找出還沒處理過的新集數
  → transcribe.py           下載音檔，用 faster-whisper 轉逐字稿（免費，跑在 GitHub 的伺服器上）
  → summarize.py            把逐字稿丟給 Claude API，整理成中文筆記
  → build_feed.py           產生 docs/episodes/xxx.html + 更新 docs/feed.xml 和 docs/index.html
  → git commit + push       把新檔案存回 repo
GitHub Pages 自動把 docs/ 部署成網站，feed.xml 就是你的訂閱網址
```

---

## 第一次設定步驟

### 1. 建立 GitHub repo
把這個資料夾整個上傳成一個 **public** repo（public 才能用 GitHub Actions 的免費無限額度；
private repo 也可以，只是每月有 2000 分鐘免費額度上限）。

```bash
cd bbc-podcast-notes
git init
git add .
git commit -m "初始化 podcast 筆記自動化"
git branch -M main
git remote add origin https://github.com/<你的帳號>/bbc-podcast-notes.git
git push -u origin main
```

### 2. 申請 Claude API Key
到 https://console.anthropic.com 建立一組 API key（跟你平常用的 claude.ai 是不同系統，
API 是另外計費的，需要先加值一點額度，一個月的用量成本非常低）。

### 3. 設定 GitHub Secrets 和 Variables
到 repo 頁面 → **Settings → Secrets and variables → Actions**：

- **Secrets** 分頁 → New repository secret
  - Name: `ANTHROPIC_API_KEY`
  - Value: 你剛剛申請的 key
- **Variables** 分頁 → New repository variable
  - Name: `SITE_BASE_URL`
  - Value: `https://<你的帳號>.github.io/bbc-podcast-notes`（下一步啟用 Pages 後就是這個網址）

### 4. 啟用 GitHub Pages
到 repo 頁面 → **Settings → Pages**：
- Source 選擇 `Deploy from a branch`
- Branch 選 `main`，資料夾選 `/docs`
- 存檔後，GitHub 會給你一個網址，格式通常是 `https://<你的帳號>.github.io/bbc-podcast-notes/`
  （跟上一步填的 `SITE_BASE_URL` 要一致）

### 5. 手動跑第一次，確認整條流程沒問題
到 repo 頁面 → **Actions** 分頁 → 左邊選「每日更新 podcast 筆記」→ 右邊 **Run workflow** 按鈕，手動觸發一次。
第一次執行預設只會處理**最新 3 集**（`config.py` 裡的 `MAX_EPISODES_PER_RUN`，可自行調整），
避免一次要處理過去全部集數。

跑完之後（通常十幾到幾十分鐘，看有幾集要處理），檢查：
- Actions 頁面那次執行是綠色打勾
- `docs/feed.xml` 有被 commit 進 repo
- 打開 `https://<你的帳號>.github.io/bbc-podcast-notes/` 看得到筆記列表

### 6. 訂閱
把 `https://<你的帳號>.github.io/bbc-podcast-notes/feed.xml` 貼到任何 RSS reader 訂閱，之後每天就會自動收到新筆記。

---

## 之後就完全自動

`.github/workflows/daily.yml` 設定成每天 UTC 23:00（台北時間早上 07:00）自動執行一次，
抓 BBC 當時最新、還沒處理過的集數（BBC Global News Podcast 一天會發好幾集，
之後每次執行都只處理「上次執行後新出的」，不會重複）。要改時間就改那個 `cron` 那一行。

---

## 換成別的 podcast

想追別的節目，只要換 `scripts/config.py` 最上面幾行：

```python
PODCAST_RSS_URL = "換成目標 podcast 的 RSS 網址"
PODCAST_DISPLAY_NAME = "節目名稱"
```

找一個節目的 RSS 網址，最快的方法是在 Apple Podcasts 找到節目頁，
用線上工具（例如搜尋「podcast rss finder」）貼節目連結轉換，或直接問我，我可以幫你查。

---

## 成本 / 效能備註

- **轉錄 (faster-whisper, base model)**：免費，但跑在 GitHub Actions 的共用 CPU 上，
  一集 30 分鐘節目大約需要 15-30 分鐘處理時間。如果之後想要更快更準，
  可以把 `scripts/transcribe.py` 換成呼叫 OpenAI Whisper API 或其他雲端語音辨識服務（約 US$0.006/分鐘）。
- **摘要 (Claude API)**：一集約消耗 1-2 萬 tokens，用 `claude-sonnet-4-5` 大約幾分錢台幣，
  想再省可以在 `config.py` 把 `CLAUDE_MODEL` 換成更便宜的 haiku 系列模型。
- **架站 (GitHub Pages)**：完全免費。

---

## 檔案結構

```
bbc-podcast-notes/
├── scripts/
│   ├── config.py              所有設定值都在這
│   ├── fetch_new_episodes.py  抓 RSS、比對已處理清單
│   ├── transcribe.py          下載音檔 + faster-whisper 轉錄
│   ├── summarize.py           呼叫 Claude API 整理成中文筆記
│   ├── build_feed.py          產生 feed.xml / index.html / 單集頁面
│   └── run_pipeline.py        串起以上所有步驟，GitHub Actions 執行的入口
├── data/
│   ├── seen_episodes.json     已經檢查過的 RSS guid（避免重複判斷）
│   └── published_episodes.json 已發布筆記的完整清單（feed.xml 的資料來源）
├── docs/                      GitHub Pages 網站根目錄
│   ├── index.html
│   ├── feed.xml
│   └── episodes/*.html
├── .github/workflows/daily.yml  每日排程設定
└── requirements.txt
```

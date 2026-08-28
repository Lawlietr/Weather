# 🌦 Weather — 台灣天氣與災情總覽

紀錄颱風動態與災情的 Markdown 倉儲，並以 build 腳本產出**純靜態網站**，已上線 Cloudflare Pages（自訂域名，主要通道）＋ GitHub Pages：

> 🌐 <https://weather.avpclub.eu.org/>（繁中）｜<https://weather.avpclub.eu.org/ja/>（日文）
> 其他端點：<https://weather.avpclub.uk/>、<https://weather.larch.dpdns.org/>、<https://lawlietr.github.io/Weather/>（同一份內容）

本站採**手動更新**、非即時，每頁標示「最後更新時間」。

## 專案組成

1. **災情／颱風紀錄**（`颱風/`、`災情/`）：以結構化 Markdown 記錄每個天氣事件，一篇一檔。
   撰寫規則與檔名規範見 `AGENTS.md`。
2. **靜態網站**（`build/` → `public/`）：build 腳本讀取本倉 Markdown 紀錄、本機抓取中央氣象署公開資料，
   產出零外部請求的靜態站。

## 網站功能

- **事件為中心**：首頁 Hero 顯示目前 `active` 事件（災情、影響縣市、最新進展）；過去事件降級為封存列表（archive）。
- **氣象總覽**（CWA Open Data API，build 時本機抓取）：
  - 颱風動態：靜態 SVG 軌跡圖＋15 m/s 風圈＋未來預報表
  - 警報與特報（海上颱風警報、豪雨／強風特報）
  - 雨量觀測站 TOP 10
- **多語言**：繁體中文（預設，根目錄）＋ 日文（`/ja/`）；UI 字串收斂於 `build/i18n.py`，
  事件正文與 CWA 資料保留原文。
- **輕量離線**：首頁零 JS、無外部 JS/CSS/追蹤、無地圖 CDN；日夜主題；mobile-first；
  全相對路徑，部署於任何子路徑皆可。
- **LLM 友善**：build 同時產出 [`llms.txt`](https://weather.avpclub.eu.org/llms.txt)（站點索引＋事件清單）
  與 `llms-full.txt`（全部事件全文），供 AI 助手直接讀取本站內容。
- **優雅降級**：CWA 抓取失敗時以本機快取舊值＋警示呈現，build 不中斷；「無法取得」與「無資料」視覺區分。

## 快速開始

```bash
# 0. 確認環境有 CWA_API_KEY（設定方式見 AGENTS.md；金鑰不可 commit）
# 1. build（自動建 venv；唯一相依：markdown）
./build/build.sh

# 2. 本機預覽
cd public && python3 -m http.server 8080
# → http://localhost:8080        繁中
# → http://localhost:8080/ja/    日文
```

## 目錄結構

```
weather/
├── AGENTS.md         # 專案規範：檔案規則、CWA API 優先級、網站設計原則
├── build/CWA_API.md  # CWA 逐 dataset 欄位查表（解析 CWA 資料前讀）
├── WORKFLOW.md       # Runbook：更新／build／驗證／部署逐步流程（接手先看）
├── TODO.md           # 未完成待辦（RSS 抓取、地圖標註）
├── README.md         # 本檔案
├── LICENSE           # 程式碼授權：GNU AGPLv3
├── LICENSE-CONTENT   # 內容授權：CC BY-NC-SA 4.0（災情紀錄與網頁產出）
├── 颱風/             # 颱風紀錄：颱風/{YYYY}/{MM}/{MMDD}_{NN}_{中文名}_{國際命名}.md
├── 災情/             # 非颱風災情：災情/{YYYY}/{MM}/{MMDD}_{事件類型}_{事件名稱}.md
├── build/            # build 腳本（site.py / cwa.py / i18n.py）；cwa_cache.json 已 gitignore
└── public/           # build 產出（已 gitignore）：根目錄＝繁中、ja/＝日文、llms.txt／llms-full.txt
```

## 資料來源

| 內容 | 來源 |
|------|------|
| 颱風軌跡／強度／警報特報／雨量 | [CWA Open Data API](https://opendata.cwa.gov.tw/)（優先級見 `AGENTS.md`，欄位查表見 `build/CWA_API.md`） |
| 災情紀錄（淹水、樹倒、停電等） | 本倉 Markdown，每筆附新聞來源與日期 |
| 停班停課、交通影響 | 教育部、各縣市政府、交通部公告（記錄於事件內文） |

## 安全原則

- **CWA API Key** 只存在本機執行環境：不寫進 build 輸出、不進任何 repo。
- **公開 GitHub repo 只放 `public/` 靜態產物**：Markdown 原文、build 腳本、內部倉庫資訊一律不公開（部署流程見 `WORKFLOW.md` §6）。

## 授權（雙授權）

- **程式碼**（`build/` 等）：[GNU AGPLv3](LICENSE)
- **內容**（`災情/`、`颱風/` 紀錄及其網頁／`llms.txt`／`llms-full.txt` 產出）：
  [CC BY-NC-SA 4.0（創用 CC 姓名標示-非商業性-相同方式分享）](LICENSE-CONTENT)
  ——可自由分享與調修，但須註明出處、**不得商用**、衍生作品須以相同授權釋出。
- 源自 CWA Open Data API 的氣象資料以中央氣象署官方條款為準，不為本專案授權範圍。

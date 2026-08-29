# Weather - 台灣天氣與災情總覽

紀錄颱風動態與災情的 Markdown 倉儲，並附靜態網站 build（產出 `public/`、`llms.txt`、`llms-full.txt`；主要 host 於 Cloudflare Pages 自訂域名，另同步 GitHub Pages；見下方「網站專案」）。

## ⚠️ 時間意識（極度重要）

**撰寫或查詢災情前，必須先確認目前的現實時間（系統時間）。**

- 本項目核心目的是**記錄目前正在發生的天氣事件**與即時災情彙整
- 搜尋與引用新聞時，**只關注當前事件相關的最新報導**，不應檢索上個月或幾年前的事件
- 檔案中的時間戳必須與現實時間一致，不可混淆年份或日期
- 若搜尋結果出現非當前事件的歷史資料，應主動過濾，避免將過去的事件誤植到當前紀錄中
- 每次新增災情前，先確認該災情是否屬於「目前正在發生」的颱風事件

## 目錄與檔名

### 颱風檔案

```
颱風/{YYYY}/{MM}/{MMDD}_{NN}_{中文名}_{國際命名}.md
```

範例：`颱風/2026/07/0702_09_巴威_BAVI.md`

**說明**：
- `{MMDD}`：生成日期（月 + 日，補零，如 0702 表示 7 月 2 日）
- `{NN}`：颱風編號（補零，如 09 表示第 9 號）**⚠️ 此編號為 CWA 熱帶氣旋編號（非 JTMA 國際編號）**，請以 CWA API W-C0034-005 回傳之 `CwaTdNo` 為準。檔名使用 CWA 編號可確保與網站「氣象總覽」區塊一致。
- 這樣命名可確保檔案按日期和編號自然排序

### 災情檔案（非颱風事件）

```
災情/{YYYY}/{MM}/{MMDD}_{事件類型}_{事件名稱}.md
```

範例：`災情/2026/08/0821_低壓帶_南台灣大雨.md`

**說明**：
- `{MMDD}`：事件起始日期（月 + 日，補零）
- `事件類型`：低壓帶、西南風、梅雨等
- `事件名稱`：簡明描述事件影響範圍
- 適用範圍：非颱風造成的災害（低壓帶、梅雨、西南風等）

## 颱風編號規範

**⚠️ 所有颱風編號一律以 CWA 熱帶氣旋編號（`CwaTdNo`）為準，不使用 JTMA 國際編號。**

- 檔名 `{NN}`、front matter `event:`、基本資料表「編號」欄位、警報時程引用——**全部使用 CWA 編號**
- 檔名仍可保留 JTMA 編號於 `_` 後（如 `0818_20_沙德爾_SAUDEL.md`），但 `event:` 標題必須寫 CWA 編號
- 原因：CWA API 回傳 `CwaTdNo`，與 JTMA 編號不一致（例：沙德爾 = JTMA 第 18 號，CWA 第 20 號）
- 若 CWA API 尚未分配編號（剛生成為 TD 時），可先寫 JTMA 編號並加註待補

## 檔案撰寫規則

- 全部使用**繁體中文**
- 時間戳須含年與時間，如 `2026/7/10 05:30`
- 災害分級標籤：`🔴重大` `🟡警戒` `🟢一般`——事件的**歷史**分級，手動指派，事件結束後**不降級**；首頁頂部「目前風險狀態列」另行由 CWA 目前警報/特報自動推導，兩者獨立（見 `WORKFLOW.md` §2.2）
- 新進展**附加**在檔尾，不覆寫；僅在結構錯誤時修改既有內容
- 颱風基本資料表（強度、風速、半徑等）置於檔首，使用表格
- **檔首只保留一筆** `最後修改：YYYY/M/D HH:mm`（置於基本資料表上方）：每次修改時**原地更新該行**，**不要新增行**（舊慣例已廢，事件頁會把所有堆疊行都渲染出來）；歷史時間戳由 git history 保存。重要變更可在同一行以括號註記，例如 `最後修改：2026/7/11 18:30（status 改為 ended）`

## 章節慣例

### 颱風檔案

依序：基本資料 → 警報時程 → 停班停課 → 風力/雨量/浪高 → 災情紀錄（依 🔴🟡🟢 分節）→ 交通影響 → 防災作為 → 備註

### 災情檔案（非颱風事件）

依序：災害概述 → 各縣市災情 → 停班停課時程 → 氣象署警報與特報 → 中央災害應變中心 → 專家分析 → 災情分級 → 未來天氣預報 → 備註 → 資料來源

## 資料來源規範

- **颱風資料**（軌跡、強度、位置、預測）：以中央氣象署（CWA）API 為主
- **警報與特報**（海上颱風警報、大雨特報、強風特報）：以 CWA API 為主
- **雨量、風力、浪高**：以 CWA API 為主
- **災情紀錄**（淹水、樹倒、落石、停電等）：以各縣市新聞媒體為輔，引用時請註明出處
- **停班停課**：以教育部或各縣市政府公告為主
- **交通影響**：以交通部或各縣市政府公告為主，新聞媒體為輔
- **災情來源優先級（build）**：repo 現有 `災情/` markdown → **RSS** → Obscura 抓取。每筆附**新聞來源**，僅給**少量摘要＋原連結**。

> ⚠️ 使用新聞資料時，請確認時效性，避免使用舊聞；引用時請註明新聞來源與日期。

## 新聞 RSS 來源

- **一律先讀 `build/rss_sources.json`** 取得來源清單（`sources` 8 家已實測可用；`failed_sources` 失效**勿呼叫**；`usage_notes` 為完整抓取守則），不要自行重新查或寫死 URL。
- 重點：解析器需相容 `rss20`（`<item>`）與 `atom`（`<entry>`，公視是 Atom）；LTN feed 檔頭有 BOM；**民報域名是 `peoplenews.tw`（非 `minmax.tw`）**；單一來源 404/超時**不中斷 build**（跳過＋記 warning）。
- **風傳媒（storm.mg）待復查**：RSS 疑似移除，但它是颱風/災情最重要新媒體之一；取不到時退而用 Obscura 抓其新聞頁。

## Git

- 預設分支：`main`（原 `master` 已更名）
- 功能開發在 `DEV` 分支，**經使用者確認後才合併回 `main`**
- 無 lint/test 指令；GitHub Actions 僅保留 `workflow_dispatch`（手動觸發，2026/8/29 起停用排程，原因見下方說明）；自動更新改由本地 cron 備用（`build/cron-enable.sh`）

### ⚠️ GitHub Actions 狀態（2026/8/29 起僅手動 dispatch）

GitHub Actions **已停用排程**（移除 `schedule`），僅保留 `workflow_dispatch`（手動觸發）。
停用原因：Actions runner（Azure `westus2`）到 CWA API 連線不穩定，導致 build 使用舊資料
卻仍部署到 CF Pages（`wrangler pages deploy` 只上傳 `public/`，不檢查資料新舊）。

若需手動跑 Actions build：到 GitHub repo 頁面 → Actions tab → "Build & Deploy" → "Run workflow"。

> 本地 cron 備用（`build/cron-enable.sh`）為主要自動更新通道；cron 執行前會先檢查 CWA
> 可用性（3 次重試），失敗則中止部署，不會推舊資料。

**若 Actions 排程日後要恢復**：確認 CWA API 可從海外連線（或改用 Cloudflare Worker 等中轉），
再把 `schedule` 加回 `.github/workflows/build.yml` 即可。

---

## 中央氣象署（CWA）Open Data API

⭐ **逐 dataset 欄位查表**（結構、呼叫範例、Python 範例、實測差異）：**`build/CWA_API.md`**——解析資料前讀它。

### API Key

以環境變數 `CWA_API_KEY` 讀取（已設在 `~/.zshrc`；也可放專案 `.env`，已 gitignore）。**不得硬編碼或 commit 到 Git**；程式用 `os.getenv("CWA_API_KEY")` 讀取。

### Base URL

```
https://opendata.cwa.gov.tw/api/v1/rest/datastore/{Data ID}?Authorization=${CWA_API_KEY}&format=JSON
```

### API 優先級說明（依事件類型）

| 優先級 | 颱風事件 | 豪雨/大雨事件（非颱風） |
|--------|----------|--------------------------|
| **P0（必須）** | W-C0034-005（軌跡）、W-C0034-001（海警） | W-C0033-002/003（豪大雨特報）、O-A0002-001（雨量站） |
| **P1（重要）** | W-C0033-001（強風特報）、W-C0033-003、O-A0001-001（逐時氣象） | W-C0033-001（強風特報）、O-A0001-001（逐時氣象）、C-B0025-001（每日雨量）、F-D0047-xxx（鄉鎮預報） |
| **P2（輔助）** | F-C0032-001、F-D0047-xxx、F-A0021-001（潮汐） | C-B0024-001（30天觀測）、C-B0074-001/002（測站基本資料）、F-C0032-001、F-A0021-001（潮汐） |

> 完整官方清單（80 筆，2026/8/25 核對）見 `https://opendata.cwa.gov.tw/apidoc/v1`（OpenAPI YAML）。舊資料中常見但**已不存在**（404）的 Data ID：O-A0013~19（逐時/3h/24h 雨量）、F-C0033-001（48h 雨量預報）、F-C0034-001、F-A0045-001（降雨雷達）、W-C0024-001、F-C0040-001（土石流）、O-C0010-001（河川水位）——開放資料平台無這些產品，需改抓 CWA 官網頁面（obscura）或新聞。

### ⚠️ 關鍵陷阱（實測）

1. O-A0001-001 / O-A0002-001 的 `Now.Precipitation` 是**本日 0 時至目前累計**（**非** 1 小時雨量）；1 小時雨量用 O-A0002-001 的 `Past1hr`。
2. CWA 回傳結構**與官方文件不同**（如 W-C0034-005 多一層 `TropicalCyclone[]`、移動欄位是 `MovingSpeed/MovingDirection`）：改解析碼前**先 dump 真實回傳**，勿照舊文件猜。對照見 `build/CWA_API.md`「實測差異」與 `WORKFLOW.md` §5。
3. **O-B0075-001（48 小時海況）回傳空 JSON**（2026/8/25 實測）；海況改看 CWA 官網頁面或新聞。
4. **CWA API 不支援 CORS**（回應無 `Access-Control-Allow-Origin`）：前端無法直接呼叫，氣象資料必須本機 build 時抓取後寫入靜態 HTML。
5. **更新頻率**：颱風警報每 3~6 小時、氣旋資料每 6 小時；建議每 30~60 分鐘查詢一次即可。
6. **W-C0034-005 forecast 欄位可能為 None**（2026/8/29 實測）：`MaxWindSpeed`、`Pressure` 等 forecast 資料可能回傳 `null`，解析時**必須做 `None` 檢查**，不可直接格式化。例：`_num(fx.get("MaxWindSpeed"))` 回傳 `None` 時，`f"{None:.1f}"` 會崩潰。正確寫法：`f"{f'{ws:.1f}' if ws is not None else '—'}"`。

資料集清單權威來源：`https://opendata.cwa.gov.tw/apidoc/v1`（OpenAPI YAML，含全部 80 個 Data ID、參數與枚舉值）；web 版資料清單頁為 SPA，直接爬 HTML 拿不到清單。

---

## Obscura 無頭瀏覽器

用於爬取 API 沒有的 JavaScript 渲染頁面（如 CWA 官網頁面）。**工具本身的使用說明見 skill `/root/.pi/agent/skills/obscura/SKILL.md`**（binary `/usr/local/bin/obscura`，Docker 容器 `obscura`，MCP HTTP port 3000）。repo 相關：

- **CWA 頁面**：颱風頁在 `P/Typhoon/`——`TY_WARN.html`（警報狀態）、`TY_NEWS.html`（路徑潛勢預報）、`TY_WIND.html`（強風告警）；舊路徑 `Typhoon.html` 已移除。
- 首頁 `https://www.cwa.gov.tw/V8/C/` 有 SVG JS 錯誤（`getTotalLength is not a function`），不影響主要內容。
- 多語句 JS 需包 IIFE：`(function(){ ... })()`。
- SSRF 保護會阻擋 private network，需加 `--allow-private-network`。
- Docker 容器未運行時：`docker run -d --name obscura -p 3000:3000 h4ckf0r0day/obscura mcp --http --port 3000 --host 0.0.0.0`

---

## 網站專案（已上線：Cloudflare Pages `weather.*` 自訂域名 ×3 ＋ GitHub Pages https://lawlietr.github.io/Weather/）

- **更新/部署工作流（runbook）**：`WORKFLOW.md`——接手者（agent 或人工）先看這個。
- **⚠️ 更新災情前先看 `WORKFLOW.md` §8「Agent 效率規範」**：先查 repo 既有檔案／`ctx_search`／`cwa_cache.json`，只查會變的資料，同一資料一個 session 只查一次。
- **構想與待辦**：`TODO.md`。
- **build 入口**：`./build/build.sh`（產出 `public/`（繁中）與 `public/ja/`（日文）、`llms.txt`（LLM 索引）與 `llms-full.txt`（事件全文）；CWA 資料 build 時本機抓取）。
  公開網站主要 host 於 Cloudflare Pages（自訂域名），另同步 GitHub Pages；彙整氣象署天氣資訊與災情紀錄。
- **颱風軌跡圖台灣輪廓**：`build/cwa.py` 的 `typhoon_svg()` 不再用手寫多邊形，改用 `build/taiwan_geo.py` 的 `ISLANDS`（本島＋澎湖／金門／馬祖／蘭嶼／綠島各自獨立 polygon）。產生器 `build/make_taiwan_geo.py`（含純 Python Douglas–Peucker 簡化，無相依）重跑後會覆寫 `taiwan_geo.py`；原始 GeoJSON 快取 `build/_geo_cache_*.json` 已 gitignore。

### 多語言（i18n）

- 預設語言 **zh-Hant**（`public/` 根目錄）、第二語言 **ja**（`public/ja/`）；頁首有語言切換。
- 所有 UI 字串收斂在 `build/i18n.py`（`STRINGS` 表＋`t()` 三級回退）；**加新語言＝在 `STRINGS` 加一組 dict**，不改模板。
- **內容不翻譯**：事件 Markdown 正文、CWA 資料（颱風名、雨量站名、特報全文）全語言保留中文原文；非預設語言頁面以 `content_note` / `cwa_data_note` 提示。

### 核心原則

- **混合更新**：平常由 **本地 cron**（`build/deploy-cron.sh`，每 2 小時，由 `build/cron-enable.sh` 安裝）自動 build＋部署；cron 執行前會檢查 CWA 可用性（3 次重試，失敗中止），並寫入 `build/logs/` 日誌。Actions 僅保留 `workflow_dispatch`（手動觸發，2026/8/29 起停用排程）。災情新聞仍需人工把關，**不自動推 RSS**。
- **金鑰管理**：CWA API Key、Cloudflare 憑證同時存在多處：(1) **本機環境**（手動 build/deploy，`~/.zshrc`）；(2) **GitHub Actions Secrets**（手動 dispatch 用，加密儲存）；(3) **`build/deploy.env`**（本地 cron 用，gitignore、600，由 `deploy-cron.sh` 載入；cron 不載入 `.zshrc`）。全程**不寫進任何輸出檔案、不進 `public/`、不進網站**。
- **非即時**：Pages 為靜態託管，採手動 build。首頁必須顯示「**產生時間**」（i18n key `updated`），由 `build/site.py` 以**固定 UTC+8 台灣時間**產生（`datetime.now(timezone(timedelta(hours=8)))`）；**不可改回不帶時區的 `datetime.now()`**（Actions runner 是 UTC，會慢 8 小時，見 `WORKFLOW.md` §5）。用「產生時間」而非「最後更新」：它只代表網頁何時生成，**不等於氣象／災情資料已更新**。
- **授權僅針對網站專案**（2026/8/28 修正）：公開網站之程式碼以 **GNU AGPLv3**（`LICENSE`）、內容（網頁、`llms.txt`、`llms-full.txt` 之災情紀錄與彙整文字）以 **CC BY-NC-SA 4.0**（`LICENSE-CONTENT`，不得商用）；**倉儲本身**（`build/` 腳本、`災情/`、`颱風/` Markdown 原文、文件）**不以此兩授權釋出**；CWA 資料以官方條款為準。
- **LLM 友善產出**：build 必產 `llms.txt`（站點＋事件索引）與 `llms-full.txt`（全部事件繁中全文），canonical base URL 為 `https://weather.avpclub.eu.org`（`build/site.py` 之 `SITE_BASE`）。

### 技術架構

```
本地 cron（主力，每 2 小時）
  ├── 載入 build/deploy.env（金鑰，gitignore、600）
  ├── CWA 檢查（3 次重試，失敗中止）
  ├── 讀 repo 災情 markdown → 災情資料
  ├── 呼叫 CWA API → 氣象彙整（typhoon_svg 繪製 build/taiwan_geo.py 輪廓）
  ├── build 出靜態 HTML（含「產生時間」）
  ├── wrangler pages deploy public → Cloudflare Pages（主要，公開）
  └── orphan gh-pages 分支 force push → GitHub Pages（備用 mirror）
  └── 全程寫入 build/logs/deploy-cron-YYYY-MM-DD.log
GitHub Actions（手動 dispatch，備援）
  ├── CWA_API_KEY / CLOUDFLARE_* 來自 GitHub Secrets
  └── 同上 build + 部署流程
本機（手動）：`./build/deploy.sh`（流程同上，金鑰取自本機環境）
Cloudflare 靜態託管提供公開網站
```

### 網站結構

- **首頁**：頂部「目前風險狀態列」（`build/cwa.py: current_risk_level()` 由 CWA 目前之熱帶氣旋/海上颱風警報/災害天氣特報自動推導，紅/黃/綠，與事件 `severity` 無關）→ 氣象彙整（颱風軌跡/警報特報/雨量/風力）→ 事件 Hero（中性入口卡，無 severity 色系與徽章）＋ 各縣市災情總覽（依縣市分組，每組內按時間倒序，最新在最上）→ 過去事件封存（含 severity 徽章）。
- **各縣市子頁（選用）**：該縣市災情按時間倒序。

### 部署與分支

- **內部仓库**：`ssh://fg/lawliet/Weather.git`（Forgejo，內網 `192.168.1.124:222`，SSH Host `fg`，Identity `~/.ssh/id_rsa_gitea`）。
- **GitHub**：`https://github.com/Lawlietr/Weather`，**已設為公開**（2026/8/27，原私有，後改公開）。開發與 commit **同時推到 Forgejo 與 GitHub**（保持同步）。build 腳本、`災情/` Markdown 原文、金鑰（存於 Actions Secrets）現存於此 repo。
- **GitHub Pages**：**已轉為公開**（2026/8/27，隨 repo 轉公開），且目前為 **404**（備用 mirror，非必需）。GitHub Actions 已把預設分支設為 `main`（原 orphan `gh-pages` 為預設分支，導致 Actions 看不到 workflow），`gh-pages` 分支因此不再自動重建、Pages 設定回 404。若日後想救回 GitHub Pages，需把預設分支改回 `gh-pages`（代價：Actions 按鈕又會藏起來，需在 Actions 頁面手動切 `main`）。只推 `public/` 靜態產物（orphan `gh-pages` 分支、不共享 history）。部署步驟見 `WORKFLOW.md` §6。
  - ⚠️ 公開網站已改由 **Cloudflare Pages** 提供；GitHub Pages 僅作 mirror，**以 Cloudflare 為主**，404 不影響公開使用。
- **Cloudflare Pages**（公開，2026/8/26 已上線，**主要更新通道兼公開網站**）：專案 `weather`，自訂域名 `weather.avpclub.eu.org`、`weather.avpclub.uk`、`weather.larch.dpdns.org`（CNAME 已建、proxied、自動 HTTPS）。更新只需 `npx wrangler pages deploy public --project-name weather`（憑證在 `~/.zshrc` 或 GitHub Actions Secrets，不進 repo）。細節見 `WORKFLOW.md` §6。

# Weather - 台灣天氣與災情總覽

紀錄颱風動態與災情的 Markdown 倉儲，並附靜態網站 build（產出 `public/`、`llms.txt`、`llms-full.txt`；主要 host 於 Cloudflare Pages 自訂域名，另同步 GitHub Pages；見下方「網站專案」）。

## ⚠️ 時間意識（極度重要）

**撰寫或查詢災情前，必須先確認目前的現實時間（系統時間）。**

- 本項目核心目的是**記錄目前正在發生的天氣事件**與即時災情彙整
- 搜尋與引用新聞時，**只關注當前事件相關的最新報導**，不應檢索上個月或幾年前的事件
- 檔案中的時間戳必須與現實時間一致，不可混淆年份或日期
- 若搜尋結果出現非當前事件的歷史資料，應主動過濾，避免將過去的事件誤植到當前紀錄中
- 每次新增災情前，先確認該災情是否屬於「目前正在發生」的颱風事件

## ⚠️ 網路搜尋（極度重要）

**使用 `web_search` 時，不要硬編碼 `provider` 參數。**

- 預設應省略 `provider` 參數，讓工具自動使用 `/web-tools` 設定的預設引擎（SearXNG）
- 若硬編碼 `provider: "brave"` 而環境沒有 Brave API key，搜尋會失敗
- 若需要特定 provider，應先確認該 provider 的 key 是否存在
- 常見配置：SearXNG（免 key）、Brave（需 key）等

## ⚠️ 颱風檔案建立門檻（極度重要）

**專案核心目的是「記錄對台灣有影響的天氣事件與災情」，不是追蹤所有太平洋颱風。**

- **只有當颱風「可能影響台灣」時，才建立颱風檔案**
- 建立條件（符合任一即可）：
  1. CWA 已發布海上颱風警報
  2. CWA 預報路徑可能影響台灣（進入 70% 暴風半徑範圍）
  3. 颱風外圍環流已對台灣造成明顯影響（大雨特報、強風特報、交通中斷等）
  4. 新聞報導明確指出該颱風對台灣有間接影響（如西南風水氣、東北風降雨等）
- **不建檔案的情況**：
  - 颱風生成後直接遠離台灣（如科羅旺，預報路徑完全遠離）
  - CWA 明確表示「對台無影響」
  - 颱風在海上減弱消散，未接近台灣
  - 純粹的學術追蹤價值，無實際災害或影響
- 若颱風起初可能影響後來確定不影響（如沙德爾第一次接近後遠離）：保留檔案，更新 `status` 與分析
- 若颱風起初不影響後來轉向可能影響（罕見）：可新建檔案
- **不確定時：寧可不建，也不要建無意義的檔案**

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
- **系統減弱後再增強（復活）不重新計號**：CWA 沿用同一 `CwaTdNo`（例：沙德爾 9/1 於南海重新升格仍為 20 號）→ **同一檔案**更新，`status` 改回 `active`，流程見 `WORKFLOW.md` §2.2

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
- **災防告警區**（大雷雨/颱風強風/山區暴雨/巨浪，含官方影響區域 polygon、細胞廣播狀態）：以 CWA cbph API（`cbph.cwa.gov.tw/api/`，免 key、build 時抓取）為主；欄位與陷阱見下方「CWA cbph 災防告警 API」節
- **雨量、風力、浪高**：以 CWA API 為主
- **災情紀錄**（淹水、樹倒、落石、停電等）：以各縣市新聞媒體為輔，引用時請註明出處
- **停班停課**：以教育部或各縣市政府公告為主
- **交通影響**：以交通部或各縣市政府公告為主，新聞媒體為輔
- **措辭跟隨來源、不自行解讀（2026/9/1 定）**：對路徑、強度、登陸與對台影響的判斷性表述，一律引來源原話（CWA API 數值、CWA 發言人/公告口吻），**不得加「二次登陸」「直接侵台」等推測性升級詞**——以 CWA 當時路徑為準（例：9/1 沙德爾返回時 CWA 預測登陸廣東、口徑為「直接侵台機會低」，就照此寫；CWA 修訂路徑後再更新）。
- **災情來源優先級（build）**：repo 現有 `災情/` markdown → **RSS** → Obscura 抓取。每筆附**新聞來源**，僅給**少量摘要＋原連結**。
- **RSS 半自動流程**：build 時 `build/rss.py` 自動抓 `rss_sources.json` 的 verified 來源，產出候選清單 `build/rss_candidates.json`（gitignored；**從不進 `public/`**）。相關性判斷**由人 / LLM 審查**，挑中者以 `- [標題](URL) — 媒體名` 寫入事件檔「XX災情新聞來源」章節才上線。流程與驗證見 `WORKFLOW.md` §1/§3。

> ⚠️ 使用新聞資料時，請確認時效性，避免使用舊聞；引用時請註明新聞來源與日期。

## 新聞 RSS 來源

- **一律先讀 `build/rss_sources.json`** 取得來源清單（`sources` 8 家已實測可用；`failed_sources` 失效**勿呼叫**；`usage_notes` 為完整抓取守則），不要自行重新查或寫死 URL。
- 重點：解析器需相容 `rss20`（`<item>`）與 `atom`（`<entry>`，公視是 Atom）；LTN feed 檔頭有 BOM；**民報域名是 `peoplenews.tw`（非 `minmax.tw`）**；單一來源 404/超時**不中斷 build**（跳過＋記 warning）。
- **風傳媒（storm.mg）待復查**：RSS 疑似移除（2026/8/30 再測仍回 HTML/404），但它是颱風/災情最重要新媒體之一；取不到時退而用 Obscura 抓其新聞頁。

## Git

- 預設分支：`main`（原 `master` 已更名）
- Remotes：`origin`＝內部 Forgejo（`ssh://fg/lawliet/Weather.git`，內網，Identity `~/.ssh/id_rsa_gitea`）；`github`＝公開 repo `Lawlietr/Weather`（SSH `git@github.com:Lawlietr/Weather.git`，key `id_ed25519_github`，直推即可、**不需要 `GH_PAT`**）。commit 後**兩邊都推**：`git push origin <branch> && git push github <branch>`
- 功能開發在 `DEV` 分支，**經使用者確認後才合併回 `main`**
- 無 lint/test 指令；**排程狀態（2026/8/29 起）**：GitHub Actions 僅保留 `workflow_dispatch`（排程已停用，原因：runner 到 CWA 連線不穩定、會推舊資料）；**主力自動更新通道＝本地 cron**（CWA 前置檢查 3 次重試、失敗中止）。部署指令與恢復 Actions 的條件 → `WORKFLOW.md` §7

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

> 完整官方清單（80 筆）見 `https://opendata.cwa.gov.tw/apidoc/v1`（OpenAPI YAML；web 清單頁是 SPA 爬不到）。常見但**已 404**、勿呼叫的 Data ID：O-A0013~19、F-C0033-001、F-C0034-001、F-A0045-001、W-C0024-001、F-C0040-001、O-C0010-001——改抓 CWA 官網頁面（obscura）或新聞。

### ⚠️ 關鍵陷阱（實測；處置細節見 `build/CWA_API.md`「實測差異」與 `WORKFLOW.md` §4–5）

1. O-A0001/O-A0002-001 的 `Now.Precipitation`＝**本日 0 時至目前累計**（非 1 小時）；1 小時用 `Past1hr`。
2. 回傳結構**與官方文件不同**（W-C0034-005 多一層 `TropicalCyclones`、移動欄位是 `MovingSpeed/MovingDirection`）：改解析碼前**先 dump 真實回傳**，勿照舊文件猜。
3. O-B0075-001（48h 海況）回傳空 JSON；海況改看 CWA 官網頁面或新聞。
4. **不支援 CORS**：前端無法直接呼叫，氣象資料必須 build 時本機抓取後寫入靜態 HTML。
5. forecast 欄位可能為 `None`：格式化前**必做 null 檢查**（`f"{None:.1f}"` 會崩潰）。
6. 更新頻率：颱風警報每 3~6 小時、氣旋資料每 6 小時；每 30~60 分鐘查一次即可。

---

## CWA cbph 災防告警 API（PWS，2026/9/1 實測）

cbph.cwa.gov.tw＝「預報中心資訊發布查詢系統」，即 CWA「災防訊息彙整」（`www.cwa.gov.tw/V8/C/P/PWS/PWS.html`；該頁只有文字清單）背後的地圖查詢系統。**公開 JSON API、免 key**；CORS 同 Open Data 不可依賴，一律 build 時本機抓取。

- **Endpoints**：`GET /api/global/`（目前生效告警，4 類分組）；`GET /api/{type}/?issuetime_after=&issuetime_before=&county=`（歷史，預設最新 50 筆）。type slugs：`cells`＝大雷雨即時訊息、`tywinds`＝颱風強風告警、`mountainstorms`＝山區暴雨警示訊息、`largesurfs`＝巨浪告警。
- **每筆欄位**：`identifier`、`official_id`、`sent`/`onset`/`effective`/`expires`（UTC）、`is_active`、`msg_type`、`description`（告警原句）、`cmam_text`（細胞廣播原文）、`cb_enabled`、`county[]`/`town[]`（含鄉鎮）、`coastal_*`、**`polygon`**（字串 `lat,lon lat,lon ...`，多 ring 以 `;` 分開＝官方影響區域座標）、`geocode_dict`（實測空）。
- **官方頁 deep link**：`https://cbph.cwa.gov.tw/ui/?type={type}&identifier={identifier}`
- **陷阱（實測）**：空類型回 503（如 largesurfs）；`county=` 過濾不可靠（自行 filter）；**非 Open Data 正式目錄**（無 SLA）→ build 端容錯、失敗跳過＋warning 不中斷；時間 UTC；UI 引用註明「資料來源：中央氣象署災防告警系統」。設計與用途 → `TODO.md` §2。

## Obscura 無頭瀏覽器

用於爬取 API 沒有的 JavaScript 渲染頁面（如 CWA 官網頁面）。**工具本身的使用說明見 skill `/root/.pi/agent/skills/obscura/SKILL.md`**（binary `/usr/local/bin/obscura`，Docker 容器 `obscura`，MCP HTTP port 3000）。repo 相關：

- **CWA 頁面**：颱風頁在 `P/Typhoon/`——`TY_WARN.html`（警報狀態）、`TY_NEWS.html`（路徑潛勢預報）、`TY_WIND.html`（強風告警）；舊路徑 `Typhoon.html` 已移除。
- 首頁 `https://www.cwa.gov.tw/V8/C/` 有 SVG JS 錯誤（`getTotalLength is not a function`），不影響主要內容。
- 多語句 JS 需包 IIFE：`(function(){ ... })()`。
- SSRF 保護會阻擋 private network，需加 `--allow-private-network`。
- Docker 容器未運行時：`docker run -d --name obscura -p 3000:3000 h4ckf0r0day/obscura mcp --http --port 3000 --host 0.0.0.0`

---

## 網站專案（已上線：Cloudflare Pages ×3 自訂域名；GitHub Pages 備用 mirror）

- **文件分工**：runbook（例行更新、新事件、驗證清單、部署、排程、陷阱）→ `WORKFLOW.md`；CWA 欄位查表 → `build/CWA_API.md`；手動路徑 → `MANUAL_UPDATE.md`；本地 cron → `LOCAL_CRON.md`；構想與待辦 → `TODO.md`。
- **⚠️ 更新災情前必看 `WORKFLOW.md` §8「Agent 效率規範」**：先查 repo 既有檔案／`ctx_search`／`cwa_cache.json`，只查會變的資料，同一資料一個 session 只查一次。
- **build 入口**：`./build/build.sh`（產出 `public/`（繁中）＋ `public/ja/`（日文）、`llms.txt`（站點＋事件索引）與 `llms-full.txt`（事件全文）；CWA 資料 build 時本機抓取）。
- **颱風軌跡圖台灣輪廓**：`build/cwa.py` 的 `typhoon_svg()` 用 `build/taiwan_geo.py` 的 `ISLANDS`（本島＋澎湖／金門／馬祖／蘭嶼／綠島各自獨立 polygon）；產生器 `build/make_taiwan_geo.py`（純 Python Douglas–Peucker，無相依）重跑後會覆寫 `taiwan_geo.py`，GeoJSON 快取 `build/_geo_cache_*.json` 已 gitignore。
- **i18n**：預設 zh-Hant（根目錄）、ja（`public/ja/`）；UI 字串收斂在 `build/i18n.py`（`STRINGS`＋`t()` 三級回退），**加新語言＝加一組 dict、不改模板**；**內容不翻譯**——事件 Markdown 正文、CWA 資料全語言保留中文原文，非預設語言頁面以 `content_note` / `cwa_data_note` 提示。

### 不變項（改動前先確認）

- **更新模式**：本地 cron（每 2 小時）自動 build＋部署為主力；Actions 手動 dispatch 為備援；**災情新聞人工把關、不自動推 RSS**（流程見 `WORKFLOW.md` §1、`MANUAL_UPDATE.md`）。
- **金鑰**：CWA Key、Cloudflare 憑證分散在 (1) 本機 `~/.zshrc`（手動）、(2) GitHub Secrets（dispatch）、(3) `build/deploy.env`（cron 用，600）；**不寫進任何輸出檔案、不進 `public/`、不進網站**。
- **非即時**：首頁顯示「**產生時間**」（i18n key `updated`），由 `build/site.py` 以**固定 UTC+8** 產生（`datetime.now(timezone(timedelta(hours=8)))`）；**不可改回不帶時區的 `datetime.now()`**（Actions runner 是 UTC、會慢 8 小時）。「產生時間」＝網頁何時生成，**不等於氣象／災情資料已更新**。
- **CWA 不支援 CORS**：氣象資料全部 build 時本機抓取寫入靜態 HTML；前端零外部請求、首頁零 JS。
- **授權僅針對網站專案**（2026/8/28 修正）：網站程式 **GNU AGPLv3**（`LICENSE`）、網站內容（含 `llms.txt`／`llms-full.txt`）**CC BY-NC-SA 4.0**（`LICENSE-CONTENT`，不得商用）；**倉儲本身**（`build/` 腳本、`災情/`、`颱風/`、文件）**不以此兩授權釋出**；CWA 資料以官方條款為準。
- **LLM 友善產出**：build 必產 `llms.txt`＋`llms-full.txt`，canonical base URL `https://weather.avpclub.eu.org`（`build/site.py` 之 `SITE_BASE`）。

### 網站結構

- **首頁**：頂部「目前風險狀態列」（`build/cwa.py: current_risk_level()` 由 CWA 目前生效中之熱帶氣旋／海上颱風警報／災害天氣特報自動推導：紅/黃/綠/**中性**（無生效中項目但有 ≤48h 內解除紀錄）/未知；與事件 `severity` 無關）→ 氣象彙整（颱風軌跡/警報特報/雨量/風力；警報特報卡**混排、時間倒序**，已解除項置底灰化、超過 48h（`LIFTED_TTL_HOURS`）不顯示）→ 事件 Hero（中性入口卡，無 severity 色系與徽章）＋ 各縣市災情總覽（依縣市分組、時間倒序）→ 過去事件封存（含 severity 徽章）。
- **各縣市子頁（選用）**：該縣市災情按時間倒序。

### 部署（詳 `WORKFLOW.md` §6）

- **Cloudflare Pages**（**主要公開通道**）：專案 `weather`，自訂域名 `weather.avpclub.eu.org`、`weather.avpclub.uk`、`weather.larch.dpdns.org`（CNAME 已建、proxied、自動 HTTPS）。更新：`npx wrangler pages deploy public --project-name weather`。
- **GitHub Pages**（備用 mirror，只收 `public/`）：orphan `gh-pages` 分支、不共享 history；目前 404 不影響使用（救回方式與代價見 `WORKFLOW.md` §6）。
- **GitHub 公開 repo 不接收**：build 腳本、災情/颱風 markdown 原文、內部倉庫資訊、金鑰——一律不外流到 `gh-pages` 或任何公開輸出。

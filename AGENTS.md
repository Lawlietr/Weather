# Weather - 台灣天氣與災情總覽

紀錄颱風動態與災情的 Markdown 倉儲，並附靜態網站 build（產出 `public/`、`llms.txt`、`llms-full.txt`；主要 host 於 Cloudflare Pages 自訂域名，另同步 GitHub Pages；見下方「網站專案」）。

## ⚠️ 時間意識（極度重要）

**撰寫或查詢災情前，必須先確認目前的現實時間（系統時間）。**

- 本項目核心目的是**記錄目前正在發生的天氣事件**與即時災情彙整；搜尋與引用新聞時**只關注當前事件相關的最新報導**，搜尋結果出現非當前事件的歷史資料應主動過濾
- 檔案中的時間戳必須與現實時間一致，不可混淆年份或日期；每次新增災情前先確認該災情屬於「目前正在發生」的事件

## ⚠️ 網路搜尋（極度重要）

**使用 `web_search` 時，不要硬編碼 `provider` 參數**——預設省略，讓工具自動使用 `/web-tools` 設定的預設引擎（SearXNG，免 key）。硬編碼未設定 key 的 provider（如 `brave`）會失敗；需要特定 provider 時先確認其 key 存在。

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

## ⚠️ 災情記錄邊界（極度重要）

**專案核心目的是「記錄天氣事件與災情」，不是「記錄所有與天氣有關的意外」。**

### 判斷原則

| 類型 | 例子 | 是否記錄 | 說明 |
|------|------|----------|------|
| **純粹天災** | 淹水、坍方、樹倒、停電 | ✅ 記錄 | 純天氣造成 |
| **天災＋人為因素** | 大雨後泛舟翻覆、跑山 | ✅ 記錄（已存在） | 天氣是條件，人為決策是關鍵 |
| **純人為意外** | 雨天車禍、雷擊意外 | ❌ 不記錄 | 天氣是背景，非主因 |

### 規則

- **核心判斷**：天氣是否為災情的**主要或關鍵因素**？若只是背景條件（如雨天），不記錄；若天氣是主要原因（如大雨導致淹水、溪水暴漲），記錄（上表即三類判斷範例）
- **已存在的記錄不刪除**：災情檔案已建立即不刪（歷史紀錄價值），新增加時嚴格依上表判斷
- 「大雨後泛舟翻覆」屬「天災＋人為」類，已存在於沙德爾檔案：既有保留，未來類似事件不新建

## 目錄與檔名

### 颱風檔案

```
颱風/{YYYY}/{MM}/{MMDD}_{NN}_{中文名}_{國際命名}.md
```

範例：`颱風/2026/07/0702_09_巴威_BAVI.md`

**說明**：
- `{MMDD}`：生成日期（月 + 日，補零，如 0702 表示 7 月 2 日）
- `{NN}`：颱風編號（補零）＝CWA 熱帶氣旋編號（非 JTMA），規則見下方「颱風編號規範」
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
- **災情行格式（重要）**：首页「各縣市災情總覽」由 build 自動把所有事件檔的災情**依縣聚合**（跨事件、時間倒序、每縣最新 8 筆）。聚合來源是事件檔中的**四欄災情表格**，欄位必須是 `時間|地點|類型|說明`（如 `2026/9/12 18:00|宜蘭冬山鄉慈愛路|積水|水深至腳踝`）。判縣依「章節標題含縣名」或「地點文字含縣名」。因此零星災情只需寫成此四欄表並放在含縣名的章節下，build 即自動歸縣、無須資料庫。

### 零星災情的寫法（2026/9/15 定案：A/B 並用，判斷標準＝對應事件 status）

「零星災情」＝不屬於任何事件檔的小災情。判斷：

1. **對應事件仍 `status: active` → 併入該事件檔（A）**：在該檔含縣名的章節以四欄表 append 一行，原地更新「最後修改」行。
2. **事件已 `ended` 或無對應事件 → 建最小事件檔（B）**：`災情/{YYYY}/{MM}/{MMDD}_{事件類型}_{名稱}.md`，**建檔即 `status: ended`**（不進「目前事件」區）。

**B 案範本與必守限制**（front matter 必填、災情行時間帶完整年份、每縣最多顯示 8 筆等）→ `WORKFLOW.md` §2.3。範例實檔：`災情/2026/09/0912_零星_台東樹倒與土石流.md`。

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

- **颱風資料**（軌跡、強度、位置、預測）、**警報與特報**（海上颱風警報、大雨特報、強風特報）、**雨量/風力/浪高**：以中央氣象署（CWA）API 為主（欄位查表 → `build/CWA_API.md`）
- **災防告警區**（大雷雨/颱風強風/山區暴雨/巨浪，含官方影響區域 polygon、細胞廣播狀態）：以 CWA cbph API（`cbph.cwa.gov.tw/api/`，免 key、build 時抓取）為主；欄位與陷阱 → `build/CWA_API.md`「CWA cbph」節
- **災情紀錄**（淹水、樹倒、落石、停電等）：以各縣市新聞媒體為輔，引用時請註明出處
- **停班停課**：以**人事行政總處（DGPA）CAP feed**為主（由各縣市政府公告、結構化、免 key；端點與陷阱 → `build/dgpa.py` 頭註），人工查證用 DGPA 22 縣市查詢頁；事件檔存檔層引用時仍註明原始出處（縣市政府公告/新聞）
- **交通影響**：以交通部或各縣市政府公告為主，新聞媒體為輔
- **措辭跟隨來源、不自行解讀（2026/9/1 定）**：對路徑、強度、登陸與對台影響的判斷性表述，一律引來源原話（CWA API 數值、CWA 發言人/公告口吻），**不得加「二次登陸」「直接侵台」等推測性升級詞**——以 CWA 當時路徑為準（例：9/1 沙德爾返回時 CWA 預測登陸廣東、口徑為「直接侵台機會低」，就照此寫；CWA 修訂路徑後再更新）。
- **災情來源優先級（build）**：repo 現有 `災情/` markdown → **RSS** → Obscura 抓取。每筆附**新聞來源**，僅給**少量摘要＋原連結**。
- **RSS 半自動流程**：build 時自動抓 verified RSS 來源產出候選清單 `build/rss_candidates.json`（**從不進 `public/`**）；相關性判斷**由人 / LLM 審查**，挑中者寫入事件檔「XX災情新聞來源」章節才上線。完整流程與驗證見 `WORKFLOW.md` §1/§3。

> ⚠️ 使用新聞資料時，請確認時效性，避免使用舊聞；引用時請註明新聞來源與日期。

## 新聞 RSS 來源

**一律先讀 `build/rss_sources.json`** 取得來源清單（`sources` 已實測可用；`failed_sources` 失效**勿呼叫**；`usage_notes` 為完整抓取守則——含 rss20/atom 解析、BOM、民報域名、風傳媒端點、失敗降級等所有陷阱），不要自行重新查或寫死 URL。

## 參考索引（本檔只留常駐規則；特定任務的細節直接去指定處查）

| 主題 | 去哪查 |
|------|--------|
| CWA API 欄位 / 事件類型優先級 / 關鍵陷阱 | `build/CWA_API.md`（或 `ctx_search(source: "CWA_API.md 欄位查表")` 抽段落） |
| cbph 災防告警（endpoints、polygon、陷阱） | `build/CWA_API.md`「CWA cbph」節 |
| 停班停課 feed（端點、實測結構、發布機制） | `build/dgpa.py` 頭註（單一事實來源） |
| RSS 來源清單與抓取守則 | `build/rss_sources.json`（`usage_notes`） |
| 例行更新 / 新事件 / 零星災情範本 / 驗證 / 部署 / 排程 | `WORKFLOW.md`（零星災情範本 §2.3） |
| Obscura 工具用法 | Skill `/root/.pi/agent/skills/obscura/SKILL.md` |
| 構想與待辦 | `TODO.md` |

## Git

- 預設分支：`main`（原 `master` 已更名）
- Remotes：`origin`＝內部 Forgejo（`ssh://fg/lawliet/Weather.git`，內網，Identity `~/.ssh/id_rsa_gitea`）；`github`＝公開 repo `Lawlietr/Weather`（SSH `git@github.com:Lawlietr/Weather.git`，key `id_ed25519_github`，直推即可、**不需要 `GH_PAT`**）。commit 後**兩邊都推**：`git push origin <branch> && git push github <branch>`
- **開發流程（2026/9/16 重申：勿直接 commit/push `main`）**：所有開發在 `DEV` 分支 commit→build＋部署測試站 `wea-testing`、真瀏覽器（Playwright）驗證→**經使用者同意後**才將 `DEV` 合併進 `main` 並推 `main`（兩邊 remote 皆推）。生產自動部署（`build/deploy-cron.sh`→`deploy.sh`）**以 repo 目前 checkout 為準、無分支邏輯**：DEV 開發期間跑自動部署＝DEV 內容上生產；合併回 `main` 後切回 `main` 再部署即恢復生產為已合併狀態。
- 無 lint/test 指令；**排程狀態（2026/8/29 起）**：GitHub Actions 僅保留 `workflow_dispatch`（排程已停用，原因：runner 到 CWA 連線不穩定、會推舊資料）；**主力自動更新通道＝本地 cron**（CWA 前置檢查 3 次重試、失敗中止）。部署指令與恢復 Actions 的條件 → `WORKFLOW.md` §7

---

## 中央氣象署（CWA）Open Data API

⭐ **逐 dataset 欄位查表＋事件類型優先級＋關鍵陷阱**：**`build/CWA_API.md`**——解析資料前讀它（或 `ctx_search` 抽段落）。

- **API Key**：環境變數 `CWA_API_KEY`（已設 `~/.zshrc`／專案 `.env` gitignored）。**不得硬編碼或 commit 到 Git**；程式用 `os.getenv("CWA_API_KEY")`。
- **Base URL**：`https://opendata.cwa.gov.tw/api/v1/rest/datastore/{Data ID}?Authorization=${CWA_API_KEY}&format=JSON`
- **最致命兩坑**：① 回傳結構**與官方文件不同**——改解析碼前**先 dump 真實回傳**，勿照舊文件猜；② **不支援 CORS**——所有氣象資料 build 時本機抓取寫入靜態 HTML。

## CWA cbph 災防告警 API（PWS）

災防告警（大雷雨/颱風強風/山區暴雨/巨浪，含官方影響區域 polygon）以 `cbph.cwa.gov.tw/api/` 為主（公開 JSON、免 key、build 時本機抓取；**非 Open Data 正式目錄、無 SLA** → build 端容錯、失敗跳過不中斷）。**完整 endpoints、欄位（polygon、cmam_text）、陷阱（503、UTC、deep link）→ `build/CWA_API.md`「CWA cbph」節**。

## context-mode 知識庫（本機 agent 查詢加速器，2026/9/15 啟用）

**本節只適用於開發環境（此機）。** 自動部署的排程機（Ubuntu LXC，見 `LOCAL_CRON.md`）是**獨立系統**：它只跑 `build/deploy-cron.sh`（抓 CWA → build → 推 CF/Pages），不做推理、不需也不需安裝 context-mode——那台機器上沒有本知識庫、也不需要重建。

**已索引來源**（source label；本機 FTS5、**不版本化、不進 git**——單一事實來源永遠是 repo 內 markdown，這裡只是免重讀的查詢快取）：

| source label | 來源 | 用途 |
|---|---|---|
| `CWA_API.md 欄位查表` | `build/CWA_API.md` | 寫解析碼前查欄位/實測差異 |
| `WORKFLOW.md runbook` | `WORKFLOW.md` | 查例行流程、部署、排程 |
| `CWA OpenAPI dataset 目錄` | `opendata.cwa.gov.tw/apidoc/v1`（80 datasets） | 查 dataset 用途/參數 |

**規則**：
- 動到相關文件（改 `CWA_API.md`/`WORKFLOW.md`、CWA 上下線 dataset）後**重跑 `ctx_index`** 更新快取（`path:` 形式索引有 staleness 標記）。
- 查詢模式：`ctx_search(queries: [...], source: "CWA_API.md 欄位查表")` 抽段落，**不必整檔讀**；查不到再讀原檔。
- `災情/`、`颱風/` 事件內容**不要索引**（`llms.txt`/`llms-full.txt` 已是 agent 取用層）。
- **換機重建**：KB 與 session 記憶都在本機、不隨 repo 走。開發環境遷移/重裝後，照上表重跑 3 個索引（本機 2 個 `ctx_index`＋1 個 `ctx_fetch_and_index`，分內完成）；遺失的只有快取與 session 級記憶，持久知識都在 repo markdown。

## DGPA 停班停課 feed（2026/9/15 實測）

停班停課（各縣市政府公告、人事行政總處中央統一發布）以 CAP feed 為主：`GET https://alerts.ncdr.nat.gov.tw/RssAtomFeed.ashx?AlertType=33`（免 key）。**⚠️ feed 是滾動近期視窗、不是「目前生效中」清單**——「是否目前相關」由 `build/dgpa.py` 的 `is_current()` 判斷。**完整 feed/CAP 欄位實測結構、陷阱、發布機制 → `build/dgpa.py` 頭註**（單一事實來源；人工查證頁 `https://www.dgpa.gov.tw/typh/daily/nds.html`（注意：僅 www 可用）亦在其中）。首頁卡呈現定案（有相關公告→展開置頂於颱風卡之上／無→收起置底）→ 見下方「網站結構」；事件檔存檔層 → `TODO.md` §6。

## Obscura 無頭瀏覽器

爬 API 沒有的 JS 渲染頁面（如 CWA 官網頁面）。**工具用法見 skill `/root/.pi/agent/skills/obscura/SKILL.md`**。本 repo 特定事實：

- **⚠️ `/map/`（Leaflet 向量層）驗證一律先用 Playwright 真 Chromium，不要用 obscura 截圖判層（2026/9/16 實測）**：obscura 引擎缺 SVG 1.1 factory API（`createSVGRect` 等）→ `L.Browser.svg === false` → 所有向量層（雨量圓點、告警 polygon）不渲染且無 console 輸出，截圖會假陽性「圖層空」。Playwright 跑法：`NODE_PATH=/root/opencode-stuffs/steam-deck-utilities/web/node_modules node <script>`（Chromium 在 `~/.cache/ms-playwright`，npx 預設解析路徑沒有 browser 不可用）；驗證要點＝`.leaflet-overlay-pane path.leaflet-interactive` 的數量＋fill 顏色分佈＋實際中心座標（可用 tile src 座標反算）。obscura 的 SVG/console 缺陷已備妥 bug 報告文本待回報。

- CWA 颱風頁：`P/Typhoon/TY_WARN.html`（警報狀態）、`TY_NEWS.html`（路徑潛勢）、`TY_WIND.html`（強風）；舊路徑 `Typhoon.html` 已移除；首頁 SVG JS 錯誤不阻擋主要內容。
- 多語句 JS 需包 IIFE；SSRF 阻擋需 `--allow-private-network`；容器未運行：`docker run -d --name obscura -p 3000:3000 h4ckf0r0day/obscura mcp --http --port 3000 --host 0.0.0.0`

---

## 網站專案（已上線：Cloudflare Pages ×3 自訂域名；GitHub Pages 備用 mirror）

- **文件分工**：見上方「參考索引」表（runbook → `WORKFLOW.md`；CWA 欄位 → `build/CWA_API.md`；手動路徑 → `MANUAL_UPDATE.md`；本地 cron → `LOCAL_CRON.md`；構想與待辦 → `TODO.md`）。
- **⚠️ 更新災情前必看 `WORKFLOW.md` §8「Agent 效率規範」**：先查 repo 既有檔案／`ctx_search`／`cwa_cache.json`，只查會變的資料，同一資料一個 session 只查一次。
- **build 入口**：`./build/build.sh`（產出 `public/`（繁中）＋ `public/ja/`（日文）、`llms.txt`（站點＋事件索引）與 `llms-full.txt`（事件全文）；CWA 資料 build 時本機抓取；另產 cbph 災防告警 `build/map.geo.json`（build 中間檔、gitignored，供 `/map/` 災防告警地圖頁消費）＋離線瓦片 `public/assets/tiles/`（z8–z11；來源與陷阱見 `build/tiles.py` 頭註：OSM 官方 server 對本機 IP 假 200 封鎖，改用 `tile.openstreetmap.de`））。
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

- **首頁**：頂部「目前風險狀態列」（`build/cwa.py: current_risk_level()` 由 CWA 目前生效中之熱帶氣旋／海上颱風警報／災害天氣特報自動推導：紅/黃/綠/**中性**（無生效中項目但有 ≤48h 內解除紀錄）/未知；與事件 `severity` 無關）→ 氣象彙整（颱風軌跡/警報特報/雨量/風力；**颱風卡淘汰過時氣旋**：最新 analysis fix 超過 24h（`TYPHOON_STALE_HOURS`）即移除、有生效中海上颱風警報者豁免，`/map/` 仍用全量軌跡；警報特報卡**混排、時間倒序**，已解除項置底灰化、超過 48h（`LIFTED_TTL_HOURS`）不顯示；**卡片排序**：有 currently 相關停班停課公告（DGPA feed）時**停班停課卡頂位**（層級最高）、無時收起卡置底（抓取失敗不顯示）；有活動氣旋時颱風卡頂位、無活動氣旋且抓取正常時置底（抓取失敗仍頂位，警示不降級）；實作詳 `build/dgpa.py` 與 `build/cwa.py` 的 `cwa_section_html()`）→ 事件 Hero（中性入口卡，無 severity 色系與徽章）＋ 各縣市災情總覽（**build 時跨所有事件檔依縣聚合、時間倒序、每縣最新 8 筆；純靜態、無資料庫**）→ 過去事件封存（含 severity 徽章）。
- **各縣市子頁（選用）**：該縣市災情按時間倒序。
- **災防告警地圖 `/map/`（2026/9/2 上線）**：`build/map_page.py`＋自託 Leaflet 1.9.4（`build/static/leaflet/`）＋離線瓦片；cbph 4 類告警官方 polygon 分色渲染、hover/click 詳情卡、圖層開關、`<noscript>` fallback、行動版 bottom-sheet；資料全 build 時寫入（`map.geo.json` 嵌入頁面，前端零外部請求）。細節與待辦見 `TODO.md` §2。

### 部署（指令、域名與救回方式詳 `WORKFLOW.md` §6）

- **Cloudflare Pages**（主要公開通道，`weather.avpclub.eu.org` 等 3 自訂域名）＋ **GitHub Pages**（備用 mirror，orphan `gh-pages` 分支、只收 `public/`）。
- **測試站**：`wea-testing` 專案（`weatesting.avpclub.eu.org`），DEV 預覽專用、**純手動部署**、不在自動部署範圍；指令與重建守則→`WORKFLOW.md` §6。
- **GitHub 公開 repo 不接收**：build 腳本、災情/颱風 markdown 原文、內部倉庫資訊、金鑰——一律不外流到 `gh-pages` 或任何公開輸出。

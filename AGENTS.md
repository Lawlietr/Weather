# Weather - 台灣天氣與災情總覽

紀錄颱風動態與災情的 Markdown 倉儲，並附靜態網站 build（產出 `public/`、`llms.txt`、`llms-full.txt`；主要 host 於 Cloudflare Pages 自訂域名，另同步 GitHub Pages；見下方「網站專案」）。

## ⚠️ 時間意識（極度重要）

**撰寫或查詢災情前，必須先確認目前的現實時間（系統時間）。**

- 本項目核心目的是**記錄目前正在發生的天氣事件**與即時災情彙整；搜尋與引用新聞時**只關注當前事件相關的最新報導**，搜尋結果出現非當前事件的歷史資料應主動過濾
- 檔案中的時間戳必須與現實時間一致，不可混淆年份或日期；每次新增災情前先確認該災情屬於「目前正在發生」的事件

## ⚠️ 網路搜尋（極度重要）

**使用 `web_search` 時，不要硬編碼 `provider` 參數**——省略讓工具用 `/web-tools` 預設引擎；硬編碼未設 key 的 provider 會失敗。

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

| 類型 | 例子 | 是否記錄 |
|------|------|----------|
| **純粹天災** | 淹水、坍方、樹倒、停電 | ✅ 記錄 |
| **天災＋人為因素** | 大雨後泛舟翻覆、跑山 | ✅ 記錄（已存在） |
| **純人為意外** | 雨天車禍、雷擊意外 | ❌ 不記錄 |

### 規則

- **核心判斷**：天氣是否為災情的**主要或關鍵因素**？背景條件（如雨天）不記錄；主要原因（如大雨導致淹水、溪水暴漲）記錄（上表即三類判斷範例）
- **已存在的記錄不刪除**：檔案已建立即不刪（歷史紀錄價值），新增時嚴格依上表判斷；「大雨後泛舟翻覆」屬「天災＋人為」類（已存在於沙德爾檔案）：既有保留，未來類似事件不新建

## 目錄與檔名

### 颱風檔案

```
颱風/{YYYY}/{MM}/{MMDD}_{NN}_{中文名}_{國際命名}.md
```

範例：`颱風/2026/07/0702_09_巴威_BAVI.md`

**說明**：`{MMDD}`＝生成日期、`{NN}`＝CWA 熱帶氣旋編號（非 JTMA，見下方「颱風編號規範」）；兩者皆補零，確保按日期與編號自然排序。

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
- **災情行格式（重要）**：災情一律寫成四欄表 `時間|地點|類型|說明`（如 `2026/9/12 18:00|宜蘭冬山鄉慈愛路|積水|水深至腳踝`），放在含縣名的章節下——build 即自動依縣聚合到首頁「各縣市災情總覽」（時間倒序、每縣最新 8 筆、無須資料庫；機制與限制 → `WORKFLOW.md` §2.3）

### 零星災情的寫法（2026/9/15 定案：A/B 並用，判斷標準＝對應事件 status）

「零星災情」＝不屬於任何事件檔的小災情。判斷：

1. **對應事件仍 `status: active` → 併入該事件檔（A）**：在該檔含縣名的章節以四欄表 append 一行，原地更新「最後修改」行。
2. **事件已 `ended` 或無對應事件 → 建最小事件檔（B）**：`災情/{YYYY}/{MM}/{MMDD}_{事件類型}_{名稱}.md`，**建檔即 `status: ended`**（不進「目前事件」區）。

**B 案範本與必守限制**（front matter 必填、災情行時間帶完整年份、每縣最多顯示 8 筆等）→ `WORKFLOW.md` §2.3。範例實檔：`災情/2026/09/0912_零星_台東樹倒與土石流.md`。

## 颱風編號規範

**⚠️ 所有颱風編號一律以 CWA 熱帶氣旋編號（`CwaTdNo`）為準，不使用 JTMA 國際編號**（兩者常不一致：沙德爾 = JTMA 18 / CWA 20）。適用範圍：檔名 `{NN}`、front matter `event:`、基本資料表「編號」、警報時程引用。檔名可於 `_` 後保留 JTMA 編號（如 `0818_20_沙德爾_SAUDEL.md`），但 `event:` 標題必須寫 CWA 編號。CWA API 尚未分配編號（剛生成 TD）時可先寫 JTMA 並加註待補。
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

- **颱風資料**（軌跡、強度、位置、預測）、**警報與特報**、**雨量/風力/浪高**：以 CWA API 為主（→ 下方「CWA」節；欄位查表 `build/CWA_API.md`）
- **災防告警區**（大雷雨/颱風強風/山區暴雨/巨浪，含官方影響區域 polygon、細胞廣播狀態）：以 CWA cbph API（`cbph.cwa.gov.tw/api/`，免 key、build 時抓取）為主；欄位與陷阱 → `build/CWA_API.md`「CWA cbph」節
- **災情紀錄**（淹水、樹倒、落石、停電等）：以各縣市新聞媒體為輔，引用時註明出處
- **停班停課**：以 DGPA CAP feed 為主（→ 下方「DGPA」節）；事件檔引用時仍註明原始出處（縣市政府公告/新聞）
- **交通影響**：以交通部或各縣市政府公告為主，新聞媒體為輔
- **措辭跟隨來源、不自行解讀（2026/9/1 定）**：對路徑、強度、登陸與對台影響的判斷性表述，一律引來源原話（CWA API 數值、CWA 發言人/公告口吻），**不得加「二次登陸」「直接侵台」等推測性升級詞**——以 CWA 當時路徑為準（例：9/1 沙德爾返回時 CWA 預測登陸廣東、口徑為「直接侵台機會低」，就照此寫；CWA 修訂路徑後再更新）。
- **災情來源優先級（build）**：repo 現有 `災情/` markdown → **RSS** → Obscura 抓取。每筆附**新聞來源**，僅給**少量摘要＋原連結**。
- **RSS 半自動流程**：build 產候選清單 `build/rss_candidates.json`（**從不進 `public/`**）；相關性由人 / LLM 審查，挑中才寫入事件檔「XX災情新聞來源」章節上線（流程與驗證 → `WORKFLOW.md` §1/§3）

> ⚠️ 新聞注意時效性、避免舊聞；引用註明來源與日期。

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
| 構想與待辦（任務帳本） | `TODO.md`（只做/優先級/狀態；細節 → `design/<功能>.md`） |

## Git

- 預設分支：`main`（原 `master` 已更名）
- Remotes：`origin`＝內部 Forgejo（`ssh://fg/lawliet/Weather.git`，內網，Identity `~/.ssh/id_rsa_gitea`）；`github`＝公開 repo `Lawlietr/Weather`（`https://github.com/Lawlietr/Weather.git`，直推即可、**不需要 `GH_PAT`**）；`codeberg`＝公開 repo `Lawlietr/Weather`（`ssh://git@codeberg.org/Lawlietr/Weather.git`，走 `~/.ssh/config` 的 codeberg.org 區塊、Identity `id_rsa_gitea`）。commit 後**三邊都推**：`git push origin <branch> && git push github <branch> && git push codeberg <branch>`
- **開發流程（2026/9/16 重申：勿直接 commit/push `main`）**：所有開發在 `DEV` 分支 commit→build＋部署測試站 `wea-testing`、真瀏覽器（Playwright）驗證→**經使用者同意後**才將 `DEV` 合併進 `main` 並推 `main`（兩邊 remote 皆推）。生產自動部署（`build/deploy-cron.sh`→`deploy.sh`）**以 repo 目前 checkout 為準、無分支邏輯**：DEV 開發期間跑自動部署＝DEV 內容上生產；合併回 `main` 後切回 `main` 再部署即恢復生產為已合併狀態。
- 無 lint/test 指令；**排程狀態（2026/8/29 起）**：GitHub Actions 僅保留 `workflow_dispatch`（排程已停用，原因：runner 到 CWA 連線不穩定、會推舊資料）；**主力自動更新通道＝本地 cron**（CWA 前置檢查 3 次重試、失敗中止）。部署指令與恢復 Actions 的條件 → `WORKFLOW.md` §7

---

## 中央氣象署（CWA）API

解析任何 CWA 資料前先查 `build/CWA_API.md`（或 `ctx_search` 抽段落）——逐 dataset 欄位、事件類型優先級、關鍵陷阱都在那裡。

- **Open Data**：`https://opendata.cwa.gov.tw/api/v1/rest/datastore/{Data ID}?Authorization=${CWA_API_KEY}&format=JSON`；key 讀環境變數 `CWA_API_KEY`（`~/.zshrc`／`.env` gitignored，**不得硬編碼或 commit**）。兩致命坑：① 回傳結構**與官方文件不同**——改解析碼前**先 dump 真實回傳**，勿照舊文件猜；② **不支援 CORS**——所有氣象資料 build 時本機抓取寫入靜態 HTML。
- **cbph 災防告警**（大雷雨/颱風強風/山區暴雨/巨浪，含官方影響區域 polygon）：`cbph.cwa.gov.tw/api/`，免 key、build 時抓取、**非 Open Data 正式目錄、無 SLA → 失敗跳過不中斷**（endpoints/欄位/陷阱 → `CWA_API.md`「CWA cbph」節）。

## context-mode 知識庫（本機 agent 查詢加速器，2026/9/15 啟用）

**本節只適用於開發環境（此機）**：部署排程機（Ubuntu LXC，`LOCAL_CRON.md`）只跑 cron build＋部署、不做推理、沒有本 KB。

**已索引來源**（source label；本機 FTS5、**不版本化、不進 git**——單一事實來源永遠是 repo 內 markdown，這裡只是免重讀的查詢快取）：

| source label | 來源 | 用途 |
|---|---|---|
| `CWA_API.md 欄位查表` | `build/CWA_API.md` | 寫解析碼前查欄位/實測差異 |
| `WORKFLOW.md runbook` | `WORKFLOW.md` | 查例行流程、部署、排程 |
| `CWA OpenAPI dataset 目錄` | `opendata.cwa.gov.tw/apidoc/v1`（80 datasets） | 查 dataset 用途/參數 |
| `design/ 功能設計檔` | `design/*.md`（map/share-button/class-halt/rss/site） | 查功能定案細節、規格、陷阱（2026/9/16 拆檔新增） |

**規則**：
- 動到相關文件（改 `CWA_API.md`/`WORKFLOW.md`/`design/`、CWA 上下線 dataset）後**重跑 `ctx_index`** 更新快取（`path:` 形式索引有 staleness 標記）。
- 查詢模式：`ctx_search(queries: [...], source: "CWA_API.md 欄位查表")` 抽段落，**不必整檔讀**；查不到再讀原檔。
- `災情/`、`颱風/` 事件內容**不要索引**（`llms.txt`/`llms-full.txt` 已是 agent 取用層）。
- **換機重建**：KB 與 session 記憶在本機、不隨 repo 走——遷移後照上表重跑 4 個索引（3 `ctx_index`＋1 `ctx_fetch_and_index`）；遺失的只有快取，持久知識都在 repo markdown。

## DGPA 停班停課 feed（2026/9/15 實測）

停班停課（各縣市政府公告、人事行政總處中央統一發布）以 CAP feed 為主：`GET https://alerts.ncdr.nat.gov.tw/RssAtomFeed.ashx?AlertType=33`（免 key）。**⚠️ feed 是滾動近期視窗、不是「目前生效中」清單**——「是否目前相關」由 `build/dgpa.py` 的 `is_current()` 判斷。**完整 feed/CAP 欄位實測結構、陷阱、發布機制 → `build/dgpa.py` 頭註**（單一事實來源；人工查證頁 `https://www.dgpa.gov.tw/typh/daily/nds.html`（注意：僅 www 可用）亦在其中）。首頁卡呈現定案（有相關公告→展開置頂於颱風卡之上／無→收起置底）→ 見下方「網站結構」；事件檔存檔層 → `design/class-halt.md`。

## Obscura 無頭瀏覽器

爬 API 沒有的 JS 渲染頁面（如 CWA 官網頁面）。**工具用法見 skill `/root/.pi/agent/skills/obscura/SKILL.md`**。本 repo 特定事實：

- **⚠️ `/map/`（Leaflet 向量層）驗證一律用 Playwright 真 Chromium，勿用 obscura 截圖判層**（obscura 缺 SVG 1.1 factory API → 向量層不渲染、截圖假陽性「圖層空」，2026/9/16 實測）。跑法與驗證要點 → `design/map.md`；obscura 缺陷 bug 報告待回報。

- CWA 颱風頁：`P/Typhoon/TY_WARN.html`（警報狀態）、`TY_NEWS.html`（路徑潛勢）、`TY_WIND.html`（強風）；舊路徑 `Typhoon.html` 已移除。
- 多語句 JS 需包 IIFE；SSRF 阻擋需 `--allow-private-network`；容器未運行：`docker run -d --name obscura -p 3000:3000 h4ckf0r0day/obscura mcp --http --port 3000 --host 0.0.0.0`

---

## 網站專案（已上線：Cloudflare Pages ×3 自訂域名；GitHub Pages 備用 mirror）

- **文件分工**：見上方「參考索引」表（runbook → `WORKFLOW.md`；CWA 欄位 → `build/CWA_API.md`；手動路徑 → `MANUAL_UPDATE.md`；本地 cron → `LOCAL_CRON.md`；構想與待辦 → `TODO.md` 帳本＋`design/` 各功能設計檔）。
- **⚠️ 更新災情前必看 `WORKFLOW.md` §8「Agent 效率規範」**：先查 repo 既有檔案／`ctx_search`／`cwa_cache.json`，只查會變的資料，同一資料一個 session 只查一次。
- **build 入口**：`./build/build.sh` → `public/`（繁中）＋`public/ja/`（日文）、`llms.txt`＋`llms-full.txt`、cbph `build/map.geo.json`（中間檔、gitignored）、離線瓦片（來源陷阱 → `build/tiles.py` 頭註）。
- **颱風軌跡圖台灣輪廓**：`build/taiwan_geo.py` 的 `ISLANDS`；產生器 `build/make_taiwan_geo.py` 重跑會**覆寫 `taiwan_geo.py`**（GeoJSON 快取 `build/_geo_cache_*.json` gitignored）。
- **i18n**：預設 zh-Hant（根目錄）、ja（`public/ja/`）；UI 字串收斂在 `build/i18n.py`（**加新語言＝加一組 dict、不改模板**）；**內容不翻譯**——事件正文與 CWA 資料全語言保留中文原文。

### 不變項（改動前先確認）

- **更新模式**：本地 cron 自動 build＋部署為主力、Actions 手動 dispatch 為備援（排程狀態與恢復條件 → `WORKFLOW.md` §7）；**災情新聞人工把關、不自動推 RSS**（→ `WORKFLOW.md` §1、`MANUAL_UPDATE.md`）。
- **金鑰**：CWA Key、Cloudflare 憑證分散在 (1) 本機 `~/.zshrc`（手動）、(2) GitHub Secrets（dispatch）、(3) `build/deploy.env`（cron 用，600）；**不寫進任何輸出檔案、不進 `public/`、不進網站**。
- **非即時**：首頁顯示「**產生時間**」（i18n key `updated`），由 `build/site.py` 以**固定 UTC+8** 產生（`datetime.now(timezone(timedelta(hours=8)))`）；**不可改回不帶時區的 `datetime.now()`**（Actions runner 是 UTC、會慢 8 小時）。「產生時間」＝網頁何時生成，**不等於氣象／災情資料已更新**。
- **CWA 不支援 CORS**：氣象資料全部 build 時本機抓取寫入靜態 HTML；前端零外部請求、首頁零 JS。
- **授權僅針對網站專案**（2026/8/28 修正）：網站程式 **GNU AGPLv3**（`LICENSE`）、網站內容（含 `llms.txt`／`llms-full.txt`）**CC BY-NC-SA 4.0**（`LICENSE-CONTENT`，不得商用）；**倉儲本身**（`build/` 腳本、`災情/`、`颱風/`、文件）**不以此兩授權釋出**；CWA 資料以官方條款為準。
- **LLM 友善產出**：build 必產 `llms.txt`＋`llms-full.txt`，canonical base URL `https://weather.avpclub.eu.org`（`build/site.py` 之 `SITE_BASE`）。

### 網站結構（實作細節 → `design/site.md`／`design/map.md`）

- **首頁**：「目前風險狀態列」（由 CWA 目前生效中警報／特報自動推導，**與事件 `severity` 無關**）→ 氣象彙整（颱風/警報特報/雨量/風力；卡片排序、過時氣旋淘汰、特報 TTL 等 → `design/site.md`）→ 事件 Hero＋各縣市災情總覽（build 時跨事件依縣聚合、純靜態無資料庫）→ 過去事件封存。
- **災防告警地圖 `/map/`**：cbph 4 類告警官方 polygon＋自託 Leaflet＋離線瓦片；資料全 build 時嵌入、**前端零外部請求**（細節與待辦 → `design/map.md`）。

### 部署（指令、域名與救回方式詳 `WORKFLOW.md` §6）

- **Cloudflare Pages**（主要公開通道，`weather.avpclub.eu.org` 等 3 自訂域名）＋ **GitHub Pages**（備用 mirror，orphan `gh-pages` 分支、只收 `public/`）。
- **測試站**：`wea-testing` 專案（`weatesting.avpclub.eu.org`），DEV 預覽專用、**純手動部署**、不在自動部署範圍；指令與重建守則→`WORKFLOW.md` §6。
- **GitHub 公開 repo 不接收**：build 腳本、災情/颱風 markdown 原文、內部倉庫資訊、金鑰——一律不外流到 `gh-pages` 或任何公開輸出。

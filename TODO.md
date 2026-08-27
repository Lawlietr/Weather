# TODO：災情與氣象彙整網站

> 狀態：**開發＋部署完成**（build＋CWA 氣象總覽＋繁中/日文多語言＋雙授權＋llms.txt，2026/8/26）；已上線 Cloudflare Pages（自訂域名 ×3，主要）＋ GitHub Pages；剩可選增強（RSS、地圖）。
> 建立日期：2026/8/26

---

## ⭐ 最高優先：改進台灣輪廓（**已實作**，2026/8/27 記）

> 現況：颱風動態的靜態 SVG（`build/cwa.py` 的 `typhoon_svg()`）把台灣畫成**手寫的 26 點簡化多邊形 `TAIWAN`**（`cwa.py` 第 288 行），加上線性矩形投影 `_px()`，輪廓很粗糙、不像真實台灣。
> 本項目標：讓輪廓「可識別」即可，不用無限逼真。工程不大——本質只是**換掉 `TAIWAN` 這串座標**，投影、城市點、軌跡線全都不用動。

### 範圍與規格（已定）

1. **包含區域**：台灣本島 ＋ 澎湖、金門、馬祖、蘭嶼、綠島（共 5 個離島群／島）。✅ 全部包含。
2. **精度**：使用**簡化的海岸線座標**，能看出「台灣本島＋各離島」的相對位置即可。✅ 本島 66 點＋離島共 48 點，總 114 點。
3. **授權／來源**：Natural Earth 1:10m（公有領域）＋ g0v/twgeojson（MIT），已標明出處。✅

### 實作結果（2026/8/27）

- **新增資料產生器**：`build/make_taiwan_geo.py`（含純 Python Douglas–Peucker 簡化，零相依）。
- **新增靜態資料**：`build/taiwan_geo.py`（`ISLANDS = [(i18n key, [(lon,lat),...]], ...]`，本島與各離島各自獨立 polygon）。
- **資料來源**：
  - 本島／澎湖／金門／蘭嶼／綠島 → Natural Earth 1:10m `ne_10m_admin_0_countries` 的 Taiwan feature（MultiPolygon，8 個 polygon，面積由大到小自動判別身分）。
  - 馬祖（連江縣）→ Natural Earth **不包含**，改取 g0v/twgeojson `twCounty2010.geo.json` 的 連江縣。
- **程式碼改動**：
  - `cwa.py` 移除手寫 `TAIWAN`，`typhoon_svg()` 改迴圈繪製 `ISLANDS` 中每個 ring（本島＋5 離島群各一 `<polygon>`，多 ring 離島如澎湖/馬祖仍正確）。
  - `_px()` 投影、城市點、軌跡線、預報、風圈**全未更動**。
- **驗證**：重 build 成功（`build.sh` → `public/`，4 事件／CWA live）。`public/index.html` 颱風卡 SVG 含 11 個 polygon；用 cairosvg 轉 PNG 預覽確認本島＋澎湖＋金門＋馬祖＋蘭嶼＋綠島均可識別，輪廓明顯像台灣。
- **快取**：產生器把原始 GeoJSON 快取於 `build/_geo_cache_*.json`（已加入 `.gitignore`，不進 repo）。
- **重跑方式**：修改輪廓只改產生器後執行 `python3 build/make_taiwan_geo.py`；最終資料 `taiwan_geo.py` 為靜態、可離線使用，**不要手改**。

> ✅ 已透過使用者審核（build 成功、輪廓可識別）。未 commit。

---

## 一、專案目標

建立一個給大眾使用的公開網站（host 於 GitHub Pages），彙整兩類資訊：

1. **氣象署天氣資訊**：颱風軌跡、警報特報、雨量、風力等（來自 CWA API）。
2. **災情彙整（新聞災情）**：各地區新聞災情，依「縣市 → 時間倒序 → 最新在最上面」呈現。

最終呈現：一個「新聞 + 氣象署資料」的綜合資訊入口，方便大眾快速掌握各地災況與天氣。

---

## 二、核心設計原則（已確認）

1. **由使用者手動更新（LLM/人工驅動）**
   - 不是自動排程，而是由使用者（或協助的 LLM）手動執行 build 並推送。
   - **API Key 等機敏資訊絕不外洩**到公開 GitHub repo 或公開網站。金鑰全程只存在本機執行環境，不編進任何輸出檔案。

2. **災情來源優先級**
   - **① repo 現有 markdown 優先**：`災情/{YYYY}/{MM}/*.md` 已整理的災情檔案。
   - **② RSS 訂閱源**：補 repo 尚未整理的新聞（如中央社、聯合、自由、民視 RSS）。
   - **③ Obscura 抓取**：RSS 沒有又確實需要時才用。
   - 每筆災情**必須附新聞來源**，僅提供**少量摘要＋原新聞連結**，詳細內容由使用者自行點進原連結。

3. **非即時、可手動更新**
   - GitHub Pages 是靜態託管，無法真正即時。
   - 採**手動 build + 推送**，更新頻率由使用者掌控。
   - **首頁必須顯示「最後更新時間」**（build 時寫入當下系統時間），讓使用者知道資料落後多久。

---

## 三、技術架構

### 3.1 為什麼不用「純前端即時抓取」
- 氣象署 API 金鑰會暴露在網頁原始碼 → 洩漏風險。
- 新聞網站大多阻擋 CORS，前端無法直接爬。
- 解法：**金鑰留在本機，build 出純靜態 HTML**，GitHub Pages 只提供檔案，金鑰從頭到尾不碰公開端點。

### 3.2 建議流程（手動 build）

```
本機（手動執行）
  ├── 讀 repo 災情 markdown  → 災情資料（縣市/時間/分級/摘要）
  ├── 讀 RSS / Obscura        → 補即時新聞災情（附來源）
  ├── 呼叫 CWA API（金鑰在本地）→ 氣象彙整
  └── build 出靜態 HTML（含「最後更新時間」）
            │ git push 到 Pages 分支
GitHub Pages 提供靜態網站
```

### 3.3 網站結構（2026/8/26 定案：事件為中心）

> **核心原則：首頁聚焦「目前正在發生」的災情事件。** 過去事件降級為封存列表，不佔首頁主體。

- **首頁**（依序）：
  1. **目前事件 Hero 區（首頁主體）**：`status: active` 且「最後修改」最新的事件——狀態 banner（🔴/🟡/🟢）、影響範圍、最新進展（讀檔尾最新數條）、縣市災情統計表、最新幾筆災情（時間倒序）。
  2. **活動氣象區塊**（CWA API 產出，天生即時）：活動颱風卡＋軌跡靜態 SVG、警報/特報列。無活動事件時顯示「目前無重大氣象事件」。
  3. **各縣市災情**（次級）：依縣分組、組內時間倒序。
  4. **過去事件封存（archive）**：`status: ended` 的事件一列一筆（事件名｜期間｜級別｜重點統計 → 事件整篇頁面）。
- **事件子頁**：單一事件完整內容（markdown 整篇渲染）。
- **各縣市子頁（選用）**：該縣市災情按時間倒序。

### 3.4 「目前事件」判定規則

- front matter 加 `status: active | ended`，由手動 build 時（LLM/人工）維護。
- 首頁 Hero = `active` 中「最後修改時間」最新者；其餘 `active` 排其下；`ended` 全部進 archive。
- CWA 氣象區塊不受此規則限制：API 有活動氣旋即顯示，無則顯示空狀態。

---

## 四、待拍板細節

### 已定案（2026/8/26）

- [x] **災情摘要：採方案 A**——每篇災情/颱風 markdown 開頭加 YAML front matter（`status`、`event`、`severity`、`counties`、`summary`、`sources`），build 直接讀取。
- [x] **氣象資料納入本 build**（金鑰留本機無虞）；API 失敗時降級為「上次成功資料＋警告」，不中斷 build。
- [x] **build 工具：Python**（自寫腳本＋內嵌 HTML 模板，零相依；不引 SSG）。
- [x] **首頁事件為中心**（見 3.3 / 3.4），聚焦目前 active 事件。
- [x] **軌跡圖：靜態 SVG**（W-C0034-005 Fix 資料 → 台灣輪廓＋軌跡折線＋預報虛線），不載入 JS 地圖庫。
- [x] **視覺**：資訊密集「應變看板」風格、mobile-first、淺色、系統字體、無外部 JS/追蹤、附 print CSS；顏色語彙 🔴 #d32f2f / 🟡 #f9a825 / 🟢 #388e3c。

### 尚未定案

- [ ] **RSS 來源清單**：需確認可用且允許跨域的台灣新聞 RSS 源（第一版可先只吃 repo markdown，RSS 留 hook 後續加）。
- [x] **GitHub Pages 分支**：定案 **orphan `gh-pages` 分支**，只裝 `public/` 靜態產物、不與 main 共享 history（2026/8/26 定案；流程見 `WORKFLOW.md` §6）。
- [x] **多語言**：已實作繁中（預設）＋日文（`public/ja/`）；UI 字串收斂於 `build/i18n.py`（~70 key），加新語言只需在 `STRINGS` 加一組 dict（§七.4 如實作）。

---

## 七、地圖標註功能（構想，2026/8/26 記，待實作）

> 目標：在互動地圖上標註災情新聞位置、雨量站 TOP、警戒區域、颱風軌跡，
> 讓使用者一眼看到「現在最危險的地區在哪」。
> （輪廓資料可與「⭐ 最高優先：改進台灣輪廓」共用同一套海岸線座標。）

### 7.1 選型（已定：Leaflet + OpenStreetMap）
- **不用 Google Maps**：JS API 強制綁定計費帳戶、需管 key 防盜用，個人靜態站不值得。
- **Leaflet + OSM 瓦片**：開源免費、無 API key、靜態部署無縫、功能夠（標記/pop-up/圓圈/折線/多邊形）。
- **保持輕量**：Leaflet 只在「地圖頁」載入（自託 `leaflet.js` ~40 KB + 1 個 CSS）；**首頁維持零 JS**（現有靜態 SVG 軌跡圖不換）。

### 7.2 離線自駕（硬需求）
- 所有 JS/CSS 自託在 `public/assets/`，不引 CDN。
- **瓦片策略**：build 時只抓台灣範圍所需瓦片存本地（約 z9–z11，幾十張 PNG、數 MB），
  Leaflet 指向本地瓦片 → **完全離線、零外部請求**；不要跑 OSM tile server（太重）。
  出範圍的瓦片顯示空白底即可（或 fallback 到現有靜態 SVG）。

### 7.3 資料座標盤點
- ✅ 已有：颱風軌跡/風圈（W-C0034-005）、雨量站（O-A0002-001 `GeoInfo`）、警戒區域多邊形（W-C0034-001 CAP `area`）。
- ❌ 缺：災情新聞的座標——做法：建**鄉鎮級靜態座標表**（gazetteer，JSON，手工維護或用 CWA C-B0074 測站資料生成），災情 markdown 的鄉鎮名稱對照；查不到回退縣級座標，再查不到不上圖。

### 7.4 多語言架構（順帶處理）
- 把 `build/site.py` 內嵌的 UI 字串收斂成 `UI_STRINGS = {"zh-Hant": {...}}` 字串表，
  模板用 key 取值 → 加新語言 = 加一個 dict，不改模板、不重寫頁面。內容（markdown）本身仍逐篇翻譯或留原文。

---

## 五、風險與注意事項

- **金鑰安全**：即使在公開 repo 的 Actions 中，Secret 也非完全隱藏；手動 build 是本方案唯一能完全排除此風險的路徑。
- **新聞合規**：直接爬新聞有反爬與版權風險，故優先 repo markdown 與 RSS。
- **資料延遲**：手動更新，最多落後一個更新週期。
- **免費限制**：Cloudflare Pages／GitHub Pages（均免費 tier）＋本機 build，對此規模足夠，無額外成本。

---

## 六、下一步

- [x] 為現有災情/颱風 markdown（4 篇）加 YAML front matter（`status`/`event`/`severity`/`counties`/`summary`/`sources`）。
- [x] 建立 build 腳本（front matter 解析＋事件為中心首頁＋archive）。
- [x] CWA 氣象總覽（`build/cwa.py`，build 時本機抓取）：颱風卡（永遠顯示，含靜態 SVG 軌跡＋15 m/s 風圈＋預報表）、警報/特報卡（無則整卡隱藏）、雨量站 TOP 10（有 active 事件展開、無則收合）。失敗降級：`build/cwa_cache.json` 快取＋「舊資料/快取/無法取得」警示，與「無資料」視覺區分。⚠️ Python 3.14 的 urllib 對 CWA 憑證鏈會 SSL 驗證失敗（Missing Subject Key Identifier），故改走 `curl` subprocess。
- [x] 設定 GitHub Pages 與推送流程：2026/8/26 上線 <https://lawlietr.github.io/Weather/>（繁中）＋ `/ja/`（日文）；orphan `gh-pages` 分支只收 `public/`；例行更新推送指令見 `WORKFLOW.md` §6。
- [x] 設定 Cloudflare Pages 與自訂域名（2026/8/26，**主要更新通道**）：專案 `weather`，域名 `weather.avpclub.eu.org`／`weather.avpclub.uk`／`weather.larch.dpdns.org`（CNAME 皆指向 `weather-9kb.pages.dev`、proxied）；更新只需 `npx wrangler pages deploy public --project-name weather`。
- [x] 雙授權：程式碼 GNU AGPLv3（`LICENSE`）＋內容 CC BY-NC-SA 4.0（`LICENSE-CONTENT`，2026/8/26 由 MIT 改訂；公開 repo 只收 `public/` 靜態產物，無 MIT 歷史痕跡）。
- [x] LLM 友善產出：build 產 `llms.txt`（索引）＋ `llms-full.txt`（事件全文），含授權聲明段。
- [ ] RSS 來源驗證與接入（可選，後續）。
- [ ] 地圖標註功能：Leaflet + OSM，離線自託瓦片，見 §七。

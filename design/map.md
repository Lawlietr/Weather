# 地圖紅警功能（/map/）設計

> 狀態：實作中（步驟 1–4a 完成、4a 樣式待重做）｜最後更新：2026/9/16
> 對應 TODO：M1–M5（見 `TODO.md` 主表）
> TL;DR：獨立 `/map/` 頁，自託 Leaflet 1.9.4＋離線 OSM 瓦片；疊 CWA cbph 4 類告警 polygon＋雨量站點＋（待做）颱風軌跡/風圈＋（待做）特報陸地紅區；資料全 build 時抓取嵌入頁面、前端零外部請求。

## 定位（2026/9/1 定案）

在互動地圖上以紅色危險告警標註「目前或預計會有淹水/大雨的地區」，讓使用者一眼看到「現在最危險的地區在哪」。**分兩層、可獨立上線**。

**地圖導向，非事件導向**——一張完整台灣地圖疊全部目前生效告警＋觀測＋災情點（對比 CWA cbph 的「選類型→事件列表→單事件範圍」），點擊紅色區域→該告警詳情＋本 repo 該區域相關災情紀錄。概念釐清：CWA 的「災情」是**危險告警**（哪裡可能變危險），非損失紀錄；實際災情（淹水/樹倒/停電）不在任何 CWA API，屬新聞層（2b）。

## 2a. CWA 紅警層（全自動部署，已定案）

- **掛在現有 build 流水線上**：build 時本機抓 CWA → 合成 `map.geo.json`（polygons + points，每筆帶 `level: 🔴/🟡/🟢`、`type`、`source`、`time`）→ 產地圖頁 → 部署。**沿用現有自動部署頻率（本地 cron 每 2 小時，2026/9/1 確認）**，不需新排程、新 agent、新金鑰；顏色/等級閾值邏輯全部寫死在 build 端（`cwa.py`/新模組），前端只負責渲染。
- 資料來源對應：

  | 地圖元素 | 來源 | 備註 |
  |----------|------|------|
  | PWS 災防告警區（大雷雨/颱風強風/山區暴雨/巨浪） | cbph.cwa.gov.tw `/api/global/`＋`/api/{type}/`（2026/9/1 實測新增） | **官方 polygon，免 gazetteer**；含生效時段/影響鄉鎮/細胞廣播狀態；欄位與陷阱見 `build/CWA_API.md`「CWA cbph」節 |
  | 雨量站紅點 | O-A0002-001 `GeoInfo` + `Past1hr`/當日累計 | 超閾值上紅，點大小/顏色深淺對應雨量等級 |
  | 颱風軌跡/風圈 | W-C0034-005 | 預測路徑＋風圈圓環 |
  | 海區警報多邊形 | W-C0034-001 CAP `area` | **唯一官方座標化多邊形，且是海區** |
  | 陸地紅區（豪大雨特報影響區域） | W-C0033-002/003 | ⚠️ 影響區域是**文字/縣市清單，非座標多邊形**，必須經 gazetteer 轉換；標籤註明生效時段（「今夜起」等）。**渲染定案（2026/9/16）：選項 A——新增縣界 GeoJSON 自託進 repo**（gazetteer 只有縣/鄉鎮中心點座標、無邊界多邊形，無法直接畫縣界；動工前需確認縣界資料源） |

- **gazetteer ✅ 已建（2026/9/1）**：`build/gazetteer.json`（產生器 `build/make_gazetteer.py`；測站/界線資料變動時才需重跑）。僅服務特報文字層＋新聞點對照（cbph 告警層用官方 polygon）；鄉鎮查不到回退縣級、再查不到不上圖。⚠️ **只有縣/鄉鎮中心點座標（lat/lon），無邊界多邊形（2026/9/16 實測）**——不足以畫縣界，見上方特報陸地層定案。
- **不做**：像素級降雨預報雲圖（CWA 開放資料無 48h 雨量預報座標，F-C0033-001 已下架）；河川水位/土石流（O-C0010-001 已下架）——淹水類警報只能靠 2b 新聞層，粒度到鄉鎮。

### cbph 災防告警 API（2026/9/1 實測，新增資料源）

實測記錄（endpoints、每筆欄位——含 `polygon` 官方影響區域座標、`cmam_text` 細胞廣播、deep link——與 503/`county=` 過濾不可靠/`is_active` 須自行驗證/UTC/無 SLA 等陷阱）一律以 `build/CWA_API.md`「CWA cbph 災防告警 API」節為**單一事實來源**，實作前先讀它。

- **更新頻率疑慮**：大雷雨即時訊息 lifespan 約 2 小時＝每 2 小時 cron 的下限，事件高峰期可能整筆錯過一週期——已接受 trade-off（見下方「決策」2；事件期間可加頻）。

## 2b. 災情新聞點層（人工/agent 餵料，可選疊層；暫緩（2026/9/1 定））

- 來源：RSS（見 `design/rss.md`）＋災情 markdown；鄉鎮名經 gazetteer 對照上圖，每筆附新聞來源連結。
- 維持人工把關（核心原則：災情新聞不自動推）；缺了不影響 2a CWA 層運作。
- gazetteer 本就要建，2b 建好後可直接沿用。

## 選型與離線自駕（已定案並實作）

- **Leaflet + OSM（非 Google Maps）**：Google 計費綁 billing、必須外連無法離線、key 暴露前端；若日後嫌 OSM 瓦片太素，改預渲染瓦片供應商（CARTO/OpenFreeMap）即可，架構不變。
- **離線自駕（硬需求）**：JS/CSS 全自託、不引 CDN；build 時只抓台灣範圍瓦片（z8–z11，`build/_tile_cache/` 持久化、缺什麼補什麼），完全離線、零外部請求；不跑 OSM tile server，出範圍顯示空白底。
- **保持輕量**：Leaflet 只在地圖頁載入；**首頁維持零 JS**（現有靜態 SVG 軌跡圖不換）。

## 地圖頁 UI（骨架已上線 2026/9/2）

- 已上線：獨立 `/map/` 頁、全幅地圖＋右側欄（行動版 bottom sheet）、點擊詳情卡（類型＋`official_id`、生效時段、影響鄉鎮、`description`、`cmam_text`＋`cb_enabled`、本 repo 災情連結、cbph 官方 deep link）、圖層配色（大雷雨 `#f59e0b`、颱風強風 `#ef4444`）＋開關、hover tooltip、「產生時間（每 2 小時更新、非即時）」、OSM 署名、`<noscript>` fallback。
- **剩（＝執行順序 6 v2）**：deep link（`/map/?layer=&zoom=&center=`、`/map/event/{identifier}`）、`/map/data.json` 公開＋寫進 `llms.txt`、時間線快照。

## 決策（2026/9/1 全部定案）

1. 採用 cbph 為資料源（非正式 API、無 SLA，以「轉引」措辭呈現；容錯沿用 RSS 守則）
2. 更新頻率＝與自動部署同頻、每 2 小時（事件期間可加頻至 30–60 分鐘；接受 trade-off：大雷雨 lifespan 約 2 小時）
3. 2b 新聞點層暫緩
4. 前端呈現＝選項 A：獨立 `/map/` 頁（「A＋首頁靜態 SVG 告警區快照」不在首批）

## 執行順序（2026/9/1 決策定案；首批＝1–4＋6）

1. ~~gazetteer（鄉鎮/縣級 JSON）~~ **✅（2026/9/1）**：`build/make_gazetteer.py` → `build/gazetteer.json`（towns 368 / counties 22，覆蓋全部現行鄉鎮市、無需手動補位；建立細節與陷阱見 git history）。
2. `build/cbph.py`：抓 4 類→驗證→合併進 `map.geo.json` — **✅（2026/9/2）**：4 類告警抓取、polygon→GeoJSON、UTC→UTC+8、503/404 容錯；`site.py` 呼叫 `cbph.build_map_geojson()` 寫 `build/map.geo.json`（build 中間檔、gitignore）。公開 `/map/data.json` 屬步驟 6。
3. `/map/` 骨架 — **✅（2026/9/2）**：`build/map_page.py`＋`build/tiles.py`（離線瓦片；來源陷阱——OSM 官方 server 對本機 IP 假 200 封鎖、改用 `tile.openstreetmap.de`——見 `tiles.py` 頭註）＋`build/static/leaflet/`（Leaflet 1.9.4 自託）。功能詳見上方「地圖頁 UI」；入口：首頁 nav＋llms.txt。
4. 觀測層（2026/9/16 拆 3 小批、各批獨立上線；實作於 `cwa.py`→`map.geo.json`→`map_page.py`）：
   - **4a 雨量站點層（2026/9/16 起）**：O-A0002-001 超閾值測站→三級點層（p1hr/p24hr ≥50/250 🔴、≥25/100 🟠、≥10/50 🟡；2026/9/16 真實資料校準：淡雨日 0/1/13 站）。座標取 **WGS84**（`GeoInfo.Coordinates[CoordinateName=WGS84]`，不可用 TWD67）；`cwa.fetch_rain_points()` 為單一事實來源。——**代碼已完成（2026/9/16）、真瀏覽器實測全點渲染正常**（obscura 無法渲染 Leaflet SVG，驗證流程見 AGENTS.md「Obscura」節）；點樣式未過關→見 4a-follow。
   - **4a-follow 雨量點樣式重做（🔥高優先、合併 4a 後先處理；2026/9/16 使用者初審未過）**：使用者實際螢幕判斷——① 圓形仍太小；② 暖橙/琥珀色系（現行 #dc2626/#ea580c/#f59e0b）仍與 OSM 底圖幹道粗橘線（含交流道/匝道交會處的橘色三角形樣小塊）混淆、干擾視覺判斷。底圖橘線是 OSM 標準 tile 自帶、不可控→點顏色必須避開色相 ~20-40° 橘系；候選方向待討論後再動手（冷藍系【注意巨浪告警 cyan 層衝突＋海水淡藍】、深色單色＋白環＋標註、加大尺寸等）。
   - **4b 颱風軌跡/風圈層**：W-C0034-005 觀測軌跡（實線）＋預報軌跡（虛線）＋最新預報點風圈圓環（空狀態＝無活動氣旋時圖層空，沿用「空＝查過」原則）。
   - **4c 特報陸地紅區層**：W-C0033-002/003 文字影響區域→**選項 A 縣界 GeoJSON 自託**（2026/9/16 定案；gazetteer 無邊界多邊形）；生效時段標籤（「今夜起」等）。
5. ~~2b 災情新聞點層（人工餵料）~~ 暫緩（見 §2b）
6. v2：`/map/data.json` 公開＋deep link＋時間線快照

## 中心偏移修正（✅ 2026/9/16）

初版開圖中心偏西 0.9°（設計 `MAP_CENTER [23.8, 120.95]`、實際 `[23.8, 120.05]`，桌面全寬皆中、手機不受影響）。根因：Leaflet 1.9.4 `setView` 對 `maxBounds` clamp，當**視口寬度超過 maxBounds 經度跨度**（z8 約 >965px＝所有桌面）時會把整個視口**重新對齊到 maxBounds 中心**——舊 bounds 中心經度恰好 120.05。修正：`MAP_MAX_BOUNDS` 改 `[[20.9,118.3],[26.7,123.6]]`（中心＝`MAP_CENTER`、總跨度不變、仍在離線瓦片覆蓋內）。**不變項：`MAP_MAX_BOUNDS` 中心必須恆等於 `MAP_CENTER`**。

## cbph 503 假警報（✅ 2026/9/13 修復、已合併 main）

**問題**：cbph API 對「**目前沒有生效中告警的類型**」回 HTTP 503（非空陣列）——此行為 2026/9/1 已實測並寫入 `AGENTS.md` 陷阱清單與 `build/cbph.py` docstring，但實作只做到「不中斷 build」、**沒做到「不算 warning」**：`fetch_alerts()` 對所有錯誤一律寫入 `warnings`，`build/map_page.py` 又將每條 warning 渲染成地圖頁 ⚠️。結果：某類型無告警＝使用者在 `/map/` 看到誤導性的「cbph {type}: 抓取失敗（HTTP 503）— 跳過」。

**實測例證（2026/9/13，正式站地圖）**：largesurfs（巨浪）無生效中告警 → 503；同刻 cells／tywinds／mountainstorms 皆 200。純表面問題（其餘三層正常、build 成功），但誤示「資料源故障」。

**修復（已定案並實作）**：`build/cbph.py` 一處小改（約 10 行）——`CbphFetchError` 帶 `status` 屬性；`fetch_alerts()` 對 503/404 視為該類型空清單（只打 `[info]`、不進 `warnings`）；4 類全 503/404 時記一條「可能 cbph 服務異常」全站 warning（防靜默）。單元測試 5/5（stub `_get_json`）；真實 build：largesurfs 503 → `[info]`、零 warning、地圖頁無「抓取失敗」。已部署測試站 wea-testing 驗證。2026/9/13 合併 main。

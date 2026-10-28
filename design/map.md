# 地圖紅警功能（/map/）設計

> 狀態：實作中（步驟 1–4a 完成、**4a-follow 樣式 2026-10-26 定案並已上線**；§2-7 底圖視野擴展 2026-10-26 定案、**§2-7c 兜底陸地層 2026-10-27 實作完成（DEV）**）｜最後更新：2026-10-27
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
- **離線自駕（硬需求）**：JS/CSS 全自託、不引 CDN；build 時只抓台灣周邊瓦片（z8–z11、**per-zoom bbox——見「底圖視野擴展」節**；`build/_tile_cache/` 持久化、缺什麼補什麼），完全離線、零外部請求；不跑 OSM tile server，出範圍顯示**海色底**（`#aad3df`）＋`errorTileUrl` 佔位，不再露紙色。
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
   - **4a 雨量站點層（2026/9/16 起）**：O-A0002-001 超閾值測站→三級點層（p1hr/p24hr ≥50/250 🔴、≥25/100 🟠、≥10/50 🟡；2026/9/16 真實資料校準：淡雨日 0/1/13 站）。座標取 **WGS84**（`GeoInfo.Coordinates[CoordinateName=WGS84]`，不可用 TWD67）；`cwa.fetch_rain_points()` 為單一事實來源。——**代碼已完成（2026/9/16）、真瀏覽器實測全點渲染正常**（obscura 無法渲染 Leaflet SVG，驗證流程見下方「/map/ 向量層驗證（Playwright）」節）；點樣式未過關→見 4a-follow。
   - **4a-follow 雨量點樣式重做（🔥高優先、合併 4a 後先處理；2026/9/16 使用者初審未過）**：使用者實際螢幕判斷——① 圓形仍太小；② 暖橙/琥珀色系（現行 #dc2626/#ea580c/#f59e0b）仍與 OSM 底圖幹道粗橘線（含交流道/匝道交會處的橘色三角形樣小塊）混淆、干擾視覺判斷。底圖橘線是 OSM 標準 tile 自帶、不可控→點顏色必須避開色相 ~20-40° 橘系；候選方向待討論後再動手（冷藍系【注意巨浪告警 cyan 層衝突＋海水淡藍】、深色單色＋白環＋標註、加大尺寸等）。 ——**✅ 2026-10-26 定案並實作（三級配色/尺寸/淡色底點/命中圈），見下方「雨量點樣式重做（§2-4a-follow）」節**
   - **4b 颱風軌跡／風圈層**：W-C0034-005 觀測軌跡（實線）＋預報軌跡（虛線）＋最新預報點風圈圓環（空狀態＝無活動氣旋時圖層空，沿用「空＝查過」原則）。——**✅ 2026-10-28 定案並實作**，見下方「颱風軌跡／風圈層（§2-4b）」節（風圈改用象限非正圓、多加 70% 暴風半徑環、圖境外提示列）。
   - **4c 特報陸地紅區層**：W-C0033-002/003 文字影響區域→**選項 A 縣界 GeoJSON 自託**（2026/9/16 定案；gazetteer 無邊界多邊形）；生效時段標籤（「今夜起」等）。
5. ~~2b 災情新聞點層（人工餵料）~~ 暫緩（見 §2b）
6. v2：`/map/data.json` 公開＋deep link＋時間線快照

## 底圖視野擴展（§2-7，🔥 高優先、2026/10/26 定案）

**使用者回報**：台灣島右方（東側）覺得「沒有繪製地圖」、視野狹隘。實測確認不是知覺問題：

| 事實 | 位置 | 實測 |
|---|---|---|
| 離線瓦片東界 **122°E** | `build/tiles.py` `BBOX` | 台灣東岸就在 121.9–122.0°E→**瓦片東界＝台灣東岸**，台灣以東幾乎沒有海（龜山島 122.05°E 已在界外） |
| 但畫面能看到 **~124.9°E** | `build/map_page.py` `MAP_MAX_BOUNDS` 東界 123.6°E | z8 桌面視口寬於 maxBounds 經度跨度（5.3°）、被 clamp 到中心 120.95°E→1440px 視窗（7.9°）可見 117–124.9°E |
| → 最右 **~2.9°（≈530px、佔 1440px 視窗 37%）無瓦片** | 122→124.9°E | 即使用者看到的「沒畫完」 |
| 缺瓦片處畫成**紙色**不是海色 | `#map`／`.leaflet-container{background:var(--bg)}` | light `#f9f3eb`／dark `#14181c`；且 tileLayer 無 `errorTileUrl`（缺檔＝404） |
| ⚠️ 舊註解不實 | `map_page.py` 原稱 maxBounds「仍在離線瓦片覆蓋 118–122°E 內」 | **錯**（123.6 > 122.0）——就是這個漏洞的來源，本批一併更正 |

**定案（三標；首批＝ a＋b 同批上線，c 待辦）**

1. **a 海色止血**：`#map`／`.leaflet-container` 背景 `var(--bg)` → **OSM standard 海洋 `#aad3df`**（OSM 瓦片本身不隨 theme 變色→light/dark 同色）；tileLayer 加 `errorTileUrl`。缺瓦片處從白紙變海。⚠️ 當時用的 `tiles/_ocean.png` 是**不透明**海色 PNG，2026-10-27 已改**全透明** `tiles/_blank.png`（不透明版會蓋住 §2-7c 兜底陸地層）；海色改由容器背景 `--sea`（＝`tiles.OCEAN_CSS`）提供。
2. **b 視野＋瓦片往東/南擴**：
   - `MAP_CENTER` `[23.8, 120.95]` → **`[23.7, 121.3]`**（往東 0.35°，台灣在畫面偏左、右側留太平洋）
   - `MAP_MAX_BOUNDS` → **`[[20.7, 118.3], [26.7, 124.3]]`**（6.0°×6.0°，**中心恰＝新 `MAP_CENTER`**）
   - `tiles.py`：單一 `BBOX` 常數拿掉，改由 `zoom_bbox(z)` **推導**每一層 bbox＝`MAP_MAX_BOUNDS` ⊕ 該層桌面視口溢出量 ⊕ `ELASTIC_DEG`（0.3°）。實測產出：z8 `(115.73,20.10,126.87,27.30)` 63 張、z9/z10/z11 `(118.00,20.40,124.60,27.00)` 121/420/1,596 張。
     **`MAP_CENTER`/`MAP_ZOOM`/`MAP_MAX_BOUNDS` 的單一事實來源改放 `build/tiles.py`**，`map_page.py` 由此 import（舊版兩處各寫一份、就是漂移的溫床）。
   - 原理（**不變項**）：⚠️ 每一 zoom 層的瓦片 bbox 必須涵蓋「視口可能到的範圍」，否則該處只剩海色底——低 zoom 時桌面視口比 maxBounds 寬（z8 1920px＝10.6° 經度 > bounds 6.0°）需要更寬瓦片帶，高 zoom（z11 1920px＝1.3°）視口比 bounds 窄、蓋 maxBounds 即可；`MAP_MAX_BOUNDS` 中心恆等於 `MAP_CENTER` 的不變項繼續成立。
   - **成本（2026/10/26 實測）**：**2,200 張**（舊 967）、`public/assets/tiles` 由 15 MB → **25 MB**（先前估 1,818 張≈ 9 MB 偏樂觀——OSM.de 的海域瓦片帶等深線/離島標註，單張仍有數 KB）。本次新抓 1,233 張、8 workers、build 總時 1 分 54 秒、失敗 0。仍遠低於 CF Pages 檔案/檔案大小上限。⚠️ `WORKFLOW.md` §3 ⑤ 已改為「先跑 `tiles.tile_list()` 查現值再對數」（瓦片數不再寫死）。
3. **c 陸地輪廓兜底（✅ 2026-10-27 實作完成、詳見下方「兜底陸地層」節）**：海色＋陸地輪廓最底層（獨立 pane、zIndex 低於 tilePane）。⚠️ **實際做法偏離原定案**：沒有擴充 `ISLANDS`（那 6 條是手描、專供**事件頁 SVG**、精度 5 位，給主島复用會被降到 4 位），而是新增獨立常數 `FALLBACK_LAND`（**Natural Earth 10m land**、經裁剪＋簡化，已含巴丹/與那國/宮古/石垣/大陸岸）。⚠️ 改視野要改**產生器** `make_taiwan_geo.py`，手改 `taiwan_geo.py` 會被覆寫（AGENTS.md 已警示）。也順帶服務 §2-4b（風圈畫到瓦片外仍有地理參照）。

**為什麼不只是美觀**：cbph **巨浪告警 polygon** 與待辦 **§2-4b 颱風軌跡/風圈**都在台灣**以東**海域——現行底圖在那邊是空白，預報路徑與 70% 暴風半徑會畫在「沒有地圖」的白區上，直接傷害本專案核心用途。

**與 4a-follow 的順序**：§2-7 先做。4a-follow 卡在「冷藍系與海水淡藍衝突」的判斷，而海洋面積一旦擴大 2.3°，點/海對比的前提就變了——先定視野與海色再定點色，才不會返工。

### a＋b 實作完成與實測（2026/10/26，DEV）

**改動**：`build/tiles.py`（視野常數＋`zoom_bbox()` 推導＋`ocean_png()` 手寫 stdlib PNG、不依赖 Pillow）、`build/map_page.py`（import 視野常數、`--sea:#aad3df`、`#map`/`.leaflet-container` 改用海色、tileLayer 加 `errorTileUrl`）、`WORKFLOW.md` §3 ⑤。

**本機 build**：`map tiles：2200 張（本次抓 1233、快取 967、失敗 0）`、零 warning；`_ocean.png` 570 bytes、實色 rgb(170,211,223)；舊快取 967 張全在新計畫內（無孤兒瓦片）。

**真 Chromium 驗證**（依本檔「/map/ 向量層驗證」規則，不用 obscura；`NODE_PATH=/root/opencode-stuffs/translate-cloud/node_modules`，playwright 1.64 對應 `chromium-1248`）：

| 視窗 | 可見經度 | 瓦片實際 covered 東界 | 右側缺口 | 404 |
|---|---|---|---|---|
| 1920×1080 | 116.03→126.57 | 126.56 | **0.01°** | 0 |
| 1440×900 | 117.34→125.26 | 125.16 | **0.10°** | 0 |
| 390×844（手機） | 120.23→122.37 | 123.75 | **0.00°** | 0 |

另外測 z11 拖到 maxBounds 四邊（東/西/南/北各拖到底）：全部零 404、海色佔位瓦片 0 張 → **可拖範圍內瓦片完整**。`.leaflet-container` 與 `#map` 實測 `rgb(170,211,223)`＝海色 ✓。截圖目視：右側出現石垣市/西表石垣國立公園（z8）與與那國町、沖繩縣界（z11）——不再是一片空白。

⚠️ 副作用：`public/assets/tiles` 25 MB（部署變大，CF Pages／gh-pages 同步時留意上傳時間）。原註「2560px 以上 ultrawide 在 z8 最外側會露海色」——⚙ **2026-10-27 實測更正**：z8 瓦片實際涵蓋 **115.31–127.97°E**（`tiles.tile_list()` 實際網格，比 `zoom_bbox()` 的 115.73–126.87 更寬，因網格以 1.4° 對齊），所以 2560 視窗在 z8 **只有左側約 18px（≈0.1°）缺瓦片**（右側不缺），該處已由 §2-7c 兜底陸地層補上海岸線（見下方「兜底陸地層」節的 on/off 截圖差異 0.405%、差異全在 x 3–18）。真正會露出海色的主要場景是**瓦片抓取失敗**與**未來改 `ZOOMS`/`MAP_MAX_BOUNDS`**。

⚠️ 2026-10-27 更正（做 §2-7c 時才發現）：上述 `_ocean.png`（570 bytes、實色）已廢——不透明的佔位底住在 tilePane 裡，會**蓋住下方的兜底陸地層**。現行＝全透明 `_blank.png`，見下方「兜底陸地層」節。

## 兜底陸地層（§2-7c，✅ 2026-10-27 實作完成、已合併 `main` ＋ 上線正式站）

**做什麼**：瓦片缺一張（build 時抓失敗、或 future 視野超出瓦片覆蓋）時，`errorTileUrl` 只補海色 → 該處**連陸地一起消失**，包括台灣自己。這層在 tilePane **之下**補上「可能露出瓦片缺口的範圍」內的陸地輪廓（Natural Earth 10m land，公有領域）。日常瀏覽時瓦片齊全 → 這層**完全不顯示**（實測見下），它的價值在兜底與 §2-4b（風圈畫到瓦片外仍有地理參照）。

**改動（三處，第三處是連動修 bug）**

1. `build/make_taiwan_geo.py`：新增 `fallback_land()`。目標範圍＝`tiles.zoom_bbox()` 各層聯集 ⊕ `FALLBACK_MARGIN_DEG`（0.5°）——**推導而非寫死**，與離線瓦片同一事實來源。新工具：`clip_rect()`（Sutherland–Hodgman 矩形裁剪；先 bbox 粗篩再裁剪，大陸的環動輒數萬點）、`douglas_peucker_iter()`（**迭代版**DP——本檔原有的遞迴版對大環會爆 recursion limit）。產出新常數 `FALLBACK_LAND`。
   **實測**：79 環／1,702 點／inline **36 KB**（台灣本島 207 點、大陸福建岸、與那國/西表/石垣/宮古、菲北巴丹 4 環都在）；`ISLANDS` 段與 HEAD **位元組相同**→ 事件頁 SVG 不受影響。⚠️ eps 必須**面積自適應** `min(0.003, max(0.0004, 0.12·√area))`：固定 0.003° 會把與那國/宮古這類小島整個簡化掉（實測丟 9 環）。
2. `build/map_page.py`：`LAND_STYLE`（顏色單一來源、用**字面 hex**不用 `var()`——Leaflet 把 color/fillColor 寫進 SVG 顯示屬性，`var()` 在部分瀏覽器無效，與 4a-follow 同一教訓）；`map.createPane("land")` ＋ `zIndex=1`（⚠️ 是 **1** 不是 2：tilePane 的 z-index 來自 `leaflet.css` 的 **200**，不是「Leaflet 預設 2」）；每 ring 一條 `L.polygon(..., {pane:"land", interactive:false})`；(lon,lat)→[lat,lng] 在 build 端轉一次。
3. ⚠️ **連動缺陷修正**：`errorTileUrl` 原本是**不透明**海色 `_ocean.png` → 它就畫在 tilePane 內，**蓋住了下方的兜底層**，這層永遠不會顯示（發現於本輪實測）。改成 **全透明** 256×256 RGBA `_blank.png`（`tiles.blank_png()`，PNG color type 6，334 bytes），海色改由容器背景 `--sea` 提供。海色收斂成單一來源 `tiles.OCEAN_RGB → OCEAN_CSS`，`map_page` 兩處寫死的 `#aad3df` 改用 `@SEA@` 佔位代換；舊 `_ocean.png` 由 `fetch_tiles()` 主動從 public/ 清掉（免上傳舊檔）。

**真 Chromium 實測**（playwright 1.64／chromium-1248，依本檔驗證規則）

| 項目 | 結果 |
|---|---|
| pane 堆疊 | land `zIndex=1`（inline）< tile（leaflet.css 200）< overlay 400 ✓ |
| 瓦片齊全時是否干擾 | on/off 截圖差異：1440×900 **0.000%**（0/144,000 取樣）；2560×1440 **0.405%** 且差異全在 x 3–18（＝左側瓦片界外，顯示大陸海岸）→ **只在瓦片缺口處露出** ✓ |
| 瓦片全 404（route abort，僅 `_blank.png` 可載入）像素探針 | 台灣本島 `#f2efe9` ✓、澎湖 ✓、石垣 ✓、與那國 有陸色像素（z8 僅 1–2px）✓、大陸岸 陸海各半（岸線）✓；**開闊太平洋／台灣海峽 純海色 `#aad3df`**（無假陸地）✓ |
| 陸地面積合理性 | land-only 截圖陸色取樣 20,728／324,000 ≈ **6.4%**（舆此窗陸海面積相符） |
| 效能 | 3 次縮放（z8→z11）＋4 次拖曳：longtask **0 筆**；新增 path 僅 79 條（overlay 2,622 不變） |
| 手機 390×844 | 瓦片 9 張、land path 79、console error 0 |
| build／體積 | 2,200 瓦片全快取命中、零 warning；`_blank.png` 334 bytes RGBA alpha=0；`public/` 14.02 MiB／2,241 檔（**檔數不變**）、最大單檔 1.18 MiB（CF Pages 25 MiB 上限的 **4.7%**） |

**測試站部署＋線上複驗（2026-10-27 15:11 build → `wea-testing`，帶 `--branch main`）**：`weatesting.avpclub.eu.org/map/` 與 `/ja/map/` 皆 land **79 paths**（pane z=1）、tile z=200、overlay 2,620 paths、容器底色 `rgb(170,211,223)`、land pane 內 `leaflet-interactive` **0**（不搶命中）；`_blank.png` HTTP 200／334 bytes／PNG colorType **6**（RGBA）；正常載入**零 4xx、零 console error**（load 2.0 s）。用 `ctx.route(/\/assets\/tiles\/\d+\//, r => r.abort())` 模擬瓦片全滅 → 20 張 errorTile 全走透明佔位底、台灣/澎湖/石垣/與那國 可見（截圖 `/tmp/live_tiles404.png`）。**對照正式站**（`weather.avpclub.eu.org/map/`）：land 0 paths、HTML 仍含 `_ocean.png` → 符合「DEV 尚未合併」的预期。

**正式站上線後複驗**（2026-10-27 15:49 透過 `build/deploy-cron.sh` 於部署機手動跑一次，`rc=0`；build：2,200 瓦片全快取命中、失敗 0、零 warning）：四个託管（`weather.avpclub.eu.org`／`.uk`／`.larch.dpdns.org`／`lawlietr.github.io/Weather`）＋ ja 頁皆 **land 79 paths（pane z=1）＜ tile z=200 ＜ overlay 2,632 paths**、容器底色海色、`_blank.png` HTTP 200／334 B／colorType 6、land pane 內命中 0、**零 4xx、零 console error**（load 1.0–2.1 s）。瓦片全滅情境（route abort）：三邊都看到 20 張 errorTile 全走透明佔位底、兜底 land 79 條可見。

⚠️ **上線時發現並已修：GitHub Pages 鏡像會漏掉 `_` 開頭的資產**。實測 `_blank.png` 在鏡像上 404（同路徑在 CF 200），而 `map/index.html`、`assets/tiles/8/214_110.png`、`leaflet.css` 均 200，gh-pages tree 內唯一的 `_` 開頭檔就是它——gh-pages 屬於 Pages 的 **branch 來源**，GitHub 會跑 Jekyll，而 Jekyll 忽略 `_` 開頭的檔/資料夾（舊 `_ocean.png` 也一直在鏡像上 404，只是没人發現）。修法：`site.py` 於站根產空檔 **`public/.nojekyll`**（commit `94963c6`），重新部署後鏡像 `_blank.png` 已是 200、`.nojekyll` 200。`public/` 2,242 檔／14.03 MiB。

**邊界與坑（改視野前必读）**
- 兜底層只蓋 `zoom_bbox` 聯集 ⊕ 0.5° ＝ **(115.2, 19.6)~(127.4, 27.8)**。窗外不含：沖繩本島（127.7°E）、呂宋 main（18.5°N 以南）、東沙（116.7°E 已在窗内但未在 NE 10m land 出小島）。
- ⚠️ **改 `tiles.MAP_MAX_BOUNDS`／`ZOOMS` 後必須重跑 `python3 build/make_taiwan_geo.py`**，否则兜底層不會跟著長——就是 §2-7「maxBounds 比瓦片寬」漂移教訓的翻版（產生器頭部已寫這條）。
- 矩形裁剪會在窗邊留下**沿裁剪邊的直線邊**（大陸/大島被窗切開處），屬預期，該處本就是視野邊緣。
- 來源授權：Natural Earth 公有領域（與 `ISLANDS` 同）；不需署名但也無需隱晦。
- ⚠️ **檔名以 `_` 開頭 → GitHub Pages 鏡像會 404**（2026-10-27 實測）：gh-pages 是 orphan 分支直推＝Pages 的 **branch 來源**，GitHub 對 branch 來源會跑 Jekyll，而 Jekyll **忽略 `_` 開頭的檔/資料夾**——實測 `assets/tiles/_blank.png` 在 `lawlietr.github.io` 404、同一路徑在 CF 上 200（鏡像上瓦片與 `leaflet.css` 皆 200，tree 內唯一的 `_` 開頭檔就是它）。舊 `_ocean.png` 也一直在鏡像上 404（只是從沒人發現）。**修法：`build/site.py` 已在站根產 `public/.nojekyll`（空檔）關掉 Jekyll**；WORKFLOW §3 ⑤ 已加檢查。若日後再出現 `_` 開頭的資產，只要 `.nojekyll` 在就不會再被漏。

## 颱風軌跡／風圈層（§2-4b，✅ 2026-10-28 定案並實作，DEV 待合併）

W-C0034-005（已在 `cwa.load_snapshot()` 的 `typhoons` 內，**不额外打 API**）→ `map.geo.json` → `/map/`。
這是 §2-7／§2-7c 存在的理由本身：巨浪 polygon 與預報路徑都在台灣以東，沒底圖與陸地參考時根本讀不出來。

### 定案
- **單一事實來源分工**（同 §2-4a 的教訓）：顏色＝`cwa.TYPHOON_COLORS`（build 時寫進每個 feature 的
  `properties.color`）；怎麼畫＝`map_page.TYPHOON_STYLE`（線寬、虛線 pattern、填色、點徑、命中圈）。
  兩邊都不写第二份 hex。
- **顏色要避開整張圖已有的色**：cbph 四色（#f59e0b/#ef4444/#7c3aed/#0ea5e9）＋雨量三級
  （#be123c/#c026d3/#4338ca）＋淡點 #5b6b7b。定案：觀測軌跡 **#1f2937**（中性近黑實線）、預報軌跡
  **#b45309**（暗琥珀虛線，與 cells 的 #f59e0b 靠明度＋虛線拉開）、15 m/s 風圈 **#b91c1c**（細環，
  與 tywinds 的實心填充不同形）、70% 暴風半徑 **#475569**（石板灰環）。地圖畫布兩主題都是亮的
  （海 #aad3df／陸 #f2efe9）→ 一律用深色線條，且 Leaflet 把 color 寫進 SVG 顯示屬性 → 不得用 `var()`。
- **圖元 kind**（一個開關控整個氣旋層，`properties.type="typhoon"`）：`track_obs`（實線）、
  `fix_obs`（過往觀測點）、`center_obs`（最新觀測點）、`wind_obs`（最新點的 15 m/s 風圈）、
  `track_fc`（虛線，從最新觀測點接出）、`center_fc`（預報點，+6h…+120h）、`wind_fc`（最遠預報點的
  15 m/s 風圈）、`radius70`（最遠預報點的 70% 暴風半徑）。空心預報點＝「未來」，與事件頁 SVG 同一語意。
- **風圈不是正圓**：實測 `Circle15ms.QuadrantRadii.Radius[]` 的元素形態是 **`{"value","dir"}`**（不是
  `Quadrant`/`Radius`），且**四象限常常不相等**（煙花 2026-10-27 14:00 ＝ NE 180／SE 200／SW 160／
  NW 180 km；10-28 14:00 四值全等 180 → 該刻畫出來就是正圓，插值結果一致）。`cwa._wind_ring()`
  沿方位角 32 點線性插值成非正圓環；等圓柱近似（1° 緯≈110.574 km、1° 經≈111.320·cos φ），風圈
  ≤ 500 km 誤差可忽略，**不引入投影庫依賴**。預報 Fix 只有單值 `Radius`→ 正圓。TD 階段風圈整欄缺
  → 跳過該環（不炸）。⚠️ `_circles()` 與 `_fix_props()`（`MovingPrediction` 是多語 list）都要對形態異常
  免疫（實測觸發過 `AttributeError`）。另 note：`Radius70PercentProbability` **實為公里半徑、不是百分比**
  （煙花 +72h：r15 200 km／R70P 210）——欄位表已写進 `build/CWA_API.md`。
- **風圈只畫兩處**（最新觀測點＋最遠預報點），不是每個預報點都畫：9 個點×2 組環會糊成一團。
  中間點的半徑數值放進 `properties`，**點下去詳情卡就顯示**（含 `+24 小時` 時距標籤、四象限半徑、
  陣風、氣壓、`MovingPrediction` 原文）。70% 暴風半徑是 AGENTS 的建檔判準（「進入 70% 暴風半徑」），
  必須在圖上看得到。
- **點擊模型（2026-10-28 真 Chromium 復驗後定案，兩條都是必須、不得改回）**：
  1. 風圈 polygon 與軌跡白襯 `interactive: false`——一個半徑 400 km 的 70% 環若可點，會吃掉整片
     海洋上的測站點與告警 polygon 的點擊（§2-4a 淡點命中圈的同一教訓）。可點的只有線與中心點。
  2. 同層內 **線→圈→點** 排序（`typhoonLayer()` 先依幾何類型排過）：預報線起點就是最新觀測點，
     不排序時線在上層會搶走該處點擊，使用者看到只有一行的軌跡卡（實測踩到）。
  3. 整個氣旋層疊在**超閾值雨量點之上**（本輪改判，推翻 §2-4a 原本「超閾值點最上」）：真氣旋靠近
     時必伴隨超閾值雨量點（半徑可到 22 px），舊順序會讓這些點把軌跡線與風圈壓在下面——最需要看
     路徑的時候最看不清。代價只有「正正點在風中心或 3 px 細線上」時改拿到氣旋卡。淡點仍在最下、
     不搶 polygon 點擊（§2-4a 定案不變）。
     ⚠️ **疊放現在靠獨立 pane 的 zIndex 固定，不靠 addLayer 先後**（2026-10-28）：淡點 pane 390 <
     告警 polygon（overlayPane 400）< 超閾值點 pane 410 < 氣旋層 pane 420（瓦片 200、兜底陸地 1 不動）。
     理由：開關圖層＝removeLayer/addTo，後加回來的會被排到同一個 overlayPane 最後面——淡點改為
     預設關閉後，使用者勾開時必定排在其他層之後，舊寫法會讓 1,300 個淡點命中圈搶走 polygon 點擊
     （實測舊版「關掉再打開」就有這個順序跑位，只是沒人碰過）。**新層要畫在同一 pane 並傳 `pane:` 選項**。
  4. 軌跡線帶 7 px 白襯（`casing`）：3 px 細線畫在 cbph polygon（fillOpacity .35）上會被填色吃掉。
- **詳情卡與事件檔連動**：`repo_links` 對氣旋圖元改用**氣旋名／國際命名比對事件檔 `event:` 標題**
  （例：「颱風薔琵（CHAMPI）— 2026年第33號」）——氣旋沒有縣市欄（影響範圍是動態風圈不是縣市清單），
  舊的 counties 交集邏輯在這裡必定回空。
- **圖境外必須提示**（新增 i18n `map_ty_outside`／`map_ty_outside_note`）：`maxBounds` 東界 124.3°E，
  而 2026-10-28 的煙花在 **158.9°E** → 圖層有 36 個圖元但 0 個可見。不提示就等於讓使用者把
  「有颱風但在視野外」讀成「沒颱風」，與 §2-4a 淡點同一目的。右側欄現會顯示
  「🌀 底圖視野外還有 1 個活動氣旋：煙花（34 號） 15.1°N 158.9°E・51 m/s・WNW 18 km/h・2026-10-28 14:00」。
- **空狀態**：CWA 回空清單 → 不寫開關、圖層空（「空＝查過」，與 cbph 503 視為空清單同一原則）；
  抓取失敗由 `site.py` 記 warning，不會被當成「沒有颱風」。
- **i18n**：zh＋ja 各 20 個新 key（ja 經 Index-Translate 起草、再照本檔 ja 慣用語複核：氣旋一律
  「台風」、`暴風半径/暴風域` 跟 `legend_wind` 同形、不用「サイクロン」）。

### 實測（真 Chromium，Playwright 1.64／chromium-1248；用 `/tmp` 預覽儀，不入 repo）
真實煙花在 158.9°E＝視窗外，**無法用真實資料驗渲染**，故沿用 §2-4a-follow 的做法：把「合成氣旋」
（路徑刻意通過台灣東側、70% 環蓋住本島）＋兩筆合成 cbph polygon ＋ 4 筆合成超閾值雨量點注入
`/tmp/typreview/map/index.html`（真實瓦片＋真實測站網絡），另用真實輸出跑一次真實路徑。要點：
- 渲染：z8/z10/z11 皆清楚（暗琥珀虛線＋空心點＋深紅中心點＋白環＋兩層虛線環），ja 頁圖例/詳情卡全日文。
- 互動：點最新中心點→完整氣旋卡（含四象限半徑）；點預報線→起訖座標＋點數＋時距範圍；點預報點→
  該點數值＋`+120 小時`；tooltip 顯示 `測試氣旋（99 號） +120 小時`。
- 不搶點擊：三個風圈 `interactive:false`；風圈下方的超閾值雨量點**仍拿到雨量卡**；告警 polygon 仍可點。
- 疊放：`byType` 內 rain 圖元 paint index 2–9、typhoon 11–33（後者在上）✔。
- 圖層開關：關閉→path 數 −25；重開正常。真實輸出：36 個 typhoon path 建立、0 可見、console error 0。
- 效能：heap 14 MB、path 2,681（含 1,327 淡點）、無 longtask 異常。
- 真實 build：`map 颱風軌跡層：1 個氣旋／36 個圖元（煙花）`；斷鏈 0；`public/` 14.11 MiB／2,242 檔
  （+0.09 MiB，最大單檔 1.22 MiB＝CF 25 MiB 上限的 4.9%）；金鑰零外洩檢查通過。

### 尚未做（新增待辦）
- **§2-7d 向東擴 `MAP_MAX_BOUNDS`**：現在氣旋中心常在圖外（只靠上面的提示列）。擴充需同步重抓瓦片＋
  重跑 `make_taiwan_geo.py`（見上方 §2-7c 那條 ⚠️），且會再長大 `public/` —— 未做。
- 25 m/s 風圈（數值已在 properties，只是沒畫環）、預報中間點的風圈（現為只靠點擊看數值）、
  風圈／線隨縮放（現固定 px；雨量點的 `dot_zoom_factor` 機制未套用到這裡）。都不影響正確性。

## 雨量點樣式重做（§2-4a-follow，✅ 2026-10-26 定案、已合併 main ＋ 22:09 手動部署上線）

使用者 2026/9/16 初審未過（① 圓形仍太小 ② 暖橙/琥珀與 OSM 幹道粗橘線混淆）。2026-10-26 用
**真瀏覽器 close-up 比對**（真實測站座標＋合成數值，見下方「驗證」）定案，取代原 4a 的暖橙配色。

### 定案
- **三級色＝深靛藍 → 洋紅 → 玫紅**（`cwa.RAIN_LEVELS`）：L3 `#be123c` r17、L2 `#c026d3` r12、
  L1 `#4338ca` r9。保留「越嚴重越紅」語意，且避開 OSM 幹道/高快的橘（色相 ~20–40°）與
  §2-7 擴大後的海面淡藍 `#aad3df`。
- **半徑隨縮放**（2026-10-26 使用者改口：「地圖拉進後圈還是一样小、點擊不方便」，故先前
  的「先固定」作廢）。實作＝`map.on("zoomend")` → `rescaleRain()` 重算視野內（含 15% 邊界）的
  `setRadius`。兩個係數分開，**可見點溫和、命中圈激進**：
  `RAIN_STYLE.dot_zoom_factor` 1.2/級（上限 `max_radius` 22px 半徑）、
  `RAIN_STYLE.hit_zoom_factor` 1.6/級（上限 `max_hit` 30px 半徑 → z11 命中圈直徑 60px）。
  實測直徑（淡點／命中圈）：z8 8／22 → z9 10／36 → z10 12／56 → z11 14／60px；
  超閾值 L3 點 34→44px、命中圈 42→60px。每級都在「半徑 −3px」處點擊成功（實測）。
  ⚠️ 兩條 cap 是必要的：先試過 dot/hit 都用 1.45/級 → z11 淡點變 24px 直徑、1314 個淡點
  成一片灰碟蓋住底圖（截圖有，已改回溫和的 1.2）。
- **淡色底點＝未超閾值測站全部上圖**：`cwa.RAIN_BELOW`＝`#5b6b7b` r4、`RAIN_STYLE.below_fill`
  0.45、面板另有獨立開關。理由：CWA 全網絡 1314 站、淡雨日超閾值 0 站 → 舊版地圖一顆點都沒有，
  使用者無法分辨「查過但沒超標」與「壞了」（呼應「空圖＝查過」原則的可驗證底）。
  **但 2026-10-28 使用者定案：該開關預設不勾選**（平時 1,300+ 個淡點把底圖弄亂）——淡點仍進
  `map.geo.json`（需要時勾開就好、不重新 build），但預設不上圖；行尾的站數（1327）就是
  「查過但沒超標」的證據，不拿淡點當下線。JS 初始狀態跟隨 checkbox 的 `checked`（`addLayer()`），
  預設值只寫在 HTML 一處。
- **透明命中圈保留**（超閾值 `RAIN_STYLE.hit_min` 14px、淡點 `below_hit` 11px）——現行 r5 小點
  在手機上點不中；2026-10-26 使用者「先留，影響操作體驗再改」。

### ⚠️ 三個坑（改樣式前先看）
1. **點色不得撞 cbph 圖層官方色**：第一版 L1 用 `#7c3aed` ＝ cbph `mountainstorms`（山區暴雨
   警示 polygon）**完全同色**；L3 也不能用與 `tywinds` `#ef4444` 相近的亮紅（改 `#be123c`
   以明度拉開）。四色見 `cbph.TYPES`，改點色前先對表。
2. **疊放順序是刻意的**：淡點最下 → 告警 polygon → 超閾值點 → 氣旋層。否則 1314 個淡點的透明
   命中圈會蓋住 polygon，點 polygon 變成點測站。⚠️ 2026-10-28 起**用獨立 pane 的 zIndex 固定**
   （淡點 390 < overlayPane 400 < 超閾值點 410 < 氣旋 420），不再是 `pointPolys()`/`polyPolys()`
   的 addLayer 先後：開關圖層是 removeLayer/addTo，後加回來的會排到同 pane 最後面 → 舊寫法下
   「淡點預設關閉 → 使用者勾開」會把淡點拱到最上面（舊版關掉再打開也同一錯，只是沒人碰過）。
3. **HTML 屬性少一個引號會「吃掉」面板文字**：swatch 的 `style="…#fff` 沒關引號 → 瀏覽器一路吞
   到下一個 `"`，層名整個消失（面板只剩色塊＋計數）。build log、`check_links.py` 都不報，
   **只有真瀏覽器截圖看得到**。

### 效能（2026-10-26 真 Chromium，淡雨日全網絡）
- 1314 淡點＋命中圈＝**2628 個 SVG path**、DOM 2728、JS heap 14MB；`public/map/index.html`
  1.2MB（gzip 53KB）。longtask（>50ms）僅 2 個、最長 166ms；連放 3 階／拖圖無明顯卡頓
  → 1314 點規模可接受，**不需要**聚類或縮放閘控。關掉淡點層 → path 2628→0。
- 加了縮放重算後：連放 3 階（z8→z11）的 longtask 仍只有 1–2 個、最長 107–144ms（多發生在
  載入），**zoomend 的 2628 次 `setRadius` 自身沒進 longtask（<50ms/次）** → 不必聚類、
  也不必只更新視野外緩存。

### 驗證方式（今日 0 站超閾值＝沒有真色點可看，故用 /tmp 預覽儀；不入 repo）
- `/tmp/rain_preview.py`＋`/tmp/rain_focus.py`：7 組候選（circle/ring/pin × 多組配色/尺寸），
  真實測站座標＋合成數值，台中 z10 close-up（橘線最密處）比對 → 定案此路線。
- `/tmp/rain_dens.py`：淡點密度/透明度三組（r3/0.35、r4/0.45、r5/0.55）比較，截圖在
  `/tmp/raindens_shots/`。
- `/tmp/rain_day.py`：真實 1314 淡點＋14 顆合成超閾值點＋**假 cbph polygon**（今日四類 0 區，
  只能這樣壓測「色點畫在 polygon 上會不會同色分不清」）。
- `/tmp/rain_perf.js`、`/tmp/rain_online2.js`：效能與測試站（wea-testing）面板/開關/點擊驗證。
- ⚠️ 「真超閾值色點」的實地外觀仍要等自然豪雨/颱風日再目視一次——合成預覽不等於實測。
- 上線後（2026-10-26 22:09 手動 `build/deploy-cron.sh`）生產站複驗：`/map/`＋`/ja/map/` 淡點 1314、開關 path 2628→0、點淡點開詳情（美和站，含近 1hr/24hr/本日累計/觀測時間）、ja 層名已是日文、console/pageerror 無；同站連結 251 條 0 斷鏈、側欄 map 導覽 2/2。

### 順帶修（同一批）
`/ja/map/` 的四個告警層名稱原本是中文（`cbph.TYPES` 只帶中文名）→ 圖層標籤改走 i18n
（`map_layer_{slug}`；日譯經 Index-Translate 後複核：大雷雨速報／台風強風警報／山間部豪雨警報／
高波警報）。

### 尚未做（4a-follow 收尾）
- 淡點在 z8 若嫌蓋到地名 → 調 `RAIN_BELOW.radius`／`RAIN_STYLE.below_fill`（三組截圖已備）
- 若仍覺得不好點：`hit_zoom_factor`（現 1.6）與 `max_hit`（現 30px 半徑）是兩個獨立旋钮，
  只調其中一個即可（調 factor 影響中低縮放、調 cap 影響最深縮放）

## 中心偏移修正（✅ 2026/9/16）

初版開圖中心偏西 0.9°（設計 `MAP_CENTER [23.8, 120.95]`、實際 `[23.8, 120.05]`，桌面全寬皆中、手機不受影響）。根因：Leaflet 1.9.4 `setView` 對 `maxBounds` clamp，當**視口寬度超過 maxBounds 經度跨度**（z8 約 >965px＝所有桌面）時會把整個視口**重新對齊到 maxBounds 中心**——舊 bounds 中心經度恰好 120.05。修正：`MAP_MAX_BOUNDS` 改 `[[20.9,118.3],[26.7,123.6]]`（中心＝`MAP_CENTER`、總跨度不變、**聲稱**仍在離線瓦片覆蓋內）。**不變項：`MAP_MAX_BOUNDS` 中心必須恆等於 `MAP_CENTER`**。（⚠️ 2026/10/26 更正：當時那句「仍在離線瓦片覆蓋內」不實——123.6°E 已超出瓦片東界 122°E，由此產生 §2-7 的右側空白；新 bbox 策略見上方「底圖視野擴展」節。）

## cbph 503 假警報（✅ 2026/9/13 修復、已合併 main）

**問題**：cbph API 對「**目前沒有生效中告警的類型**」回 HTTP 503（非空陣列）——此行為 2026/9/1 已實測並寫入 `AGENTS.md` 陷阱清單與 `build/cbph.py` docstring，但實作只做到「不中斷 build」、**沒做到「不算 warning」**：`fetch_alerts()` 對所有錯誤一律寫入 `warnings`，`build/map_page.py` 又將每條 warning 渲染成地圖頁 ⚠️。結果：某類型無告警＝使用者在 `/map/` 看到誤導性的「cbph {type}: 抓取失敗（HTTP 503）— 跳過」。

**實測例證（2026/9/13，正式站地圖）**：largesurfs（巨浪）無生效中告警 → 503；同刻 cells／tywinds／mountainstorms 皆 200。純表面問題（其餘三層正常、build 成功），但誤示「資料源故障」。

**修復（已定案並實作）**：`build/cbph.py` 一處小改（約 10 行）——`CbphFetchError` 帶 `status` 屬性；`fetch_alerts()` 對 503/404 視為該類型空清單（只打 `[info]`、不進 `warnings`）；4 類全 503/404 時記一條「可能 cbph 服務異常」全站 warning（防靜默）。單元測試 5/5（stub `_get_json`）；真實 build：largesurfs 503 → `[info]`、零 warning、地圖頁無「抓取失敗」。已部署測試站 wea-testing 驗證。2026/9/13 合併 main。

## /map/ 向量層驗證（Playwright，2026/9/16 定案）

**規則**：`/map/`（Leaflet 向量層）驗證一律用 Playwright 真 Chromium，**不要用 obscura 截圖判層**——obscura 引擎缺 SVG 1.1 factory API（`createSVGRect` 等）→ `L.Browser.svg === false` → 所有向量層（雨量圓點、告警 polygon）不渲染且無 console 輸出，截圖會假陽性「圖層空」。obscura 的 SVG/console 缺陷已備妥 bug 報告文本待回報。

**Playwright 跑法（2026-10-26 實測更正）**：用 `NODE_PATH=/root/opencode-stuffs/translate-cloud/node_modules node <script>`（playwright **1.64.0**，對應本機快取 `~/.cache/ms-playwright/chromium-1248`）。
⚠️ 舊指引寫的 `steam-deck-utilities/web/node_modules` **目前跑不起來**：那組是 playwright **1.62.1**，要 `chromium_headless_shell-1234`，本機快取只有 1248 → `browserType.launch: Executable doesn't exist`（2026-10-26 實測踩到）。

**驗證要點**：`.leaflet-overlay-pane path.leaflet-interactive` 的數量＋fill 顏色分佈＋實際中心座標（可用 tile src 座標反算）。

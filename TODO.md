# TODO：任務帳本

> 本檔只記**要做的事＋優先級＋狀態＋設計檔連結**；問題背景、定案細節、規格與陷阱在 `design/<功能>.md`（每功能領域一份）；流程 runbook（更新／build／驗證／部署）在 `WORKFLOW.md`。已完成項目的歷史細節看 git history。
> 編號為傳統編號（§N），供既有引用對照；細節一律跟連結進 design/。
> 最後更新：2026-10-27（**§2-7c 兜底陸地層完成——在 `DEV`，尚未合併 main／未部署**；順帶修正 §2-7a 的 `errorTileUrl` 缺陷（實色海色底會蓋住陸地 → 改全透明 `_blank.png`）。同時修正舊帳目錯誤：§2-7 a+b 已於 2026-10-26 合併 main 並上線（舊行寫「待合併」＝過時）→ 移入已完成；§2-4b 的前置（先做 2-7c）已滿足。前次 2026-10-26：§12 斷鏈修復 129→0；拆檔歷史見 2026-09-16：§2→`design/map.md`、§5→`design/share-button.md`、§6→`design/class-halt.md`、§1→`design/rss.md`、§3/§4/§7/§9/§10/§11→`design/site.md`；本檔瘦身為帳本）

## 待辦（依優先級排序）

| # | 任務 | 優先級 | 狀態 | 設計檔 |
|---|------|--------|------|--------|
| §2-4b | 颱風軌跡/風圈層（實線觀測＋虛線預報＋最新預報點風圈） | 🔥 高 | 待辦。⚠️ 舊行「需先做 §2-7c」的前置**已滿足**（§2-7c 2026-10-27 完成、在 DEV）→ 風圈畫到瓦片外仍有陸地參考 | [design/map.md](design/map.md) |
| §2-4c | 特報陸地紅區層（選項 A：自託縣界 GeoJSON；**動工前需確認縣界資料源**） | 高 | 待辦 | [design/map.md](design/map.md) |
| §2-2b | 災情新聞點層（人工/agent 餵料，gazetteer 已備） | 中 | 暫緩（2026/9/1 定） | [design/map.md](design/map.md) |
| §2-6 | /map/ v2（data.json 公開＋deep link＋時間線快照；**快照需先定案**存哪裡、留幾份） | 中 | 待辦 | [design/map.md](design/map.md) |
| §6 | 停班停課事件檔存檔層（**事件期間才做**、非待辦；新事件時從 feed/查詢頁/新聞撈入事件檔「停班停課」章節） | 中高 | 事件期間進行 | [design/class-halt.md](design/class-halt.md) |
| §5 | 事件分享按鈕：A Web Share＋複製連結 → B Line 一鍵 → C OG 分享圖卡 | 低 | 待辦 | [design/share-button.md](design/share-button.md) |
| §1 | RSS 關鍵詞微調（`rss.py` `KEYWORDS`；隨事件期間 flag 假陽性/假陰性實戰資料，非獨立待辦） | 隨事件 | 隨事件維護 | [design/rss.md](design/rss.md) |

## 已完成（非待辦；細節在設計檔與 git history）

| # | 項目 | 完成 | 設計檔 |
|---|------|------|--------|
| §2-1~3 | 地圖紅警基礎（gazetteer、cbph 抓取→map.geo.json、/map/ 骨架＋離線瓦片＋自託 Leaflet） | 2026/9/2 | [design/map.md](design/map.md) |
| §2-4a | 雨量站點層初版（三級點層＋側欄圖例＋詳情卡；樣式待 4a-follow 重做） | 2026/9/16 | [design/map.md](design/map.md) |
| §12 | **站內斷鏈修復**：信任頁缺深度前綴、ja 樹的站根產物（llms.txt／sitemap）與語言切換按鈕差一層、事件正文的 `.md` 互連未改寫為事件頁；新增 `build/check_links.py` 當 build 後驗證工具（WORKFLOW §3 ②）。實測 **129 條 → 0 條**、build 零 warning | 2026-10-26 | [design/site.md](design/site.md) |
| §2-7 a+b | 底圖視野擴展：`MAP_CENTER` 向東 0.35°、`tiles.py` per-zoom bbox **推導**（MAP_MAX_BOUNDS ⊕ 視口溢出 ⊕ 0.3° elastic）、離線瓦片 967→**2,200 張**（15→25 MB）、缺瓦片處改海色底（修了舊缺陷：`MAP_MAX_BOUNDS` 比瓦片覆蓋寬→右側 1.6° 一直只有海）。真 Chromium 驗 1920/1440/390 與 maxBounds 四邊拖曳＝零 404 | 2026-10-26（已合併 main＋上線；commit `07e3ec4`） | [design/map.md](design/map.md) |
| **§2-7c** | **兜底陸地層**：獨立 pane（zIndex **1** < tilePane 200）＋ Natural Earth 10m land 經裁剪/簡化 → 新常數 `FALLBACK_LAND` 79 環／1,702 點／**36 KB**，範圍由 `tiles.zoom_bbox()` 推導（⚠️ 改 `MAP_MAX_BOUNDS`/`ZOOMS` 後**必須重跑 `build/make_taiwan_geo.py`**，否則兜底層不跟著長）。⚠️ 順帶修 §2-7a 舊缺陷：不透明海色佔位底 `_ocean.png` 在 tilePane 內、會蓋住陸地層→改全透明 `_blank.png`（海色改由 `--sea`＝`tiles.OCEAN_CSS` 注入）。真 Chromium 實測：瓦片齊全時 1440×900 差異 **0.000%**（完全被蓋）、2560×1440 仅 0.405% 且全在左側瓦片界外；瓦片全 404 時台灣/澎湖/石垣顯陸色、開闊太平洋/台灣海峽純海色（無假陸地）；3 縮放＋4 拖曳 longtask **0**；`public/` 14.02 MiB／2,241 檔（檔數不變）、最大單檔 1.18 MiB（CF 25 MiB 上限的 4.7%） | **2026-10-27（在 `DEV`；已部署測試站 `wea-testing` 並線上複驗通過；尚未合併 `main`／正式站未上線）** | [design/map.md](design/map.md) |
| §2-4a-follow | **雨量點樣式重做定案**：三級改「深靛藍 #4338ca → 洋紅 #c026d3 → 玫紅 #be123c」（避開 OSM 橘線與 cbph 四色）、半徑 11/8/5→9/12/17 且**隨縮放**（可見點 1.2/級、命中圈 1.6/級，z11 命中圈直徑 60px）、未超閾值測站全網絡淡色底點（`RAIN_BELOW`＋面板開關）、命中圈保留；樣式收斂成 `RAIN_STYLE` 單一來源。真瀏覽器 close-up 比對 7 組候選後定案（效能：2628 path／heap 14MB／longtask 最長 166ms）。已合併 main ＋ 22:09 手動部署上線，生產站複驗通過 | 2026-10-26 | [design/map.md](design/map.md) |
| §6-自動層 | 停班停課 DGPA CAP feed 首頁卡（is_current 判斷、置頂/置底、容錯） | 2026/9/15 | [design/class-halt.md](design/class-halt.md) |
| §1 | RSS 災情抓取（半自動：build 產候選清單、人工審查後入事件檔） | 2026/8/30 | [design/rss.md](design/rss.md) |
| §7 | 颱風動態區塊淘汰機制（TYPHOON_STALE_HOURS 24h、海上警報豁免） | 2026/9/13 | [design/site.md](design/site.md) |
| §8 | cbph 503 假警報修復（503/404 視為空清單、不進 warnings） | 2026/9/13 | [design/site.md](design/site.md) |
| §9 | 氣象總覽卡片排序（無活動氣旋時颱風卡置底、stale 例外頂位） | 2026/9/13 | [design/site.md](design/site.md) |
| §10 | 零星災情縣市分組寫法（A/B 並用、判斷標準＝事件 status） | 2026/9/15 | [design/site.md](design/site.md) |
| §11 | AI bot 可偵測性強化（JSON-LD、OG、信任頁、404 指引、llms.txt） | 2026/9/15 | [design/site.md](design/site.md) |
| §3 | ja 產出保留＋隱藏語言切換按鈕（機翻彙整文字作廢） | 2026/9/15 | [design/site.md](design/site.md) |
| §4 | 平常時期區域性天氣報導（❌ 不採：偏離事件＋災情定位、靜態站無在地化能力） | 2026/9/15 | [design/site.md](design/site.md) |



# TODO：任務帳本

> 本檔只記**要做的事＋優先級＋狀態＋設計檔連結**；問題背景、定案細節、規格與陷阱在 `design/<功能>.md`（每功能領域一份）；流程 runbook（更新／build／驗證／部署）在 `WORKFLOW.md`。已完成項目的歷史細節看 git history。
> 編號為傳統編號（§N），供既有引用對照；細節一律跟連結進 design/。
> 最後更新：2026-10-28（**§2-4b 颱風軌跡／風圈層 ＋ 淡點改預設不勾選，兩者皆只在 `DEV`、尚未合併 `main`／未上線**；衍生新待辦 **§2-7d：底圖再向東擴**——現在氣旋中心多在 124.3°E 以外，只有側欄提示列可見。前次 2026-10-27：**§2-7c 兜底陸地層已合併 `main` 並上線正式站**（四託管＋ja 皆複驗通過；順帶修 §2-7a 的 `errorTileUrl` 缺陷——實色海色底會蓋住陸地→改全透明 `_blank.png`）。**另發現並修好一個镜像缺陷**：GitHub Pages（branch 來源＝跑 Jekyll）會忽略 `_` 開頭資產→ `_blank.png`（與舊 `_ocean.png`）在 `lawlietr.github.io` 一直 404，現由 `site.py` 在站根產 `public/.nojekyll` 解決。兩項皆已上線。前次 2026-10-26：§12 斷鏈修復 129→0；拆檔歷史見 2026-09-16：§2→`design/map.md`、§5→`design/share-button.md`、§6→`design/class-halt.md`、§1→`design/rss.md`、§3/§4/§7/§9/§10/§11→`design/site.md`；本檔瘦身為帳本）

## 待辦（依優先級排序）

| # | 任務 | 優先級 | 狀態 | 設計檔 |
|---|------|--------|------|--------|
| §2-7d | 底圖**再向東擴** `MAP_MAX_BOUNDS`（§2-4b 上線後的衍生項：氣旋中心常在 124.3°E 以外，現在只能靠側欄「圖境外活動氣旋」提示列；擴充需同步重抓瓦片＋**重跑 `make_taiwan_geo.py`**，`public/` 會再長大） | 中 | 待辦（未定案：擴到多少度、瓦片体積 trade-off） | [design/map.md](design/map.md)「尚未做」 |
| §2-4c | 特報陸地紅區層（選項 A：自託縣界 GeoJSON；**動工前需確認縣界資料源**） | 高 | 待辦 | [design/map.md](design/map.md) |
| §2-2b | 災情新聞點層（人工/agent 餵料，gazetteer 已備） | 中 | 暫緩（2026/9/1 定） | [design/map.md](design/map.md) |
| §2-6 | /map/ v2（data.json 公開＋deep link＋時間線快照；**快照需先定案**存哪裡、留幾份） | 中 | 待辦 | [design/map.md](design/map.md) |
| §6 | 停班停課事件檔存檔層（**事件期間才做**、非待辦；新事件時從 feed/查詢頁/新聞撈入事件檔「停班停課」章節） | 中高 | 事件期間進行 | [design/class-halt.md](design/class-halt.md) |
| §5 | 事件分享按鈕：A Web Share＋複製連結 → B Line 一鍵 → C OG 分享圖卡 | 低 | 待辦 | [design/share-button.md](design/share-button.md) |
| §1 | RSS 關鍵詞微調（`rss.py` `KEYWORDS`；隨事件期間 flag 假陽性/假陰性實戰資料，非獨立待辦） | 隨事件 | 隨事件維護 | [design/rss.md](design/rss.md) |

## 已完成（非待辦；細節在設計檔與 git history）

| # | 項目 | 完成 | 設計檔 |
|---|------|------|--------|
| §2-4b | **颱風軌跡／風圈層**（**僅在 `DEV`，待合併 `main`**）：`cwa.typhoon_map_features()` 把 W-C0034-005 轉 GeoJSON（觀測實線＋預報虛線＋最新觀測點／最遠預報點的 15 m/s 風圈＋**70% 暴風半徑環**）；風圈用 `QuadrantRadii` 四象限插值→**非正圓**（實測煙花 2026-10-27 14:00：NE180／SE200／SW160／NW180 km）；顏色單一來源 `cwa.TYPHOON_COLORS`、畫法 `map_page.TYPHOON_STYLE`；一個開關控整層＋圖例＋詳情卡（含四象限半徑、預報時距）＋用氣旋名比對事件檔的本站連結；**風圈 polygon 不互動**、**同層線→圈→點**、**氣旋層疊在超閾值雨量點之上**（推翻 §2-4a 舊定案）三條為鐵則（前兩者實測踩過搶點擊）；新增「圖境外活動氣旋」提示列（煙花在 158.9°E、`maxBounds` 東界 124.3°E→36 圖元 0 可見）。實測：真 Chromium z8/z10/z11、ja 頁、console error 0、heap 14 MB、斷鏈 0、`public/` 14.11 MiB／2,242 檔（+0.09 MiB） | 2026-10-28（**待合併 `main`**） | [design/map.md](design/map.md) |
| §2-4a（續） | **未超閾值淡點改為預設不勾選**（使用者 2026-10-28 要求：平時 1,300+ 個淡點把底圖弄亂）：淡點仍進 `map.geo.json`（勾開即顯示、不重新 build），label 加「（預設不顯示）」提示與站數作為「查過但沒超標」的證據；JS 初始狀態跟隨 checkbox 的 `checked`（`addLayer()`，預設值只寫在 HTML 一處）。同時修一個**真實順序 bug**：叠放原本靠 addLayer 先後，開關（removeLayer/addTo）會把淡點拱到最上面 → 1,300 個命中圈搶走 polygon 點擊；現用**獨立 pane 的 zIndex 固定**（淡點 390 < overlay 400 < 超閾值點 410 < 氣旋 420）。實測（真 Chromium）：z8/z9/z10/z11 淡點開啟與 off→on 兩次後，polygon 仍拿到點擊（命中圈 22→60px）；縮放重算仍 8/22→14/60px；氣旋中心點擊在任何開關後仍贏過超閾值點；真實頁載入後淡點 pane 0 path、console error 0 | 2026-10-28（**待合併 `main`**） | [design/map.md](design/map.md) |
| §2-1~3 | 地圖紅警基礎（gazetteer、cbph 抓取→map.geo.json、/map/ 骨架＋離線瓦片＋自託 Leaflet） | 2026/9/2 | [design/map.md](design/map.md) |
| §2-4a | 雨量站點層初版（三級點層＋側欄圖例＋詳情卡；樣式待 4a-follow 重做） | 2026/9/16 | [design/map.md](design/map.md) |
| §12 | **站內斷鏈修復**：信任頁缺深度前綴、ja 樹的站根產物（llms.txt／sitemap）與語言切換按鈕差一層、事件正文的 `.md` 互連未改寫為事件頁；新增 `build/check_links.py` 當 build 後驗證工具（WORKFLOW §3 ②）。實測 **129 條 → 0 條**、build 零 warning | 2026-10-26 | [design/site.md](design/site.md) |
| §2-7 a+b | 底圖視野擴展：`MAP_CENTER` 向東 0.35°、`tiles.py` per-zoom bbox **推導**（MAP_MAX_BOUNDS ⊕ 視口溢出 ⊕ 0.3° elastic）、離線瓦片 967→**2,200 張**（15→25 MB）、缺瓦片處改海色底（修了舊缺陷：`MAP_MAX_BOUNDS` 比瓦片覆蓋寬→右側 1.6° 一直只有海）。真 Chromium 驗 1920/1440/390 與 maxBounds 四邊拖曳＝零 404 | 2026-10-26（已合併 main＋上線；commit `07e3ec4`） | [design/map.md](design/map.md) |
| **§2-7c** | **兜底陸地層**：獨立 pane（zIndex **1** < tilePane 200）＋ Natural Earth 10m land 經裁剪/簡化 → 新常數 `FALLBACK_LAND` 79 環／1,702 點／**36 KB**，範圍由 `tiles.zoom_bbox()` 推導（⚠️ 改 `MAP_MAX_BOUNDS`/`ZOOMS` 後**必須重跑 `build/make_taiwan_geo.py`**，否則兜底層不跟著長）。⚠️ 順帶修 §2-7a 舊缺陷：不透明海色佔位底 `_ocean.png` 在 tilePane 內、會蓋住陸地層→改全透明 `_blank.png`（海色改由 `--sea`＝`tiles.OCEAN_CSS` 注入）。真 Chromium 實測：瓦片齊全時 1440×900 差異 **0.000%**（完全被蓋）、2560×1440 仅 0.405% 且全在左側瓦片界外；瓦片全 404 時台灣/澎湖/石垣顯陸色、開闊太平洋/台灣海峽純海色（無假陸地）；3 縮放＋4 拖曳 longtask **0**；`public/` 14.02 MiB／2,241 檔（檔數不變）、最大單檔 1.18 MiB（CF 25 MiB 上限的 4.7%） | **2026-10-27**（合併 `main` ＋ 15:49 由部署機 `deploy-cron.sh` 上線：三自訂域名＋GH Pages 鏡像＋ja 皆複驗通過） | [design/map.md](design/map.md) |
| **鏡像 `_` 開頭資產 404 修正** | GitHub Pages 的 gh-pages 是 **branch 來源**（會跑 Jekyll），而 Jekyll **忽略檔名以 `_` 開頭的檔** → `assets/tiles/_blank.png`（與舊鏡像上的 `_ocean.png`）在 `lawlietr.github.io` 一直 404（同路徑在 CF 200；`map/index.html`、瓦片、`leaflet.css` 皆 200，tree 內唯一的 `_` 檔就是它）。修法：`build/site.py` 站根產空檔 `public/.nojekyll`（與 404.html／robots.txt 同一處產出）；WORKFLOW §3 ⑤ 新增檢查、AGENTS 不變項新增第 ④ 條。重新部署後鏡像 `_blank.png` 200／334 B ✓ | 2026-10-27（commit `94963c6`，已上線） | [design/map.md](design/map.md) |
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



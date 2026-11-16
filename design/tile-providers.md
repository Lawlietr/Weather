# 底圖瓦片供應商評估（OpenFreeMap / VersaTiles / Protomaps）

> 狀態：**評估完成、未實作**（結論：維持現行來源，不換）｜最後更新：2026-11-17
> 對應 TODO：見 `TODO.md`「底圖供應商升級 POC」列
> TL;DR：三家都是**向量（vector）優先**。現行線是「build 時抓好 2,200 張 PNG、前端只做 Leaflet 柵格疊圖」，改用其中兩家要把 Leaflet 換成 MapLibre GL JS（重寫 `/map/` 的 pane／polygon／命中判定），改用第三家（Protomaps）可留在 Leaflet。實測：這個地圖窗改用向量瓦片，體積從 10.38 MB 變成約 23 MB（變大）。因此本輪結論是不動；只有日後要「依語言換地名」或「重畫底圖風格」時，才啟動 Protomaps 的 POC，做法寫在下方「若要啟動 POC」。

## 1. 評估動機

使用者提出三個來源，問是否比現行來源好：

- <https://openfreemap.org/>
- <https://versatiles.org/>
- <https://docs.protomaps.com/>

評估標準不是「哪家比較漂亮」，而是**能否塞進本專案的既有不變項**。這五條先列出，後面的判斷都從它們推導：

1. **前端零外部請求**：網站只有靜態檔，气象資料與底圖都在 build 時放進 `public/`（AGENTS「不變項」）。
2. **Leaflet 三層堆疊**：兜底陸地層（自訂 pane、`zIndex=1`）→ 離線瓦片 `tilePane`（200）→ 告警 polygon／雨量點 overlay（400）。換底圖不得破壞這個 z 序。
3. **build 端工具要輕**：`build/build.sh` 由本地 cron 每 2 小時在部署機（`192.168.100.14`）跑一次。新增 Rust／Go／需要 GPU 的渲染工具鏈都違反這條。
4. **缺瓦片兜底機制**：`errorTileUrl` 那張 `_blank.png` 必須全透明；海色由 CSS 背景提供，而且必須與瓦片自帶的海洋同色（`build/tiles.py` 的 `OCEAN_RGB`／`OCEAN_CSS`）。
5. **缺瓦片處的陸地要與瓦片同風格**：兜底陸地層由 `build/taiwan_geo.py` 的 `FALLBACK_LAND` 上色，改底圖風格就要跟著重新取色並重跑 `python3 build/make_taiwan_geo.py`。

## 2. 現行來源與基線（2026-11-17 實測）

來源＝OSM 德國社群瓦片伺服器 `https://tile.openstreetmap.de`（`build/tiles.py` 之 `TILE_SERVER`，免 key、自訂 UA 帶 contact）。層＝`ZOOMS = (8, 9, 10, 11)`，每層 bbox 由 `zoom_bbox()` 從 `MAP_MAX_BOUNDS` 推導。

| zoom | 張數 | PNG 實績 |
|---|---|---|
| 8 | 63 | 0.62 MB |
| 9 | 121 | 0.90 MB |
| 10 | 420 | 2.46 MB |
| 11 | 1,596 | 6.40 MB |
| **合計** | **2,200** | **10.38 MB** |

`du -sh` 看到的 25 MB 是檔案系統叢（cluster）開銷，2,201 個檔案（含 `_blank.png`）在 Cloudflare Pages 的 20,000 檔／25 MiB 每檔上限內。

來源健康狀態（同日實測）：

- `8/216/110.png` → HTTP 200、`image/png`、7,458 B
- `11/1731/883.png` → HTTP 200、103 B（海域空瓦片，正常）

現行的已知弱點：OSM 官方伺服器曾對本機 IP 回「假 200 ＋ 封鎖頁 PNG」（2026/9/2 記錄，967 張全中）；`build/tiles.py` 已有防呆（HTTP 非 200 或 PNG signature 不對 → 判失敗）。社群伺服器有流量上限，本專案靠持久快取 `build/_tile_cache/`（缺什麼補什麼）把用量壓到接近零。若哪天 OSM.de 也封，退路是換鏡像 URL（一處）。

## 3. 逐個結果

### 3a. OpenFreeMap — 只有向量瓦片，且本專案窗會變大

實測：

- TileJSON `https://tiles.openfreemap.org/planet` → 瓦片模板 `https://tiles.openfreemap.org/planet/20261101_080013_pt/{z}/{x}/{y}.pbf`，`minzoom 0`、`maxzoom 14`。
- 任何 raster（PNG）路徑都拿不到：`/raster/liberty/8/214/110.png`、`/raster/8/214/110.png`、`/planet_prebuilt/...` → 全部 403／404（HTML）。**沒有柵格端點可 hotlink。**
- 樣式 `https://tiles.openfreemap.org/styles/liberty`：111 個 layer；兩個 source——`openmaptiles`（vector）與 `ne2_shaded`（raster PNG，`maxzoom 6`）。
- 向量瓦片**有中文地名**：抓 `11/1715/876.pbf`（台北市）後在二進位內容找到「臺北」「台北市」「松山」「松山空港」等字串。
- 同一張 z11/1715/876：向量 **161,547 B**，現行 PNG **41,500 B**（3.9 倍）。
- 以本專案同一窗抽樣 72 張向量瓦片（z8×10、z9×12、z10×20、z11×30）後外推：平均 z8 42.2 KB、z9 20.1 KB、z10 19.2 KB、z11 5.9 KB → **總量約 23.1 MB**，對照現行 PNG 10.38 MB（約 2.2 倍）。抽樣誤差約 ±20%。變大的原因：OpenMapTiles 全 schema 在 z8–z11 帶了我們用不到的圖層與多語地名欄位。
- 走 MapLibre 的固定成本（都要自托管，因為前端零外部請求）：
  - `maplibre-gl@5.14.0` 的 `dist/maplibre-gl.js`：1,011,731 B（gzip 265,430 B）
  - sprite：`sprites/ofm_f384/ofm@2x.png` 118,872 B ＋ `ofm.json` 27,737 B
  - glyph（字型）：`fonts/Noto Sans Regular/0-255.pbf` 76,580 B、`Noto Sans Bold/0-255.pbf` 81,170 B，每檔只蓋 256 個字元；**中文字要另外抓多個 CJK range 檔**。試 `Noto Sans TC Regular/...` 回 404，代表 fontstack 名稱要照 style 的 `text-font`（該 style 用 `Noto Sans Regular`／`Italic`／`Bold`）逐一对上去，離線自托管是一筆額外工作。
- 另有 Natural Earth 陰影柵格可用：`natural_earth/ne2sr/6/53/27.png` → 200、134,373 B、512×512 PNG（z5 `5/26/13.png` 268,822 B）。但 `maxzoom 6`，我們的地圖是 z8–z11，放大後無細節可言 → **對本專案沒有解析度價值**。
- 授權與用量：免 key、自架免費、每週全planet 下載（Btrfs／MBTiles／PMTiles）。

結論：**不採**。要前端換 MapLibre，體積還變大。

### 3b. VersaTiles — 自架生態，沒有柵格輸出路線

實測與文件（docs.versatiles.org、download.versatiles.org）：

- 下載的是 `.versatiles` 容器（自家 v02 格式）、planet 級：`osm-vector`（有日期版，20240101 … 20261027）、`hillshade-vector` **105.4 GB**、`bathymetry-vector` **681.5 MB**、另有 `landcover-vector`、`satellite-raster`、`elevation-raster`。要小區域得用 `versatiles extract`（Rust CLI）。
- 展示端走 MapLibre GL JS（其 demo 頁載 `maplibre-gl.js`）；另有 `versatiles-svg-renderer`（瀏覽器端 SVG 渲染）。**柵格輸出**只有「VersaTiles Renderer（render a map view as image）」，文件自己標 **WIP**。
- `tiles.versatiles.org` 是展示前端，不是公開柵格端點：探 `/assets/tiles/8/216/110`、`/assets/raster/...`、`/assets/tiles.json` 全部 404。

結論：**不採**。它假設使用者自架 Rust tile server 並用 MapLibre 渲染，與不變項 3（build 端工具要輕）與 2（Leaflet 三層）直接衝突。它真正的優勢（完全自架、單檔容器、可自訂 style、有 hillshade／bathymetry／landcover／satellite 圖層）在我們的規模下用不到。

### 3c. Protomaps — 唯一可留在 Leaflet 的路線

實測與文件：

- 載體是 **PMTiles**（單檔瓦片封存＋HTTP Range 請求）。OSM basemap 全planet 檔約 **120 GB**（z0–15，v4 daily build 於 `maps.protomaps.com/builds`，有 BLAKE3 hash）。官方建議**不要 hotlink 下載位**，要複製到自己的 storage。
- 可只取區域窗：`pmtiles extract` ＋ `--maxzoom`（文件：每多一層約加倍）。我們只需 z8–z11 ＋ 台灣窗，檔案會小得多（**尚未實測**，需要 Go CLI `pmtiles`；依規則不得自行安裝執行體，要先前徵同意）。
- **Leaflet 路線**：`protomapsL.leafletLayer({url, flavor, lang})`（`protomaps-leaflet@5.0.0`）。它用 Canvas 把向量瓦片畫成圖瓦，所以 **Leaflet 的 pane／`zIndex`／overlay 結構可以保留**，我們的三層堆疊不必重寫。成本實測：`protomaps-leaflet.js` 127,298 B（gzip 37,341 B）；`pmtiles@4` 前端庫 20,229 B（gzip 7,957 B）。
- ⚠️ 官方警語：該庫處於 **maintenance mode**，只建議用於重度依賴 Leaflet 的舊專案，並說明它「designed for non-interactive layers」。我們正是「底圖不可互動、互動都在 Leaflet overlay」的形態，條件符合，但要接受它不是主線路線。
- `flavor` 只有 `light`／`dark`／`white`／`grayscale`／`black` 五種；海色要重新取色餵回 `OCEAN_RGB`／`OCEAN_CSS`，並重取 `FALLBACK_LAND` 的陸地色、重跑 `make_taiwan_geo.py`（不變項 4、5）。
- **定位（localization）是它最大的亮點**：官方支援語言清單含 **Chinese (Traditional) `name:zh-Hant`** 與 Japanese `name:ja`，並把多語地名拆成 `name`/`name2`/`name3` ＋ `script`（例：`name=香港`、`script=Han`、`name2=Hong Kong`）。這是三家里唯一能明確講「同一張底圖依語言給不同地名」的來源——our `public/ja/` 日文站日後可考虑 `lang: 'ja'`（**未驗證**：OSM 的 `name:ja` 對台灣地名覆蓋率未知）。
- 授權：軟體 BSD、basemap 為 ODbL 產出物（需 OSM 署名），planet 下載免費。

結論：**這是唯一值得做 POC 的一家**，但仍不值得現在動（下方結論 2 的三個前提都還沒驗證）。

## 4. 結論（本輪定案）

1. **不換底圖。** 四條理由：
   - 換 OpenFreeMap 或 VersaTiles ＝ 把底圖從「離線柵格 PNG」變成「前端跑 MapLibre 渲染向量」。`build/map_page.py`（905 行）的自訂 pane、cbph polygon 的命中判定、颱風軌跡與風圈層、tooltip 全部要重寫，AGENTS 那條「三層堆疊四不得破壞條件」整套失效。
   - 還要額外自托管 MapLibre JS（gzip 265 KB）、sprite、以及**中文 glyph range 檔**。MapLibre 另要求 WebGL，對災時舊裝置是風險（現行 Leaflet 只要 SVG/Canvas）。
   - 對我們的地圖窗（z8–z11、台灣周邊）向量瓦片**比較大**：約 23 MB vs 10.38 MB。
   - 現行來源今天實測正常，風險已有退路（換鏡像 URL 一處 ＋ 假 200 防呆 ＋ 全透明佔位瓦片 ＋ 兜底陸地層）。
2. **日後要升級就只走 Protomaps**，但啟動 POC 前要確認三件事：
   - (a) Cloudflare Pages 對 **HTTP Range request** 的支援（PMTiles 靠 Range）。若不支援，退回「向量 pbf 金字塔」放在 `public/`（檔案數與現在相同），或改放 R2。
   - (b) `flavor` 的海色與陸地色能否對上 `OCEAN_RGB`／`OCEAN_CSS` 與 `FALLBACK_LAND`（否則缺瓦片處會有色差）。
   - (c) 真 Chromium（Playwright）比對 z8／z11 的地名清晰度與繪製速度。依 AGENTS，`/map/` 的向量層驗證一律用 Playwright，不用 obscura 截圖。
3. **值得加的其實是地形/等深線參考層，不是換供應商。** 現行 z8–z11 的 OSM 瓦片已有等高線；OpenFreeMap 的 `ne2sr` 只到 z6（放大無細節）、VersaTiles 的 hillshade/bathymetry 是 planet 級向量且要自架與 MapLibre。列入観望，不進時程。

## 5. 若要啟動 POC（Protomaps）的步驟

1. 先徵得使用者同意安裝 `pmtiles` CLI（Go 執行體；依規則不自行安裝）。
2. 用台灣窗＋`--maxzoom=11` 做 `pmtiles extract`，記錄檔案大小與耗时（與現行 2,200 檔／10.38 MB 對照）。
3. 在 `DEV` 分支做最小改動：`build/map_page.py` 的底圖層改為 `protomapsL.leafletLayer({url: '/assets/basemap.pmtiles', flavor: 'white', lang: 'zh-Hant'})`，**不動**三層 pane 與 overlay 程式。
4. 依結果更新 `build/tiles.py` 的 `OCEAN_RGB`／`OCEAN_CSS`，必要時重取 `FALLBACK_LAND` 色並重跑 `python3 build/make_taiwan_geo.py`。
5. 部署到測試站 `wea-testing`，用 Playwright 真 Chromium 檢查三層 z 序、告警 polygon 可點、缺瓦片處仍顯示陸地層。
6. 只有在 (a)(b)(c) 都過、且測試站比對滿意後，才討論合併 `main`。

## 6. 重現本輪實測

```bash
# 現行來源與體積基線
python3 -c "import sys,os;sys.path.insert(0,'build');import tiles;
print([(z,len(tiles.tile_list((z,))),sum(os.path.getsize(f'build/_tile_cache/{z}/{x}_{y}.png') for (zz,x,y) in tiles.tile_list((z,)) if os.path.exists(f'build/_tile_cache/{z}/{x}_{y}.png'))) for z in tiles.ZOOMS])"

# OpenFreeMap：TileJSON／向量瓦片／無柵格端點／ne2sr
curl -s https://tiles.openfreemap.org/planet | python3 -m json.tool | head -20
curl -s -o t.pbf -w "%{http_code} %{size_download}\n" https://tiles.openfreemap.org/planet/20261101_080013_pt/11/1715/876.pbf
curl -s -o /dev/null -w "%{http_code}\n" https://tiles.openfreemap.org/raster/liberty/8/214/110.png   # 403
curl -s -o ne.png -w "%{http_code} %{size_download}\n" https://tiles.openfreemap.org/natural_earth/ne2sr/6/53/27.png

# 前端固定成本（raw／gzip）
curl -sL -o mlg.js https://unpkg.com/maplibre-gl@5.14.0/dist/maplibre-gl.js && wc -c mlg.js && gzip -c mlg.js | wc -c
curl -sL -o pml.js https://unpkg.com/protomaps-leaflet@5.0.0/dist/protomaps-leaflet.js && wc -c pml.js && gzip -c pml.js | wc -c
```

⚠️ 對 `tiles.openfreemap.org` 抽樣要帶明確 UA＋contact（空 UA 會被擋）。抽樣用隨機層層抽、依各 zoom 的實際張數外推，**不要**只看陸地瓦片（會高估）。

## 7. 陷阱與注意（供日後動工）

- OpenFreeMap **沒有可 hotlink 的 PNG 端點**；把它當成「改個 URL 就能換的預渲染供應商」是錯的。本檔撰寫前的舊註（`design/map.md`「選型與離線自駕」節）寫的正是這種誤解，已更正。
- 向量瓦片的中文地名存在與否要**逐來源實測**（grep 二進位內容即可判斷），不能假設 OSM 來源一定有當地文字。
- `ne2sr` 是 512×512、`maxzoom 6`；用在不帶 `maxNativeZoom` 的 Leaflet 圖層會看到糊的放大圖。
- Protomaps 的 `protomaps-leaflet` 官方定位是 maintenance mode／non-interactive layers；選它等於接受一條非主線路線（主線是 MapLibre GL JS）。
- 換底圖必然要動的東西（一次全列，避免只改一半）：`TILE_SERVER` 或底圖層產生式、`OCEAN_RGB`／`OCEAN_CSS`、`FALLBACK_LAND` 陸地色、`make_taiwan_geo.py` 重跑、地圖頁頁尾署名（三家都要 OSM 署名，OpenFreeMap 另要求 OpenMapTiles／OpenFreeMap、Protomaps 建議加 Protomaps 出處）、`ZOOMS`／`MAP_MAX_BOUNDS`（向量來源的 maxzoom 通常比我們現在深，若要更深要重算瓦片窗與體積）、以及 `design/map.md` 的三層 z 序章節。

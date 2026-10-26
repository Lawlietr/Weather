# TODO：任務帳本

> 本檔只記**要做的事＋優先級＋狀態＋設計檔連結**；問題背景、定案細節、規格與陷阱在 `design/<功能>.md`（每功能領域一份）；流程 runbook（更新／build／驗證／部署）在 `WORKFLOW.md`。已完成項目的歷史細節看 git history。
> 編號為傳統編號（§N），供既有引用對照；細節一律跟連結進 design/。
> 最後更新：2026/10/26（新增 §2-7 底圖視野擴展；拆檔歷史見 2026/9/16：§2→`design/map.md`、§5→`design/share-button.md`、§6→`design/class-halt.md`、§1→`design/rss.md`、§3/§4/§7/§9/§10/§11→`design/site.md`；本檔瘦身為帳本）

## 待辦（依優先級排序）

| # | 任務 | 優先級 | 狀態 | 設計檔 |
|---|------|--------|------|--------|
| **§2-7** | **底圖視野擴展**：瓦片東界 122°E＝台灣東岸→右側 2.9°（佔桌面視窗 37%）無底圖且畫成紙色。a 海色底＋`errorTileUrl`、b `MAP_CENTER` 往東＋`tiles.py` per-zoom bbox | 🔥 高 | **a＋b 已實作（2026/10/26，DEV，真瀏覽器實測全 PASS）**、待合併 main；**c 陸地輪廓兜底仍待辦** | [design/map.md](design/map.md) |
| §2-7c | 陸地輪廓兜底（海色＋陸地最底層；`taiwan_geo.py` 擴到菲北/與那國/宮古——**要改產生器 `make_taiwan_geo.py`**） | 中 | 待辦 | [design/map.md](design/map.md) |
| §2-4a-follow | 雨量點樣式重做（4a 合併後**先處理**；現行尺寸/色碼未過關） | 🔥 高 | 待辦（候選方向待討論；⚠️ 色碼判斷前提＝§2-7 的海域面積先定案） | [design/map.md](design/map.md) |
| §2-4b | 颱風軌跡/風圈層（實線觀測＋虛線預報＋最新預報點風圈） | 高 | 待辦 | [design/map.md](design/map.md) |
| §2-4c | 特報陸地紅區層（選項 A：自託縣界 GeoJSON；**動工前需確認縣界資料源**） | 高 | 待辦 | [design/map.md](design/map.md) |
| §2-2b | 災情新聞點層（人工/agent 餵料，gazetteer 已備） | 中 | 暫緩（2026/9/1 定） | [design/map.md](design/map.md) |
| §2-6 | /map/ v2（data.json 公開＋deep link＋時間線快照；**快照需先定案**存哪裡、留幾份） | 中 | 待辦 | [design/map.md](design/map.md) |
| §6 | 停班停課事件檔存檔層（**事件期間才做**、非待辦；新事件時從 feed/查詢頁/新聞撈入事件檔「停班停課」章節） | 中高 | 事件期間進行 | [design/class-halt.md](design/class-halt.md) |
| §5 | 事件分享按鈕：A Web Share＋複製連結 → B Line 一鍵 → C OG 分享圖卡 | 低 | 待辦 | [design/share-button.md](design/share-button.md) |
| §12 | **站內 nav 斷鏈**（與本次改動無關的既有問題）：about/contact/privacy 頁的地圖連結缺 `{base}` → 404（zh＋ja 共 ~98 條；`site.py:692` 寫死 `href="map/index.html"`）；ja 事件頁殘留 `.md` 連結（~32 條） | 中 | 待辦（2026/10/26 實測 130 條斷鏈） | [design/site.md](design/site.md) |
| §1 | RSS 關鍵詞微調（`rss.py` `KEYWORDS`；隨事件期間 flag 假陽性/假陰性實戰資料，非獨立待辦） | 隨事件 | 隨事件維護 | [design/rss.md](design/rss.md) |

## 已完成（非待辦；細節在設計檔與 git history）

| # | 項目 | 完成 | 設計檔 |
|---|------|------|--------|
| §2-1~3 | 地圖紅警基礎（gazetteer、cbph 抓取→map.geo.json、/map/ 骨架＋離線瓦片＋自託 Leaflet） | 2026/9/2 | [design/map.md](design/map.md) |
| §2-4a | 雨量站點層初版（三級點層＋側欄圖例＋詳情卡；樣式待 4a-follow 重做） | 2026/9/16 | [design/map.md](design/map.md) |
| §6-自動層 | 停班停課 DGPA CAP feed 首頁卡（is_current 判斷、置頂/置底、容錯） | 2026/9/15 | [design/class-halt.md](design/class-halt.md) |
| §1 | RSS 災情抓取（半自動：build 產候選清單、人工審查後入事件檔） | 2026/8/30 | [design/rss.md](design/rss.md) |
| §7 | 颱風動態區塊淘汰機制（TYPHOON_STALE_HOURS 24h、海上警報豁免） | 2026/9/13 | [design/site.md](design/site.md) |
| §8 | cbph 503 假警報修復（503/404 視為空清單、不進 warnings） | 2026/9/13 | [design/site.md](design/site.md) |
| §9 | 氣象總覽卡片排序（無活動氣旋時颱風卡置底、stale 例外頂位） | 2026/9/13 | [design/site.md](design/site.md) |
| §10 | 零星災情縣市分組寫法（A/B 並用、判斷標準＝事件 status） | 2026/9/15 | [design/site.md](design/site.md) |
| §11 | AI bot 可偵測性強化（JSON-LD、OG、信任頁、404 指引、llms.txt） | 2026/9/15 | [design/site.md](design/site.md) |
| §3 | ja 產出保留＋隱藏語言切換按鈕（機翻彙整文字作廢） | 2026/9/15 | [design/site.md](design/site.md) |
| §4 | 平常時期區域性天氣報導（❌ 不採：偏離事件＋災情定位、靜態站無在地化能力） | 2026/9/15 | [design/site.md](design/site.md) |



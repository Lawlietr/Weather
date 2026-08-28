# TODO：待辦事項

> 專案背景、設計原則、技術架構與部署流程分別見 `README.md`、`AGENTS.md`、`WORKFLOW.md`，本文件只放**未完成的待辦**。
> 最後更新：2026/8/28

---

## 1. RSS 災情抓取接入 build

`build/rss_sources.json` 已建好並實測（來源清單與抓取守則見 `build/rss_sources.json` 與 `AGENTS.md`「新聞 RSS 來源」），但 `build/site.py` 尚未有任何 RSS 邏輯。待實作：

- 批次抓取 `rss_sources.json` 的 `sources`（勿呼叫 `failed_sources`）。
- 解析器需同時相容 `rss20`（`<item>`）與 `atom`（`<entry>`，公視是 Atom）。
- 單一來源 404/超時不中斷 build（跳過＋記 warning）。
- 依時間過濾，只保留近期且與當前活動事件相關條目；每筆只給摘要＋原新聞連結。
- **風傳媒（storm.mg）待復查**：RSS 疑似移除，但它是颱風/災情最重要的新媒體之一。若確認失效，取不到時退而用 Obscura 抓其新聞頁。

## 2. 地圖標註功能（構想，待實作）

在互動地圖上標註災情新聞位置、雨量站 TOP、警戒區域、颱風軌跡，讓使用者一眼看到「現在最危險的地區在哪」。

### 選型（已定：Leaflet + OpenStreetMap）

- 不用 Google Maps（JS API 強制計費帳戶，個人靜態站不值得）。
- Leaflet + OSM 瓦片：開源免費、無 API key、靜態部署無縫。
- **保持輕量**：Leaflet 只在「地圖頁」載入（自託 `leaflet.js` ~40 KB + 1 個 CSS）；**首頁維持零 JS**（現有靜態 SVG 軌跡圖不換）。

### 離線自駕（硬需求）

- 所有 JS/CSS 自託在 `public/assets/`，不引 CDN。
- 瓦片策略：build 時只抓台灣範圍所需瓦片存本地（約 z9–z11，幾十張 PNG、數 MB），Leaflet 指向本地瓦片 → 完全離線、零外部請求；不要跑 OSM tile server。出範圍的瓦片顯示空白底（或 fallback 到現有靜態 SVG）。

### 資料座標盤點

- ✅ 已有：颱風軌跡/風圈（W-C0034-005）、雨量站（O-A0002-001 `GeoInfo`）、警戒區域多邊形（W-C0034-001 CAP `area`）。
- ❌ 缺：災情新聞的座標——做法：建**鄉鎮級靜態座標表**（gazetteer，JSON，手工維護或用 CWA C-B0074 測站資料生成），災情 markdown 的鄉鎮名稱對照；查不到回退縣級座標，再查不到不上圖。

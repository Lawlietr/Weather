# RSS 災情抓取設計

> 狀態：✅ 2026/8/30 完成；剩餘僅隨事件維護（非待辦）｜最後更新：2026/9/16
> 對應 TODO：R1（見 `TODO.md` 主表）
> TL;DR：build 時自動抓 verified RSS 產候選清單 `build/rss_candidates.json`（從不進 `public/`）；相關性由人/LLM 審查，挑中者寫入事件檔「XX災情新聞來源」章節才上線——災情新聞永不自動推。

## 已實作

`build/rss.py` build 時自動抓 verified feeds 產出候選清單 `build/rss_candidates.json`（**從不進 `public/`**）；人 / LLM 審查後挑中者寫入事件檔「XX災情新聞來源」章節才上線（流程見 `WORKFLOW.md` §1）。

來源清單與抓取守則（rss20/atom 解析、BOM、民報域名、風傳媒端點、失敗降級等陷阱）一律以 `build/rss_sources.json` 的 `usage_notes` 為單一事實來源（見 AGENTS.md「新聞 RSS 來源」）。

## 維護註記（非待辦）

- 關鍵詞清單（`rss.py` 的 `KEYWORDS`）隨事件期間 `rss_candidates.json` 的 flag 假陽性/假陰性實戰資料微調——只有事件期間才有實戰依據；2026/9/7 已完成第一輪修剪（細節見 git history）。
- （可選構想）事件期間候選量太大時，把 flag 條目渲染到首頁供快速瀏覽（非必需）。

已完成：風傳媒（storm.mg）RSS 復查恢復（2026/9/7，端點與入列見 `AGENTS.md`「新聞 RSS 來源」）。

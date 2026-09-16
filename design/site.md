# 首頁／網站設計（已定案小項彙整）

> 狀態：已完成／已定案（下列各項均非待辦）｜最後更新：2026/9/16
> 對應 TODO：無（全部定案項；待辦僅存於各功能自己的設計檔）
> TL;DR：與首頁、網站行為相關的已定案小項（ja 產出、颱風卡淘汰、卡片排序、零星災情寫法、AI bot 可偵測性、平常時期天氣報導不採）。

## ja 產出（✅ 2026/9/15 定案：不移除，隱藏語言切換按鈕）

**定案**：ja 產出**保留**（`public/ja/` 照常 build、`/ja/` 直接 URL 仍可進、sitemap 含 ja URL）；只**隱藏**頁首語言切換按鈕（2026/9/15，使用者指示：隱藏不是移除，ja 翻譯日後可能恢復使用）。

- 實作＝`build/site.py` 一列 CSS `.lang-switch{display:none}`（帶註解；要恢復刪該行即可）。HTML 仍渲染、`build/i18n.py` 全部不動。
- 歷史：2026/8/28 曾定案「移除 ja 產出」（半殘體驗、維護雙倍），2026/9/15 使用者改判：內容留下、入口藏起。
- 機翻自撰彙整文字（Google/DeepL，build 時）已評估但**作廢**（2026/8/28）：CWA 資料不該翻譯（條款＋正確性）、新聞摘要無翻譯授權（版權）；不列入待辦。

## 平常時期區域性天氣報導（❌ 不採，2026/9/15 定案；2026/8/29 提出）

不採理由：①偏離專案「天氣事件＋災情」定位——天氣預報非事件紀錄、非預警（預警＝CWA 警報/特報呈現，首頁既有）；②純靜態站無從得知使用者位置，「在地化」不可行，北/中/南/東分組與既有雨量/特報卡重疊。唯一有獨立價值的一塊——事件期間「本次雨量 vs 30 日均值」對照（C-B0024-001）——保留為構想，日後併入地圖（`design/map.md`）或災情檔案，不獨立成卡。完整構想史（方案 A/B）見 git history（44bd5bd）。

## 颱風動態區塊淘汰機制（✅ 2026/9/13 定案並實作、已合併 main 並上線）

**問題意識**：首頁「氣象總覽」下的**颱風動態　CWA W-C0034-005** 區塊是 build 時自動抓取 CWA 熱帶氣旋軌跡 API 生成；該 API 把 CWA 追蹤的**所有**熱帶氣旋都回傳（含對台無影響或已消散者）。原 `build/cwa.py: render_typhoon_card()` 只要 cyclone 有 analysis fix 就顯示、無任何新鮮度或相關性過濾，過時／已離開的氣旋會一直掛在首頁。

**實測例證（2026/9/13）**：首頁最後 build 於 2026/9/7 仍顯示**科羅旺（2026 第 27 號）**；同日 CWA W-C0034-005 **仍回傳科羅旺**（fix 時間 `2026-09-07T20:00:00+08:00`、風速 12 m/s——CWA 已多日未更新但仍列在軌跡中）。即使重跑 build 一樣會顯示——問題在渲染邏輯沒過濾。對照：警報卡 `render_alert_card()` 已有 `LIFTED_TTL_HOURS = 48` 淘汰機制，颱風卡沒有對等機制＝設計缺口。

**根因（兩層疊加）**：
1. **渲染邏輯缺失**：`render_typhoon_card` 從未設計氣旋淘汰/過濾；首頁 CWA 區塊完全由 API 生成、無 TTL、無「對台相關性」過濾。科羅旺已被刪為 `颱風/` 檔案（對台無影響、不符合建檔門檻），但那個刪除只影響 markdown 檔案，**對自動生成的首頁卡片無效**。
2. **更新管道與本機分離**：本地主力 cron（`0 */2 * * *`）的自動部署跑在**開發環境**、不是這台機器——刻意設計，讓開發／修改不會自動影響正式服務。因此這台（開發/手動端）首頁停在哪裡、多老，不會被自動更新修好，也不會被自動偵測到過時。

**定案與實作（2026/9/13）**：採用**方向 A（新鮮度 TTL）＝ `TYPHOON_STALE_HOURS = 24`**：最新 analysis fix 超過 24h（＝漏 4 個 CWA 6h 更新週期，代表 CWA 已停止追蹤）即從首頁移除；全部淘汰顯示現有 `typhoon_none` 空狀態。`W-C0034-001` 對該氣旋有**生效中（未解除）海上颱風警報者豁免**（防 API 延遲；警報名稱解析失敗時 fail-safe 全保留）。**不採 B（對台相關性）**：CWA 對遠洋氣旋本身就不會定期更新 fix，TTL 已自然淘汰絕大多數噪音；若日後出現「CWA 持續追蹤但與台無關」的卡位案例再補。

實作位置：`build/cwa.py` 新增 `filter_typhoon_stale()`，套用於（1）`cwa_section_html` 的颱風卡、（2）`current_risk_level()` 狀態列（同一缺口：過時氣旋會把風險狀態推成黃色）。**`/map/` 仍用原始 `fetch_typhoons()` 全量軌跡**（地圖層需求），與首頁過濾後子集分開取用。純 build 邏輯，自動部署即可持續生效。實測驗證（2026/9/13）：科羅旺（最後 fix 9/7）不再顯示、卡片轉空狀態、風險狀態列不受其影響。

## 氣象總覽卡片排序（✅ 2026/9/13 定案並實作、已合併 main）

**問題**：首頁「氣象總覽」卡片順序寫死為「颱風動態→警報與特報→雨量 TOP 10」；無活動氣旋時，颱風卡以「目前無活動中熱帶氣旋」空狀態佔據最高位，而當下真正的風險訊號（如生效中的陸上強風特報）被壓在下面。

**定案（方案 A：空則置底）**：過濾後有活動氣旋 → 颱風卡頂位（版面不變）；無活動氣旋且資料抓取正常 → 置底（警報/特報卡承接風險訊號）。**例外：颱風資料抓取失敗（stale）時維持頂位**——警示狀態不降級。不採「空則完全隱藏」：空狀態是「查過、沒颱風」的確認訊號，且卡片內的 stale 故障標籤會跟著消失。

實作：`build/cwa.py: cwa_section_html()` 約 10 行（`typhoon_first = bool(typhoons_live) or bool(stale.get("typhoons"))` 決定插入位置）。單元測試 5 案（有氣旋/空/空＋stale/有氣旋＋stale/過時淘汰）＋真實 build 驗證（2026/9/13：警報→雨量→颱風空卡）。已部署測試站 wea-testing 驗證。已合併 main（`a8bc806`）。

## 零星災情的縣市分組寫法（✅ 2026/9/15 定案：A/B 並用、判斷標準＝事件 status；規則已寫入 AGENTS.md，build 不需改動）

**背景**：縣市分組機制「已經存在」，天生適合本專案的靜態架構（Cloudflare Pages、無資料庫）——build 時（`build/site.py`）跨所有事件檔聚合災情、依縣分組，渲染到首頁「各縣市災情總覽」：

- `extract_table_rows()`：只提取 `時間|地點|類型|說明` 四欄表格，每列＝一筆「災情行」。
- `find_county()`：依「章節標題含縣名」或「地點文字含縣名」判讀該筆屬哪個縣市。
- `compute_groups()`：跨事件依縣分組，每縣取最新 8 筆，縣間按最新災情時間倒序。

**結論**：零星災情只要寫成四欄災情表、放在含縣名的章節下（或地點寫明縣市），build 就會自動歸縣並排上首頁，無須任何資料庫查詢。

**限制（必守）**：

- 每個 markdown 檔都須有 front matter（`load_events()`：`if not fm: continue`）——零星災情無法做成「只有災情、無 front matter」的純災情檔，要嘛併入既有事件檔、要嘛建最小事件檔。
- 首頁「各縣市災情」每縣**最多顯示最新 8 筆**（`compute_groups` 的 `[:8]`）；完整歷史仍在各事件頁。
- 不帶年份的災情行靠檔案路徑 `{YYYY}/{MM}/` 推定年份（`parse_row_time`），**寫時間請用完整年份**（如 `2026/9/12 18:00`）。

**定案（2026/9/15）**：A/B 並用，判斷標準＝對應事件 status（使用者已認可；判斷規則在 `AGENTS.md`「零星災情的寫法」節、B 案範本與必守限制在 `WORKFLOW.md` §2.3）：

1. **對應事件仍 `status: active` → A（併入該事件檔）**：含縣名章節 append 四欄表一行、原地更新「最後修改」行。
2. **事件已 `ended` 或無對應事件 → B（最小事件檔）**：`災情/{YYYY}/{MM}/{MMDD}_{事件}_{名稱}.md`＋最小 front matter（建檔即 `status: ended`、通常 `🟢一般`）、備註欄一句話說明＋有因果時放原事件頁連結。

**剩餘（非待辦，構想）**：「某縣市歷年全量災情」獨立彙整頁——需要時才改 `site.py` 新增彙整頁。

## AI bot 可偵測性強化（✅ 2026/9/15 完成並上線；背景：is-agentic.com 掃描 52/100）

**已實作（2026/9/15）**：首頁 JSON-LD（WebSite＋Organization）與事件頁 Article JSON-LD；全頁 meta description／Open Graph（含 `assets/og.png`，`build/make_og_image.py` 純 stdlib 產生）／canonical；`<meta name="is-agentic-site-type" content="content">`；信任頁 `/about/`、`/contact/`、`/privacy/`（zh＋ja，各 ≥500 字）；404 頁加 agent 指引（llms.txt／sitemap.xml 連結）；llms.txt 加「使用指引」段；footer 加關於／聯絡／隱私＋llms.txt／sitemap 連結。實作於 `build/site.py`（`render_page` 加 `page_url`/`jsonld` 參、`build_trust_pages()`）＋`build/i18n.py`。

**分數收尾二輪（2026/9/15，78→目標 ~85）**：Organization JSON-LD 補 `contactPoint`（GitHub Issues）＋國家層級 `address`；build 產出站對外的 `/AGENTS.md`（agent when-to-use/引用指引，與 repo 內 AGENTS.md 不同）；404 頁加字面 markdown 語法區塊（agent-friendly 404 滿分要求）；llms.txt 引用 `/AGENTS.md`。

**不追項（錯配、有意跳過）**：markdown content negotiation（需 Pages Function 動態 Accept 協商，破壞純靜態不變項；agent 取 markdown 已由 `llms-full.txt` 覆蓋）；OpenAPI／JSON error／api-catalog（RFC 9727）／Web Bot Auth（RFC 9421）（本站無公開 API——掃描器的「API」視角是跟隨 llms.txt 連結抓到 CWA 的 apidoc YAML 觸發的，非本站問題）。**注意**：`is-agentic-site-type` tag 只改預設顯示視角、不加分；API 視角仍會計分，故分數天花板受限。

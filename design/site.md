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

## 風險狀態列／颱風卡的「警報狀態」推導（✅ 2026-10-25 定案並實作、DEV）

**問題**（薔琵解警後的首页實測）：
1. 已解除的災害性天氣特報被當成生效中 → CWA `W-C0033-002` 的 `datasetInfo.datasetDescription`
   只寫「大雨特報」，**解除與否寫在 `contents.content`**（「…故解除大雨特報。」）；
   舊碼只查名稱（`"解除" in r["name"]`）。
2. 已解除警報的氣旋（薔琵：24日20:30 第24報 END，CWA 之後仍每 6 小時發布定位）與
   **從未發警報**的外海氣旋（煙花 CWA 34）都被列為「生效中」，把風險列推成 🔴。

**定案**：風險列只計入「CWA 目前對台有生效中（未解除）警報/特報」的項目，與事件 `severity` 仍完全獨立。

**實作**（`build/cwa.py`）：
- `LIFT_RE`＋`is_lifted_report(r)`：名稱含「解除」，**或**（`phenomena` 為空 **且** 內文符合
  `解除…特報/警報`）。`phenomena` 為空是必要條件：生效特報一定附 `hazardConditions`
  （實測 陸上強風特報 phenomena=`陸上強風`、解除的大雨特報 phenomena=`[]`），
  這樣才不會把內文順帶寫到「解除大雨特報，改發豪雨特報」的生效特報誤判。
  同時套用於 `current_risk_level()` 與 `render_alert_card()`（解除報轉 `sev-grey`、置底）。
- `alert_typhoon_names(m)`＋`typhoon_alert_state(c, marine)` → `active`/`lifted`/`none`。
  ⚠️ 解除報的 `typhoon-info`「颱風名稱」欄**實測是空的**（2026-10-24 20:30 第24報），
  名稱要從 `description` 的「命名與位置」內文抓（「輕度颱風 薔琵（國際命名 CHAMPI）」）。
- `current_risk_level()`：`active` 才計入紅/黃；`lifted` 進 `lifted_recent`（⚪ 中性列的「最近已解除」註記）；
  `none` 完全不計入。
- `render_typhoon_card(lang, …, marine)` 加狀態 badge，i18n 新 key `state_active`／`state_lifted`／
  `state_watch`（zh＋ja）：警報生效中（紅）／警報已解除（灰）／未發布警報（外海追蹤）（灰）。

**驗證**：
- 快取即時資料：解除大雨特報→灰且不計入；生效陸上強風特報→計入（黃）；薔琵→lifted、煙花→none。
- 合成回歸 4 案：生效海上陸上警報→`active`＋🔴＋badge 警報生效中；END＋解除特報混合→紅/黃只由生效特報決定；
  帶 phenomena 的「解除大雨特報，改發豪雨特報」→不誤判；全空→🟢。
- 真實 build＋測試站 `wea-testing`（真瀏覽器）：風險列由 🔴（誤）→ 🟡「陸上強風特報（有效至 10/26）」（正）；
  zh/ja 氣旋列顯示「警報已解除／未發布警報（外海追蹤）」與「警報解除済み／警報未発表（海上追跡中）」；
  各縣市災情聚合與事件頁連結不受影響。
- 注意：`/map/` 的地圖層仍走原始 `fetch_typhoons()` 全量軌跡（見上節 TTL 定案），本修正只影響首頁卡片與風險列。

## 特報/警報的「有效時間」判定（✅ 2026-11-14 定案並實作、DEV）

**問題**（生產站實測）：首頁頂部風險列掛了「陸上強風特報（有效至 2026-11-11 16:16 ~ 2026-11-11 23:00）」
**2 天 11 小時**，把全站風險推成 🟡「警戒生效中」。逐期比對 Cloudflare Pages 部署（每 2 小時一期的
preview URL，共 50 期）得到：11/11 18:00 → 11/14 10:00 共 33 個排程檔（11/14 00:00 那期部署失敗
`rc=1`，wrangler 上傳階段）、**32 期渲染同一筆**，其中自 11/12 00:00 起的 **30 期是明確誤報**。
該筆最後在 11/14 12:00 期消失——但**不是我們判出來的**，是 CWA 在 11/14 10:23 因鋒面發了新一報、
把舊記錄頂掉。

**根因**（三層）：
1. CWA `W-C0033-002` 只留**最新一筆**記錄（實測三個不同日期的 feed 回傳都各只有 1 筆、卡面也只有
   1 個 `alert-item`）。舊記錄離開 feed 的**唯一**途徑是被下一報頂掉。
2. 強風/低溫等特報常常**不發正式解除報**。CWA 的兩種動作都不給「解除」文字：
   ① 改發效期較短的新報——11/11 10:29 那報原本寫「有效至 11/12 23:00」，16:16 改發後縮成
     「有效至 11/11 23:00」；② 下次有事件才發新報。
3. 我們的「生效與否」只看文字（`is_lifted_report()`：名稱含「解除」，或 `phenomena` 空且內文符合
   `LIFT_RE`），`current_risk_level()` 與 `render_alert_card()` **從不比較 `validTime.endTime` 與現在**。
   `LIFTED_TTL_HOURS = 48` 只對「已解除」生效，救不到這種筆。

為何不能只等 CWA 自己清掉：CWA 發新報的時機由**天氣**決定。真有強風時誤報看起來最合理、最難被發現；
而**平靜無事件的日子才是它掛最久、最顯眼**的時候——若 CWA 一週不發特報，那筆過期的 🟡 就會掛一週。
清除時間沒有上限，與我們的正確性無關。

**定案**：CWA 給的 `validTime.endTime`（特報）與 CAP `expires`（海上颱風警報）就是「何時失效」的權威值。
過該時點一律**不計入危險信號**，即使內文沒有任何解除字樣。

**實作**（`build/cwa.py`）：
- `report_expiry_raw(r)` / `report_expiry(r)`：讀新欄 `valid_end`（`fetch_reports` 新增 `valid_start` 與 `valid_end` 兩欄）；舊 `cwa_cache.json` 無該欄時退回把 `valid` 字串按 `~` 切尾段（相容舊快取）。
- `alert_expiry(m)` / `alert_is_current(m, now)`：讀 `fetch_marine_alert` 新增的 `expires` 欄；
  缺欄回傳 True（行為不減）。
- `EXPIRED_TTL_HOURS = 24`：已過效期項目在卡面/中性列的保留窗（**以 endTime 起算**，不是發布時間）。
  超過就整筆消失，風險列也不提。已解除項目仍用 `LIFTED_TTL_HOURS = 48`，但 TTL 基準改用
  endTime（缺該欄才退回發布/生效時間）。
- `current_risk_level()`：特報/警報先判過效期 → 不進紅/黃；24 小時內轉進 `lifted_recent`（⚪ 中性列
  「最近：… 已過有效時間」）；超過 24 小時連註記都不留 → 🟢。海上警報同理（不計 🔴）。
- `render_alert_card()`：已過效期與已解除同屬「不再是危險信號」組 → `sev-grey`＋`expired_note`、
  與已解除一起置底；超過各自 TTL 整筆移除。
- `typhoon_alert_state()` 新增 `expired` 狀態（CAP 已到期但 CWA 未發 END 報）、
  `filter_typhoon_stale()` 不再讓已到期 CAP 替舊氣旋撐 TTL。颱風卡 badge i18n `state_expired`。
  ⚠️ 這是防禦性路徑：CWA 對活動中的海上警報每 3 小時發新報、解警一定發 END，實務未遇過。
- i18n 新增 `expired_note` / `note_lifted` / `note_expired` / `valid_until` / `expired_at` / `state_expired`
  （zh＋ja）。同時修正兩處措辭：`risk_report` 由「有效至 {valid}」改為「有效 {valid}」（`{valid}` 本是
  「起 ~ 迄」區間，寫「有效至」不通）；`risk_neutral` 把「已解除」從模板移到各條目自帶（否則已過效期
  的條目會被寫成「已解除」）。

**驗證**：`python3 build/test_report_expiry.py`（新增的離線回歸，不連 CWA：把 `cwa.datetime` 換成固定
時鐘餵合成資料；21 案全過）。重點案例：1 過期 61 小時 → 🟢 且卡面不出現（就是這次事故的原形狀）；
2 過期 30 分鐘 → ⚪ 帶「已過有效時間」、卡面轉灰；3 效期内特報照樣 🟡 且不轉灰（不迴歸）；
4 正式解除報 → 不計入、標「已解除」；5 **10/25 修正不迴歸**：生效豪雨特報內文提到「解除大雨特報，
改發豪雨特報」仍計入；7 過效期 CAP → 不推紅、氣旋 badge 轉「警報已過效期」；8 生效 CAP 照舊紅；
10 舊快取（無 `valid_end` 欄）仍判過期；11 ja 介面用 `有効時間経過`。

**測試站實測**（`wea-testing`，2026-11-14 12:19 期；自訂網域 `weatesting.avpclub.eu.org` 與
`29e2dca8.wea-testing.pages.dev` 兩者內容一致）：
- 效期內的陸上強風特報不受影響：zh 首頁 🟡「陸上強風特報（**有效** 2026-11-14 20:00 ~ 2026-11-15 23:00）」、
  badge `sev-yellow`、卡面無過期註記；ja 同位置為「有効 …」＋🟡 警戒中。措辭已為「有效 …」。
- **A/B/C 端到端重放**（同一條 `site.build_home()` 管線，氣旋/雨量/海上警報全用即時真實 CWA 資料，
  只把 `reports` 換成 11/11 16:16 那筆，時鐘固定 2026-11-14 10:00）：
  - A 對照組（即時真實特報 ＋ 新碼）→ 🟡（不迴歸）
  - B 11/11 那筆 ＋ **修正前**（`git show HEAD:build/cwa.py` 另存後 importlib 載入）→ 完整重現她看到的
    🟡 「陸上強風特報（有效 2026-11-11 16:16 ~ 2026-11-11 23:00）」
  - C 11/11 那筆 ＋ 修正後 → 🟢 目前無危險信號，該卡整張不出現
- 重放腳本是一次性的（`/tmp/weather-scratch/replay_1111.py`；合成預覽另見
  `/tmp/weather-scratch/make_synth.py`。要重跑：`git show <修正前 commit>:build/cwa.py` 另存、
  用 `build/.venv/bin/python` 跑（`site.py` 需 python-markdown），並用 importlib 載 `build/site.py`
  ——`import site` 會被 stdlib `site` 搶走）。**正式回歸只跑 `build/test_report_expiry.py`**。
  ⚠ 合成預覽頁會把假風險狀態放到 `wea-testing`（只限測試站、不是生產站），看完**務必**立刻
  `npx -y wrangler@latest pages deploy public --project-name wea-testing --branch main` 還原，
  並用 `grep 產生時間` 確認已回到真實那一期的時間戳。
- **obscura 真瀏覽器驗證**（obscura MCP 0.4.1-cjk）：
  1. 不迴歸：zh/ja 首頁風險列 `risk-yellow`、border `rgb(255,179,0)`、badge `sev-yellow`，各一筆且
     無過期註記；無 console error。
  2. **合成預覽**（把 11/11 那筆塞回 `site.build_home()`、其餘用即時真實 CWA 資料，寫進 `public/`
     的 hardlink 副本後暫時部署 `wea-testing`，看完立即重新部署真實 `public/` 還原）：
     - **B 過期 30 分鐘**（`eaf6bdec.wea-testing.pages.dev`）→ 風險列 `risk-neutral`、⚪ 常態監視
       （border 不再是黃色）、文字「最近：陸上強風特報（有效至 2026-11-11 23:00，已過有效時間）」；
       「警報與特報」卡 badge `sev-grey`（`rgb(158,158,158)`）＋「（有效時間已過，供參考）」。
     - **A 過期 61 小時**（`24c0f32f.wea-testing.pages.dev`，時鐘就是事故當期）→ 風險列 `risk-green`、
       🟢 目前無危險信號（border `rgb(102,187,106)`），「警報與特報」卡**整張不出現**。
     兩期「各縣市災情」時間軸仍有 8 月的陸上強風特報——那是事件存檔層的歷史紀錄，與風險列無關。
  3. 事件頁（薔琵、0920 西南風）正常：h1/章節/23 與 19 個表格、無 console error。
     ⚠ 事件頁 URL 為**無副檔名**的 `/events/…/<名>`，手拼 `.html` 會 404。
  4. `/map/` 只用 obscura 做**結構對照**、不判向量層（AGENTS 定案：obscura 缺 SVG 1.1 factory API，
     向量層會假陽性「圖層空」）：測試站與生產站舊版探測結果完全一致（`leaflet-container` 在、內嵌
     GeoJSON 1368 個 Feature、tile 模版 `tiles/{z}/{x}_{y}.png`、最大 inline 腳本 1,108,986 bytes、
     無 console error；`tiles` 與 `overlaySvgs` 兩邊都回 0）→ 回 0 是 obscura 的已知限制，不是新版差異。
     向量層的正式判定仍須 Playwright 真 Chromium（本輪 Playwright MCP 兩次導航失敗、一次回傳非頁面
     內容的錯亂文字，不適用）。本輪 diff 不含 `map_page.py`／`cbph.py`／`tiles.py`／`taiwan_geo.py`，
     `/map/` 不受影響。

## 站內連結的深度前綴（§12，✅ 2026-10-26 修復；測試站實測 129 條斷鏈 → 0）

**根因一類化**：`public/` 是三層樹——網站根（zh 首頁、`llms.txt`／`sitemap.xml`／`robots.txt`／`AGENTS.md` 只在這裡）、`ja/`（ja 首頁＋ja 事件＋ja `/map/`）、`events/**` 與信任頁 `about|contact|privacy/`（zh 深度 1、ja 深度 2）。**同一個 `base` 字串同時要指「語言根」和「網站根」就會錯**。定案規則：

| 變數 | 指哪裡 | 用於 |
|---|---|---|
| `base`（由 `home_link` 推） | **目前語言**的根（zh＝網站根、ja＝`/ja/`） | 側欄事件、about/contact/privacy（ja 樹有鏡像頁）、返回首頁 |
| `root_base`（`render_page` 新參數） | **網站根** | 只有站層產物：`llms.txt`、`sitemap.xml`（ja 樹要再多上一層） |
| `lang_switch_html(lang, root_base)` | 語言首頁固定是 `<root>/index.html`（預設語）與 `<root>/<lang>/index.html` | 語言切換按鈕。**舊版拿 home_link 推語言根再 `+"../index.html"`** → 在 `/ja/about/`、`/ja/events/**` 會跳出網站根之外 |

**其他兩處**：
- 信任頁 `build_trust_pages` 舊版傳 `base=""`（根目錄深度），但頁在 `/about/index.html`（深度 1；ja 深度 2）→ 側欄 map／事件／llms.txt 連結全 404（zh＋ja 共 ~98 條）。現由 `prefix` 的層數推深度，不寫死。
- 事件正文內的 `.md` 互連（來源 md 用**倉儲內**相對路徑，例 `../08/0828_….md`）由 `build_md_link_index()`＋`fix_md_links()` 改寫成事件頁 URL：先以「來源 md 所在目錄」解析、再以倉儲根解析，都不中則用 **basename 唯一比對**兜底（印 `[note] …層級不對`，因為那是來源 md 少寫一層 `../`，例：`颱風/2026/08` → `災情/2026/08` 需要三層 `../`，現行檔內寫兩層）；解析不到才拆成純文字（印 `[warning]`，絕不留斷鏈）。**不改事件正文**（AGENTS.md：僅結構錯誤可改既有內容）。

**驗證**：`build/.venv/bin/python build/check_links.py`（WORKFLOW §3 ②；exit 0＝無斷鏈）。已知限制：`404.html` 的相對連結另計不計入 exit——CF Pages 對任何深度的未匹配路徑都送同一份 top-level `404.html`，瀏覽器以被請求的 URL 為基準解析相對連結；改絕對 URL 又會讓 GitHub Pages mirror（`/Weather/` 前綴）跳回 CF 域名，故刻意保留。

**順帶**：更新頻率文案不再寫死「每小時」——`i18n._cron_interval_hours()` 解析 `build/cron.txt`（排程的單一事實來源）→ zh「每 2 小時」／ja「2時間ごと」，套用於 `updated`、`map_updated`、`map_rain_note`、`footer`、`meta_desc`、about 正文，以及 `site.py` 的 llms.txt／llms-full.txt／站對外 AGENTS.md 與 `cbph` 的 GeoJSON note（文案內用 `%IV%` 佔位，因那些長段落本身就是 `.format` 模板、`{}` 會打架）。改排程只改 `build/cron.txt`＋部署機 crontab。

## AI bot 可偵測性強化（✅ 2026/9/15 完成並上線；背景：is-agentic.com 掃描 52/100）

**已實作（2026/9/15）**：首頁 JSON-LD（WebSite＋Organization）與事件頁 Article JSON-LD；全頁 meta description／Open Graph（含 `assets/og.png`，`build/make_og_image.py` 純 stdlib 產生）／canonical；`<meta name="is-agentic-site-type" content="content">`；信任頁 `/about/`、`/contact/`、`/privacy/`（zh＋ja，各 ≥500 字）；404 頁加 agent 指引（llms.txt／sitemap.xml 連結）；llms.txt 加「使用指引」段；footer 加關於／聯絡／隱私＋llms.txt／sitemap 連結。實作於 `build/site.py`（`render_page` 加 `page_url`/`jsonld` 參、`build_trust_pages()`）＋`build/i18n.py`。

**分數收尾二輪（2026/9/15，78→目標 ~85）**：Organization JSON-LD 補 `contactPoint`（GitHub Issues）＋國家層級 `address`；build 產出站對外的 `/AGENTS.md`（agent when-to-use/引用指引，與 repo 內 AGENTS.md 不同）；404 頁加字面 markdown 語法區塊（agent-friendly 404 滿分要求）；llms.txt 引用 `/AGENTS.md`。

**不追項（錯配、有意跳過）**：markdown content negotiation（需 Pages Function 動態 Accept 協商，破壞純靜態不變項；agent 取 markdown 已由 `llms-full.txt` 覆蓋）；OpenAPI／JSON error／api-catalog（RFC 9727）／Web Bot Auth（RFC 9421）（本站無公開 API——掃描器的「API」視角是跟隨 llms.txt 連結抓到 CWA 的 apidoc YAML 觸發的，非本站問題）。**注意**：`is-agentic-site-type` tag 只改預設顯示視角、不加分；API 視角仍會計分，故分數天花板受限。

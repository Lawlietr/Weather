"""多語言 UI 字串表（TODO §七.4）。

設計：
- 加新語言 = 在 STRINGS 加一個 dict，不改模板、不重寫頁面。
- 內容（災情/颱風 markdown 正文）不在此表：各語言保留原文顯示，
  事件子頁上方以 content_note 提示。
- CWA 提供的資料（颱風名、雨量站名、特報全文、影響區域）為中文原文，
  非預設語言頁面以 cwa_data_note 提示。
- t(lang, key) 在語言缺 key 時回退預設語言，再缺則回傳 key 本身（不炸 build）。
"""

DEFAULT_LANG = "zh-Hant"
LANGS = ["zh-Hant", "ja"]

STRINGS = {
"zh-Hant": {
    # --- 站體 / 導覽 ---
    "site_title": "🌦 台灣天氣與災情總覽",
    "nav_home": "🏠 總覽",
    "nav_active": "目前事件",
    "nav_ended": "過去事件",
    "nav_no_county": "目前無該縣市的災情紀錄",
    "updated": "產生時間：{ts}（每 2 小時自動更新，非即時）",
    "aria_menu": "開啟事件清單",
    "aria_theme": "切換日夜主題",
    "footer": "本頁內容彙整自中央氣象署公開資料與新聞媒體公開報導，每筆災情請點入來源連結查證原文；官方資訊以中央氣象署與各縣市政府公告為準。本站每 2 小時自動更新，資訊可能落後。",
    "github_pending": "GitHub（網址待提供）",
    "lang_self": "繁體中文",
    # --- 首頁 ---
    "hero_period": "影響期間：{p}",
    "hero_source": "資料來源：{src}",
    "chip_jump": "跳到{county}災情",  # 注意：此 key 在下方 county_section 前被引用
    "hero_latest": "最新進展",
    "hero_no_rows": "（無災情表格資料）",
    "hero_cta": "查看完整事件紀錄 →",
    "no_event_title": "目前無重大氣象事件",
    "no_event_body": "無進行中的災情事件；如有異動將手動更新後呈現。",
    "county_section": "各縣市災情",
    "county_latest": "最新 {n} 筆",  # 見上 chip_jump
    "back_to_top": "↑ 回頂端",
    "archive_title": "過去事件封存",
    # --- 404 頁 ---
    "notfound_title": "找不到頁面",
    "notfound_body": "您尋找的頁面不存在或已移動。請返回總覽。",
    "notfound_agent": "供 agent／自動化工具：",
    "notfound_llms": "llms.txt（本站內容索引）",
    "notfound_sitemap": "sitemap.xml（完整頁面清單）",
    # --- 事件子頁 ---
    "status_active": "目前事件",
    "status_ended": "已封存事件",
    "back_home": "← 返回總覽",
    "content_note": "※ 事件原文為中文，本頁保留原文顯示。",
    # --- severity 徽章 ---
    "sev_red": "🔴 重大",
    "sev_yellow": "🟡 警戒",
    "sev_green": "🟢 一般",
    # --- CWA 氣象總覽 ---
    "cwa_title": "氣象總覽（中央氣象署）",
    "cwa_data_note": "",
    "typhoon_title": "颱風動態",
    "typhoon_none": "目前無活動中熱帶氣旋（西北太平洋及南海）。",
    "typhoon_nodata": "（有氣旋紀錄但無分析資料）",
    "stale_tag": "（舊資料：{ts}）",
    "typhoon_no": "（{year} 第{no} 號）",
    "obs_line": "最新觀測（{ts}）：{pos}｜{cat}｜最大風速 {w} m/s｜陣風 {g} m/s｜氣壓 {p} hPa｜{move}",
    "moving": "{dir} 方向移動，{speed} km/h",
    "future_fc": "未來預報",
    "th_time": "時間",
    "th_pos": "位置",
    "th_wind": "最大風速",
    "th_pressure": "氣壓",
    "no_fc": "（無預報資料）",
    "legend_analysis": "分析軌跡",
    "legend_forecast": "預報路徑",
    "legend_wind": "15 m/s 暴風半徑",
    "latest_tag": "{name}（最新）",
    "city_taipei": "台北",
    "city_taichung": "台中",
    "city_kaoxiong": "高雄",
    "city_hualien": "花蓮",
    "city_taitung": "台東",
    "alert_title": "警報與特報",
    "marine_badge": "海上颱風警報",
    "report_no": "（第 {n} 報）",
    "typhoon_label": "颱風：{n}",
    "effective": "生效 {ts}",
    "view_full": "查看特報全文",
    "issued": "發布 {ts}",
    "valid": "有效 {ts}",
    "affected": "影響區域：{a}",
    "lifted_note": "（已解除，供參考）",
    "rain_title": "雨量觀測站 TOP 10",
    "rain_th_station": "雨量站",
    "rain_th_area": "縣市/鄉鎮",
    "rain_th_today": "本日累計 (mm)",
    "rain_th_1h": "近 1 小時 (mm)",
    "rain_th_24h": "近 24 小時 (mm)",
    "rain_note": "「本日累計」= 當日 0 時至觀測時間（{ts}）；短延時強降雨請看「近 1 小時」。CWA O-A0002-001，每 10 分鐘更新。",
    "rain_details": "當日累計雨量 TOP 10（點開）",
    "cwa_fail": "本次 build 無法取得 CWA 資料，且無可用快取。",
    "cwa_fail_fix": "{why}。設定 CWA_API_KEY 後重新 build。",
    "cwa_warn_partial": "⚠️ 本次 build 部分 CWA 資料來源無法取得（{bad}），以下含舊資料。",
    "cwa_warn_cache": "⚠️ 本次 build 無法連線 CWA API，以下為上次成功抓取之快取資料。",
    # --- 停班停課（人事行政總處 CAP feed；置位規則見 cwa.cwa_section_html 註解）---
    "susp_title": "停班停課（各縣市政府公告）",
    "susp_count": "共 {n} 筆",
    "susp_none": "目前無停班停課公告。",
    "susp_asof": "資料截至 {ts}（build 時抓取、非即時）",
    "susp_note": "公告時程以官方為準：全日或上午停班於前一日 19:00–22:00 前發布；下午或晚間停班於當日上午 10:30 前發布。",
    "susp_source": "資料來源：行政院人事行政總處（由各縣市政府公告）",
    "susp_page": "人事總處停班停課查詢頁",
    "susp_window": "影響時段 {a}–{b}",
    "susp_sent": "公告於 {ts}",
    "susp_cap": "CAP 原文",
    # --- 目前風險狀態列（由 CWA 現況警報推導，與事件歷史分級無關）---
    "risk_label_red": "🔴 目前危險中",
    "risk_label_yellow": "🟡 警戒生效中",
    "risk_label_green": "🟢 目前無危險信號",
    "risk_label_neutral": "⚪ 常態監視（目前無風險信號）",
    "risk_label_unknown": "⚪ 狀態未知（CWA 資料無法取得）",
    "risk_none": "目前無生效中熱帶氣旋、海上颱風警報或豪雨/強風特報。",
    "risk_neutral": "目前無生效中警報/特報（最近：{recent} 已解除）；無異常天氣活動，常態監視中。",
    "risk_asof": "依中央氣象署目前之警報與特報判斷（網頁產生於 {ts}）；此為目前風險信號，不等於事件歷史分級。",
    "risk_typhoon": "熱帶氣旋 {name} 生效中{cat}",
    "risk_marine": "{title}（生效中）",
    "risk_report": "{name}（有效至 {valid}）",
    # --- 站體 meta（SEO／agent） ---
    "meta_desc": "記錄台灣目前與歷史上發生的颱風、豪雨等天氣事件與各縣市災情的純靜態網站；氣象資料來源中央氣象署（CWA），每 2 小時自動 build，非即時。",
    "footer_about": "關於本站",
    "footer_contact": "聯絡",
    "footer_privacy": "隱私",
    # --- 信任頁（/about /contact /privacy） ---
    "about_title": "關於本站",
    "about_body": """本站是記錄台灣目前與歷史上發生的天氣事件（颱風、豪雨、低壓帶等）與各縣市災情的純靜態網站。

資料來源：颱風軌跡、警報與特報、雨量觀測站、風力等氣象資料取自中央氣象署（CWA）Open Data API，build 時於本機抓取；災防告警區取自 CWA 災防告警系統（PWS）；災情紀錄彙整自各縣市政府公告與新聞媒體公開報導，每筆均標注來源。

更新方式：本站採人工維護，每 2 小時自動執行 build 與部署；頁面顯示的氣象資料是 build 時的快照，非即時。颱風警報期間氣象資料約每 3～6 小時更新一次；緊急資訊請直接查中央氣象署官方網站與各縣市政府公告。

網站結構：首頁含氣象彙整與各縣市災情總覽；各事件頁記錄事件完整過程（警報時程、災情紀錄、交通影響、防災作為）；/map/ 為災防告警地圖；/ja/ 為日文介面（事件正文仍為繁中原文）。

AI agent 與自動化工具：請以 /llms.txt 讀取本站內容索引、/llms-full.txt 讀取全部事件全文。

授權與免責：本站內容（災情紀錄與彙整）採 CC BY-NC-SA 4.0；程式碼為 GNU AGPLv3；CWA 資料以 CWA 官方條款為準。本站僅供資訊彙整與學習參考，不取代任何官方資訊；官方資訊一律以中央氣象署與各縣市政府公告為準。""",
    "contact_title": "聯絡",
    "contact_body": """本站不設表單，請透過 GitHub Issues 聯繫：https://github.com/Lawlietr/Weather/issues

歡迎提出的問題類型：
- 災情紀錄更正：颱風、雨量、警報特報等內容與 CWA 官方或實際情況不符。請附上相關事件頁連結、問題段落，以及您查到的官方來源連結，以便逐項查證。
- 死連結或引用錯誤：新聞來源連結失效、出處未標注、來源日期錯誤。
- 網站顯示問題：版面錯亂、錯字、日文介面用詞、地圖頁問題等。
- 改善建議：希望新增的資料類型、顯示方式或功能。

回應方式：本站為個人維護，Issue 由人工在每次 build 後查閱，沒有保證回應時間（SLA）。緊急的天氣資訊（警報發布、停班停課公告、避難資訊等）請直接以中央氣象署、教育部與各縣市政府的最新公告為準，請勿等待本站更新。

引用本站的方式：引用時請註明頁首的「產生時間」與該筆紀錄的時戳，並保留災情紀錄所附的新聞來源連結；氣象資料請註明出處為中央氣象署（CWA）Open Data API 及資料產生時間。

授權：本站內容（災情紀錄與彙整）採 CC BY-NC-SA 4.0（姓名標示、非商業性、相同方式分享）；程式碼為 GNU AGPLv3。""",
    "privacy_title": "隱私",
    "privacy_body": """本站是純靜態網站，不收集、不儲存、也不分析任何訪客資訊。

追蹤與儲存：
- 不嵌入任何分析工具（如 Google Analytics）。
- 不嵌入任何第三方追蹤腳本、廣告標記或指紋程式碼。
- 不送出任何 cookie。
- 唯一的儲存是您的瀏覽器 localStorage 中的一個設定（key: wtf-theme），為您選擇的日夜主題；它只存在於您自己的裝置上，不會傳送到任何伺服器。

外部請求：本站頁面不含任何外部資源請求（樣式與腳本全部内嵌於頁面；地圖頁使用自託的 Leaflet 與離線瓦片）。您瀏覽本站時，網路請求的唯一對象就是本站主機（Cloudflare Pages）。

外部連結：本站包含大量外部連結（新聞來源連結、GitHub、中央氣象署官網等）。點擊這些連結後，該網站的隱私做法即由該網站負責，與本站無關。

資料來源與授權：氣象資料取自中央氣象署（CWA）Open Data API；災情紀錄彙整自各縣市政府與新聞媒體的公開報導。本站內容採 CC BY-NC-SA 4.0；程式碼為 GNU AGPLv3。

如果您發現本站出現您認為涉及個人隱私的內容（例如新聞引用誤植），請透過 https://github.com/Lawlietr/Weather/issues 開 Issue 告知，會儘速查證並處理。""",
    # --- 颱風強度分類（CWA 級別） ---
    "ty_cat_super": "超強颱風",
    "ty_cat_strong": "強颱風",
    "ty_cat_vstrong": "猛烈颱風",
    "ty_cat_mod": "中度颱風",
    "ty_cat_weak": "輕度颱風",
    "ty_cat_td": "熱帶性低氣壓",
    # --- 災防告警地圖 /map/（TODO §2）---
    "map_enter": "🗺 告警地圖",
    "map_title": "災防告警地圖｜台灣天氣與災情總覽",
    "map_title_short": "🗺 災防告警地圖",
    "map_updated": "產生時間：{ts}（每 2 小時更新，非即時）",
    "map_alert_count": "告警地圖・生效 {n} 筆",
    "map_close": "關閉",
    "map_layers": "圖層",
    "map_detail_title": "告警詳情",
    "map_detail_hint": "點擊地圖上的告警區域查看詳情",
    "map_official": "官方編號",
    "map_effective": "生效時段",
    "map_county": "影響縣市",
    "map_town": "影響鄉鎮",
    "map_desc": "告警原文",
    "map_cmam": "細胞廣播",
    "map_cb_on": "細胞廣播已啟動",
    "map_cb_off": "細胞廣播未啟動",
    "map_repo": "本站相關災情紀錄",
    "map_no_repo": "無相關災情紀錄",
    "map_src": "回到 CWA 災防告警官方頁",
    "map_none": "目前無生效中的災防告警",
    "map_osm": "© OpenStreetMap contributors",
    "map_source": "資料來源：中央氣象署災防告警系統（PWS）、雨量站（O-A0002-001）",
    "map_noscript": "JavaScript 已停用：以下為靜態告警清單；互動地圖需啟用 JS。",
    "map_noscript_rain": "雨量站觀測（超閾值）",
    "map_layer_rain": "雨量站（超閾值）",
    "map_rain_l3": "1小時≥50mm 或 24小時≥250mm",
    "map_rain_l2": "1小時≥25mm 或 24小時≥100mm",
    "map_rain_l1": "1小時≥10mm 或 24小時≥50mm",
    "map_rain_p1hr": "近 1 小時",
    "map_rain_p24hr": "近 24 小時",
    "map_rain_pday": "本日累計",
    "map_rain_obs": "觀測時間",
    "map_rain_loc": "位置",
    "map_rain_note": "測站資料由 CWA 每 10 分鐘更新；本圖為每 2 小時刷新的快照",
},

"ja": {
    # --- 站体 / ナビ ---
    "site_title": "🌦 台湾の天気と災害情報",
    "nav_home": "🏠 総覧",
    "nav_active": "現在進行中のイベント",
    "nav_ended": "過去のイベント",
    "nav_no_county": "その地域の災害記録はありません",
    "updated": "生成時刻：{ts}（2時間ごとに自動更新・リアルタイムではありません）",
    "aria_menu": "イベント一覧を開く",
    "aria_theme": "テーマ切替（夜間/日間）",
    "footer": "本ページの情報は中央気象局（CWA）の公開データと各ニュースメディアの公開報道をまとめたものです。個別の災害については出典リンクから原文を確認してください。公式情報は中央気象局および各市県政府の発表を基準とします。本サイトは2時間ごとに自動更新されますが、情報が遅れている可能性があります。",
    "github_pending": "GitHub（URL 未設定）",
    "lang_self": "日本語",
    # --- ホーム ---
    "hero_period": "影響期間：{p}",
    "hero_source": "出典：{src}",
    "chip_jump": "{county}の災害情報へ",  # noqa: 同 zh 版位置
    "hero_latest": "最新状況",
    "hero_no_rows": "（災害テーブルデータなし）",
    "hero_cta": "詳細なイベント記録を見る →",
    "no_event_title": "現在、重大な気象イベントはありません",
    "no_event_body": "進行中の災害イベントはありません。変更があれば手動更新のうえ表示されます。",
    "county_section": "地域別災害情報",
    "county_latest": "最新 {n} 件",  # 見上 chip_jump
    "back_to_top": "↑ トップへ",
    "archive_title": "過去のイベント（アーカイブ）",
    # --- 404 ページ ---
    "notfound_title": "ページが見つかりません",
    "notfound_body": "お探しのページは存在しないか、移動した可能性があります。総覧に戻ってください。",
    "notfound_agent": "AI エージェント・自動化ツール向け：",
    "notfound_llms": "llms.txt（サイト内容インデックス）",
    "notfound_sitemap": "sitemap.xml（全ページ一覧）",
    # --- イベント詳細 ---
    "status_active": "現在進行中",
    "status_ended": "アーカイブ済み",
    "back_home": "← 総覧に戻る",
    "content_note": "※ 本文は原文（中国語）のまま表示しています。",
    # --- severity バッジ ---
    "sev_red": "🔴 重大",
    "sev_yellow": "🟡 警戒",
    "sev_green": "🟢 一般",
    # --- CWA 気象総覧 ---
    "cwa_title": "気象総覧（中央気象局）",
    "cwa_data_note": "※ 台風名・地域名・雨量観測局名・特別警報本文は中央気象局（CWA）のデータのため、原文（中国語）のまま表示しています。",
    "typhoon_title": "台風の動向",
    "typhoon_none": "現在、活動中の熱帯低気圧はありません（北西太平洋・南シナ海）。",
    "typhoon_nodata": "（気旋の記録はあるが解析データなし）",
    "stale_tag": "（古いデータ：{ts}）",
    "typhoon_no": "（{year}年第{no}号）",
    "obs_line": "最新観測（{ts}）：{pos}｜{cat}｜最大風速 {w} m/s｜突風 {g} m/s｜気圧 {p} hPa｜{move}",
    "moving": "{dir}方向に {speed} km/h で移動",
    "future_fc": "今後の予報",
    "th_time": "時間",
    "th_pos": "位置",
    "th_wind": "最大風速",
    "th_pressure": "気圧",
    "no_fc": "（予報データなし）",
    "legend_analysis": "解析軌跡",
    "legend_forecast": "予報経路",
    "legend_wind": "15 m/s 暴風半径",
    "latest_tag": "{name}（最新）",
    "city_taipei": "台北",
    "city_taichung": "台中",
    "city_kaoxiong": "高雄",
    "city_hualien": "花蓮",
    "city_taitung": "台東",
    "alert_title": "警報と特別警報",
    "marine_badge": "海洋台風警報",
    "report_no": "（第{n}報）",
    "typhoon_label": "台風：{n}",
    "effective": "発効 {ts}",
    "view_full": "特別警報全文を見る",
    "issued": "発表 {ts}",
    "valid": "有効 {ts}",
    "affected": "影響地域：{a}",
    "lifted_note": "（解除済み、参考用）",
    "rain_title": "雨量観測局 TOP 10",
    "rain_th_station": "雨量観測局",
    "rain_th_area": "都道府県・市区町村",
    "rain_th_today": "当日累計 (mm)",
    "rain_th_1h": "直近1時間 (mm)",
    "rain_th_24h": "直近24時間 (mm)",
    "rain_note": "「当日累計」= 当日 0 時から観測時刻（{ts}）までの雨量；短時間集中豪雨は「直近1時間」をご覧ください。CWA O-A0002-001、10 分ごとに更新。",
    "rain_details": "当日累計雨量 TOP 10（クリックで展開）",
    "cwa_fail": "今回のビルドで CWA データを取得できず、利用可能なキャッシュもありません。",
    "cwa_fail_fix": "{why}。CWA_API_KEY を設定のうえ再ビルドしてください。",
    "cwa_warn_partial": "⚠️ 今回のビルドで一部の CWA データソースを取得できませんでした（{bad}）。以下は古いデータを含みます。",
    "cwa_warn_cache": "⚠️ 今回のビルドで CWA API に接続できませんでした。以下は前回取得成功時のキャッシュデータです。",
    # --- 休み・登校中止（人事行政総処 CAP feed；配置規則は cwa.cwa_section_html のコメント参照）---
    "susp_title": "休み・登校中止（各県市政府の発表）",
    "susp_count": "全 {n} 件",
    "susp_none": "現在、休み・登校中止の発表はありません。",
    "susp_asof": "データは {ts} 時点（ビルド時取得、リアルタイムではありません）",
    "susp_note": "発表タイミングは公定準拠：1日または午前中の休みは前日 19:00–22:00 までに、午後または夜間の休みは当日午前 10:30 までに発表されます。",
    "susp_source": "データソース：行政院人事行政総処（各県市政府が発表）",
    "susp_page": "人事総処 休み・登校中止照会ページ",
    "susp_window": "対象期間 {a}–{b}",
    "susp_sent": "発表 {ts}",
    "susp_cap": "CAP 原文",
    # --- 現在のリスク状態バー（CWA の現行警報から導出、イベントの過去段階とは無関係）---
    "risk_label_red": "🔴 現在危険",
    "risk_label_yellow": "🟡 警戒中",
    "risk_label_green": "🟢 現在の危険シグナルなし",
    "risk_label_neutral": "⚪ 通常監視（現在の危険シグナルなし）",
    "risk_label_unknown": "⚪ 状況不明（CWA データ取得不可）",
    "risk_none": "現在、活動中の熱帯低気圧、海洋台風警報、大雨・強風特別警報はありません。",
    "risk_neutral": "現在、発効中の警報・特別警報はありません（直近：{recent} 解除済み）；異常な天気活動はなく、通常監視中です。",
    "risk_asof": "中央気象局（CWA）の現在の警報・特別警報に基づく（ページ生成 {ts}）；これは現在のリスクシグナルであり、イベントの過去段階を意味しません。",
    "risk_typhoon": "熱帯低気圧 {name} が発効中{cat}",
    "risk_marine": "{title}（発効中）",
    "risk_report": "{name}（有効 {valid}）",
    # --- サイトメタ情報（SEO／エージェント） ---
    "meta_desc": "台湾で現在発生中・過去に発生した台風・大雨などの気象イベントと各地域の災害を記録する純静的サイト。気象データは中央気象局（CWA）から取得、2 時間ごとに自動ビルド（リアルタイムではありません）。",
    "footer_about": "このサイトについて",
    "footer_contact": "連絡先",
    "footer_privacy": "プライバシー",
    # --- 信頼ページ（/about /contact /privacy） ---
    "about_title": "このサイトについて",
    "about_body": """当サイトは、台湾で現在および過去に発生した気象イベント（台風、大雨、低気圧など）と各地域の災害情報を記録する純静的サイトです。

データソース：台風の経路、警報・特別警報、雨量観測局、風速などの気象データは中央気象局（CWA）Open Data API からビルド時にローカルで取得します。災害防警報領域は CWA 災害防警報システム（PWS）から取得。災害記録は各市県政府の発表とニュースメディアの公開報道をまとめたもので、すべて出典を明記しています。

更新方法：当サイトは人間による保守のもと、2 時間ごとに自動でビルドとデプロイを実行します。ページに表示される気象データはビルド時点のスナップショットであり、リアルタイムではありません。台風警報中は気象データが約 3〜6 時間ごとに更新されます。緊急情報は中央気象局の公式サイトと各市県政府の発表を直接ご確認ください。

サイト構成：トップページに気象総覧と地域別災害情報総覧を掲載。各イベントページにはイベントの経緯（警報の推移、災害記録、交通影響、防災対応）を記録。/map/ は災害防警報マップ、/ja/ は日本語 UI（イベント本文は中国語原文のまま）です。

AI エージェント・自動化ツール向け：/llms.txt でサイト内容のインデックス、/llms-full.txt で全イベントの全文をお読みください。

ライセンスと免責：サイト内容（災害記録とまとめ）は CC BY-NC-SA 4.0、コードは GNU AGPLv3、CWA データは CWA の利用規約に準じます。当サイトは情報まとめ・学習用の参考であり、公式情報に代わるものではありません。公式情報は中央気象局と各市県政府の発表を基準とします。""",
    "contact_title": "連絡先",
    "contact_body": """当サイトにはフォームを設置していません。GitHub Issues からご連絡ください：https://github.com/Lawlietr/Weather/issues

受け付けているIssueの種類：
- 災害記録の訂正：台風・雨量・警報・特別警報などの内容が CWA 公式や実際の状況と一致しない場合。関連するイベントページのリンク、問題の段落、およびご確認いただいた公式ソースのリンクをお付けください。
- 死リンクや引用エラー：ニュース出典リンクが無効、出典未明記、出典の日付エラーなど。
- サイト表示の問題：レイアウト崩れ、誤字、日本語 UI の表記、マップページの問題など。
- 改善提案：追加してほしいデータ種類・表示方法・機能など。

対応方法：当サイトは個人が保守しており、Issue は各ビルド後に人工で確認します。保証された対応時間（SLA）はありません。緊急の天気情報（警報発表、停学・休校の発表、避難情報など）は、中央気象局・教育部・各市県政府の最新の発表を直接ご確認ください。当サイトの更新を待たないでください。

当サイトを引き用いる方法：引用時はページ上部の「生成時間」と各記録のタイムスタンプを明記し、災害記録に付随するニュース出典リンクを保持してください。気象データは中央気象局（CWA）Open Data API からの取得であることと、データ生成時刻を明記してください。

ライセンス：サイト内容（災害記録とまとめ）は CC BY-NC-SA 4.0（表示・非営利・同じ条件で共有）、コードは GNU AGPLv3 です。""",
    "privacy_title": "プライバシー",
    "privacy_body": """当サイトは純静的サイトであり、訪問者からの情報を収集・保存・解析しません。

トラッキングと保存：
- どの分析ツール（Google Analytics など）も組み込んでいません。
- サードパーティのトラッキングスクリプト、広告ピクセル、フィンガリングコードは組み込んでいません。
- どの cookie も送信しません。
- 唯一の保存は、ご自身のブラウザの localStorage に入る設定（key: wtf-theme）であり、あなたが選んだ夜間/日間テーマです。これはあなたの端末にのみ保存され、どのサーバーにも送信されません。

外部リクエスト：当サイトのページには外部リソースへのリクエストが一切含まれません（スタイルとスクリプトはすべてページ内にインライン化。マップページは自社ホストの Leaflet とオフラインタイルを使用）。当サイトを閲覧する際、ネットワークリクエストの対象は当サイトホスト（Cloudflare Pages）のみです。

外部リンク：当サイトには多くの外部リンク（ニュース出典リンク、GitHub、中央気象局公式サイトなど）が含まれています。これらのリンクをクリックした後、該当サイトのプライバシー運用が適用され、当サイトとは無関係です。

データソースとライセンス：気象データは中央気象局（CWA）Open Data API から取得。災害記録は各市県政府とニュースメディアの公開報道をまとめたものです。サイト内容は CC BY-NC-SA 4.0、コードは GNU AGPLv3 です。

当サイトに個人プライバシーに関わると考える内容（ニュース引用の誤植など）を発見された場合は、https://github.com/Lawlietr/Weather/issues で Issue を開いてお知らせください。速やかに確認し対応します。""",
    # --- 台風強度分類（CWA 級別） ---
    "ty_cat_super": "猛烈な台風",
    "ty_cat_strong": "非常に強い台風",
    "ty_cat_vstrong": "強い台風",
    "ty_cat_mod": "台風",
    "ty_cat_weak": "弱い台風",
    "ty_cat_td": "熱帯低気圧",
    # --- 災害防警報マップ /map/（TODO §2）---
    "map_enter": "🗺 警戒マップ",
    "map_title": "災害警戒マップ｜台湾の天気と災害情報",
    "map_title_short": "🗺 災害警戒マップ",
    "map_updated": "生成時間：{ts}（2時間ごとに更新・リアルタイムではありません）",
    "map_alert_count": "警戒マップ・有効 {n} 件",
    "map_close": "閉じる",
    "map_layers": "レイヤー",
    "map_detail_title": "警報の詳細",
    "map_detail_hint": "地図上の警戒領域をクリックすると詳細が表示されます",
    "map_official": "公式番号",
    "map_effective": "有効期間",
    "map_county": "影響県市",
    "map_town": "影響町村",
    "map_desc": "告警原文",
    "map_cmam": "セルブロードキャスト",
    "map_cb_on": "セルブロードキャスト有効",
    "map_cb_off": "セルブロードキャスト無効",
    "map_repo": "当サイトの関連災害記録",
    "map_no_repo": "関連する災害記録はありません",
    "map_src": "CWA災害防報公式ページへ戻る",
    "map_none": "現在有効な災害防警報はありません",
    "map_osm": "© OpenStreetMap contributors",
    "map_source": "出典：中央気象局災害防報システム（PWS）、雨量観測点（O-A0002-001）",
    "map_noscript": "JavaScript が無効です：以下は静的な警報リストです。インタラクティブ地図には JS が必要です。",
    "map_noscript_rain": "雨量観測点（閾値超過）",
    "map_layer_rain": "雨量観測点（閾値超過）",
    "map_rain_l3": "1時間≥50mm または 24時間≥250mm",
    "map_rain_l2": "1時間≥25mm または 24時間≥100mm",
    "map_rain_l1": "1時間≥10mm または 24時間≥50mm",
    "map_rain_p1hr": "直近1時間",
    "map_rain_p24hr": "直近24時間",
    "map_rain_pday": "当日累計",
    "map_rain_obs": "観測時刻",
    "map_rain_loc": "所在地",
    "map_rain_note": "測站データはCWAが10分ごとに更新。本図は2時間ごとのスナップショットです",
},
}


def t(lang, key, **kw):
    """取字串：語言缺 key → 回退預設語言 → 再缺回傳 key（不炸 build）。"""
    table = STRINGS.get(lang, STRINGS[DEFAULT_LANG])
    s = table.get(key, STRINGS[DEFAULT_LANG].get(key, key))
    return s.format(**kw) if kw else s


def is_default(lang):
    return lang == DEFAULT_LANG

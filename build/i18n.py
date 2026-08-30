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
    "updated": "產生時間：{ts}（手動生成，非即時）",
    "aria_menu": "開啟事件清單",
    "aria_theme": "切換日夜主題",
    "footer": "本頁內容彙整自中央氣象署公開資料與新聞媒體公開報導，每筆災情請點入來源連結查證原文；官方資訊以中央氣象署與各縣市政府公告為準。本頁採手動更新，資訊可能落後。",
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
    # --- 目前風險狀態列（由 CWA 現況警報推導，與事件歷史分級無關）---
    "risk_label_red": "🔴 目前危險中",
    "risk_label_yellow": "🟡 警戒生效中",
    "risk_label_green": "🟢 目前無危險信號",
    "risk_label_unknown": "⚪ 狀態未知（CWA 資料無法取得）",
    "risk_none": "目前無生效中熱帶氣旋、海上颱風警報或豪雨/強風特報。",
    "risk_asof": "依中央氣象署目前之警報與特報判斷（網頁產生於 {ts}）；此為目前風險信號，不等於事件歷史分級。",
    "risk_typhoon": "熱帶氣旋 {name} 生效中{cat}",
    "risk_marine": "{title}（生效中）",
    "risk_report": "{name}（有效至 {valid}）",
    # --- 颱風強度分類（CWA 級別） ---
    "ty_cat_super": "超強颱風",
    "ty_cat_strong": "強颱風",
    "ty_cat_vstrong": "猛烈颱風",
    "ty_cat_mod": "中度颱風",
    "ty_cat_weak": "輕度颱風",
    "ty_cat_td": "熱帶性低氣壓",
},

"ja": {
    # --- 站体 / ナビ ---
    "site_title": "🌦 台湾の天気と災害情報",
    "nav_home": "🏠 総覧",
    "nav_active": "現在進行中のイベント",
    "nav_ended": "過去のイベント",
    "nav_no_county": "その地域の災害記録はありません",
    "updated": "生成時間：{ts}（手動生成・リアルタイムではありません）",
    "aria_menu": "イベント一覧を開く",
    "aria_theme": "テーマ切替（夜間/日間）",
    "footer": "本ページの情報は中央気象局（CWA）の公開データと各ニュースメディアの公開報道をまとめたものです。個別の災害については出典リンクから原文を確認してください。公式情報は中央気象局および各市県政府の発表を基準とします。本ページは手動更新のため、情報が遅れている可能性があります。",
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
    # --- 現在のリスク状態バー（CWA の現行警報から導出、イベントの過去段階とは無関係）---
    "risk_label_red": "🔴 現在危険",
    "risk_label_yellow": "🟡 警戒中",
    "risk_label_green": "🟢 現在の危険シグナルなし",
    "risk_label_unknown": "⚪ 状況不明（CWA データ取得不可）",
    "risk_none": "現在、活動中の熱帯低気圧、海洋台風警報、大雨・強風特別警報はありません。",
    "risk_asof": "中央気象局（CWA）の現在の警報・特別警報に基づく（ページ生成 {ts}）；これは現在のリスクシグナルであり、イベントの過去段階を意味しません。",
    "risk_typhoon": "熱帯低気圧 {name} が発効中{cat}",
    "risk_marine": "{title}（発効中）",
    "risk_report": "{name}（有効 {valid}）",
    # --- 台風強度分類（CWA 級別） ---
    "ty_cat_super": "猛烈な台風",
    "ty_cat_strong": "非常に強い台風",
    "ty_cat_vstrong": "強い台風",
    "ty_cat_mod": "台風",
    "ty_cat_weak": "弱い台風",
    "ty_cat_td": "熱帯低気圧",
},
}


def t(lang, key, **kw):
    """取字串：語言缺 key → 回退預設語言 → 再缺回傳 key（不炸 build）。"""
    table = STRINGS.get(lang, STRINGS[DEFAULT_LANG])
    s = table.get(key, STRINGS[DEFAULT_LANG].get(key, key))
    return s.format(**kw) if kw else s


def is_default(lang):
    return lang == DEFAULT_LANG

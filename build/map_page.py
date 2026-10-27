"""災防告警地圖 /map/ 獨立頁（design/map.md 執行順序 3）。

設計（2026/9/1 定案）：
- Leaflet 只在此頁載入（自託 build/static/leaflet/、無 CDN）；首頁維持零 JS
  ＋現有靜態 SVG 軌跡圖，只加「查看地圖」入口。
- 離線自駕（硬需求）：瓦片為 build 時抓取之本地檔（見 tiles.py），
  Leaflet 指向 public/assets/tiles/ → 前端零外部請求。
- 佈局：全幅地圖（預設全台視角 z8）＋右側欄（行動版 bottom sheet）：
  點擊詳情卡＋圖例＋圖層開關＋「產生時間」（快照標示必顯示）。
- 資料：build/map.geo.json（cbph 災防告警 polygon 快照＋雨量站觀測點 Point，
  build 時由 cbph.py＋cwa.fetch_rain_points() 先寫）；此模組只渲染、不新增抓取。
  顏色/等級閾值邏輯在 build 端，前端只負責渲染。
- 無 JS fallback：靜態告警清單＋回總覽連結（靜態 SVG 總覽在首頁）。
- 瓦片署名義務：頁尾必顯示「© OpenStreetMap contributors」（瓦片來源 OSM 德國社群 server tile.openstreetmap.de，2026/9/2 起；官方 server 對本機 IP 假 200 封鎖，見 tiles.py 註）。
"""
import json
from pathlib import Path

from i18n import t, LANGS, is_default
from cbph import TYPES  # slug → (中文名, 配色)，與 cbph UI 一致
# ⚠️ 地圖視野常數的單一事實來源在 `build/tiles.py`（離線瓦片的 per-zoom bbox 由 maxBounds
# 推導，兩邊必須同步）——不在本檔重建座標，否則又會出現「maxBounds 比瓦片寬」的漂移
# （§2-7 的成因：舊 maxBounds 東界 123.6°E 超出舊瓦片東界 122°E → 右側 2.9° 無底圖）。
from tiles import (MAP_CENTER, MAP_ZOOM, MAP_MAX_BOUNDS, BLANK_TILE_NAME, OCEAN_CSS)
from taiwan_geo import FALLBACK_LAND  # §2-7c 陸地兜底層（範圍由 tiles 視野推導）

# ⚠️ 雨量點樣式的「怎麼畫」單一來源（§2-4a-follow）。“畫多大、什幀顏色”在
# `cwa.RAIN_LEVELS`（進 map.geo.json 的 properties.color/radius），本 dict 只管
# 形狀/描邊/填充等「怎麼畫」，外加圖例要跟著形狀走。兩邊都不得在 JS 或圖例裡再寫死 hex
# （舊版圖例硬編碼 #dc2626/#ea580c/#f59e0b 三份、跟 cwa.RAIN_LEVELS 完会漂移）。
# shape: circle（現行外觀）| ring（空心粗環）| pin（水滴 divIcon，形狀編碼不靠色相）
RAIN_STYLE = {
    "shape": "circle",
    "weight": 3,          # 描邊（halo）粗細 px——§2-4a-follow B3 定案：3px 白環，淺陸地/淡海都跳
    "stroke": "#fff",     # 描邊色
    "fill": 0.95,         # fillOpacity
    "hit_min": 14,        # 手機可點度： invisible 命中圈最小半徑 px（§2-4a-follow：先留，影響體驗再調）
    # 未超閾值測站的淡色底點（顏色/半徑在 cwa.RAIN_BELOW，這裡只管怎麼畫）：
    # 小、淡、白環 1px；命中圈也縮小——淡點有 400+ 個，命中圈太大會吃掉告警 polygon 的點擊
    "below_weight": 1,
    "below_fill": 0.45,
    "below_hit": 11,
    # 半徑隨縮放（2026-10-26 使用者改口：固定 px 在 z11 點還是一樣小、命中圈也一樣小、
    # 點不中）。兩個係數分開：**可見點溫和放大**（1.2/級）、**命中圈快速放大**（1.6/級）。
    # 理由：完全地理固定是 2.0/級 → z11 點變 4 倍大、1314 個淡點會變成一片灰碟蓋住底圖
    #（實測過、已改）；但命中圈要大才點得中。上限 max_radius/max_hit 收斂 z11。
    # base ＝ RAIN_LEVELS/RAIN_BELOW 的半徑（即 z8 的值）。
    "dot_zoom_factor": 1.2,
    "hit_zoom_factor": 1.6,
    "zoom_ref": MAP_ZOOM,     # z8 ＝ 設計基準
    "max_radius": 22,         # 可見點上限 px（半徑）
    "max_hit": 30,            # 命中圈上限 px（半徑）→ z11 直徑 60px，手機拇指夠用
}

# ⚠️ 兜底陸地層樣式的單一來源（§2-7c）。用**字面 hex** 而非 var(--land)：本檔已有的教訓
#   （RAIN_STYLE 註解）＝ Leaflet 把 color/fillColor 寫進 SVG 顯示屬性，`var()` 在部分
#   瀏覽器不生效。顏色取 OSM standard 陸地色系（#f2efe9）——瓦片本身不隨主題變色，
#   所以兜底陸地兩主題同色（與 §2-7a 海色同一理由）。
LAND_STYLE = {
    "fill": "#f2efe9",   # 陸地填色（OSM standard land 同色系）
    "edge": "#d6ccbc",   # 海岸線描邊（比填色暗一點，低縮放才讀得出輪廓）
    "weight": 1,         # 描邊粗細 px
}


def _rain_legend_item(color):
    """圖例小色塊的樣式：形狀要跟實際渲染一致（ring→空心、pin→三角）。"""
    sh = RAIN_STYLE["shape"]
    if sh == "ring":
        return (f'background:#fff;border:{max(2, RAIN_STYLE["weight"] + 1)}px solid {color};'
                f'border-radius:50%')
    if sh == "pin":
        return (f'background:{color};border-radius:50% 50% 50% 0%;'
                f'transform:rotate(-45deg);border:1px solid {RAIN_STYLE["stroke"]}')
    return f'background:{color};border-radius:50%'

# 地圖視野：MAP_CENTER [23.7,121.3]、MAP_ZOOM 8、MAP_MAX_BOUNDS [[20.7,118.3],[26.7,124.3]]
# ——皆由 tiles.py import（不在此定義；§2-7）。不變項：MAP_MAX_BOUNDS 中心恆等於 MAP_CENTER
#（Leaflet 1.9.4 setView 對 maxBounds clamp：視口寬於 bounds 經度跨度時會把整個視口對齊
#  bounds 中心；2026/9/16 實測舊 bounds 中心 120.05 曾導致開圖偏西 0.9°）。

THEME_VARS = """
:root{--red:#ef5350;--yellow:#ffb300;--green:#66bb6a;
--bg:#14181c;--card:#1d242c;--line:#2f3944;--ink:#e4e8ec;--muted:#98a3af;
--accent:#64b5f6;--chip-bg:#2a333e;--side-bg:#0f1317;--head-bg:#0c0f12;
--sea:@SEA@;  /* §2-7：缺瓦片處的容器底色＝OSM standard 海洋色（OSM 瓦片不隨主題變色→dark 同色）；
             值由 tiles.OCEAN_CSS 注入（下方 replace），不得在此寫死 hex——會與 tiles.OCEAN_RGB 漂移 */
color-scheme:dark;}
/* 與 site.py 主題變數同步（子集：本頁未用 risk-bg/table-head/ph-*）；
   site.py 改主題色時須一併更新此處（2026/9/16 曾遺漏淡黃舊版）。 */
:root[data-theme="light"]{--red:#c62828;--yellow:#ef8f00;--green:#2e7d32;
--bg:#f9f3eb;--card:#fcfaf7;--line:#d1b594;--ink:#3b2816;--muted:#76614c;
--accent:#a35200;--chip-bg:#f2e4d4;--side-bg:#f5eee5;--head-bg:#342214;
--sea:@SEA@;
color-scheme:light;}
"""
# 海色只定義一次（單一事實來源＝tiles.OCEAN_RGB → OCEAN_CSS）：上面兩個 @SEA@ 在此一次代換
THEME_VARS = THEME_VARS.replace("@SEA@", OCEAN_CSS)

MAP_CSS = THEME_VARS + """
*{box-sizing:border-box}
body.map-page{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Noto Sans TC","PingFang TC","Microsoft JhengHei","Hiragino Sans","Noto Sans JP","Yu Gothic","Meiryo",sans-serif;color:var(--ink);background:var(--bg);line-height:1.7;font-size:16px}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.muted{color:var(--muted)}
header.site{background:var(--head-bg);color:#fff;padding:8px 0;position:sticky;top:0;z-index:40}
.site-bar{max-width:none;margin:0;padding:2px 14px;display:flex;align-items:center;gap:10px}
.site-bar h1{font-size:1.05rem;margin:0;flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.backlink{color:#b0bec5;white-space:nowrap;flex:none}
.updated{color:#b0bec5;font-size:.78rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:none}
.map-wrap{display:grid;grid-template-columns:minmax(0,1fr) 340px;flex:1 1 auto;min-height:0}
/* isolation:isolate（2026/9/17）：把 Leaflet 內部 pane（z-index 100–1000）封進 #map 自己的
   堆疊上下文。否則 .leaflet-container 不形成堆疊上下文、pane 直接與 root 競爭，
   sticky header（z-40）與行動版 bottom sheet（z-50）會被地圖蓋住。 */
#map{isolation:isolate;min-height:320px;background:var(--sea)}  /* §2-7：海色底，缺瓦片處不再是紙色 */
/* 桌面鎖死視口：header＋地圖（彈性）＋footer 填滿一屏、頁面不捲動
   （取代舊的 height:calc(100vh - 49px) magic number） */
@media(min-width:768px){
html,body.map-page{height:100%;overflow:hidden}
body.map-page{display:flex;flex-direction:column}
}
.leaflet-container{background:var(--sea);font:inherit}
.map-panel{background:var(--card);border-left:1px solid var(--line);overflow-y:auto}
.panel-tab{display:none}
.panel-body{padding:14px 16px}
.map-updated{font-size:.85rem;color:var(--muted);margin:0 0 10px}
.map-warn{background:var(--chip-bg);border:1px solid var(--yellow);border-radius:8px;padding:8px 12px;margin:8px 0;font-size:.85rem}
.map-panel h3{font-size:.95rem;border-bottom:1px solid var(--line);padding-bottom:4px;margin:18px 0 8px}
.layer{display:flex;align-items:center;gap:8px;padding:5px 2px;font-size:.9rem;cursor:pointer}
.layer input{accent-color:var(--accent);width:16px;height:16px;margin:0}
.swatch{width:14px;height:14px;border-radius:3px;flex:none}
.swatch.round{border-radius:50%}
.rain-legend{margin:2px 0 6px 24px;font-size:.8rem;color:var(--muted);line-height:1.9}
.rain-legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}
.rain-pin{background:transparent;border:none}   /* pin 形狀的 divIcon：去掉 Leaflet 預設白框 */
.layer .cnt{margin-left:auto;color:var(--muted);font-size:.85rem}
.map-detail{font-size:.9rem}
.map-detail .dl{margin:8px 0}
.map-detail .dt{color:var(--muted);font-size:.8rem;margin-bottom:1px}
.map-detail .dd{white-space:pre-wrap;word-break:break-word}
.map-detail .dd-src{background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:.85rem}
.map-detail ul{list-style:none;padding:0;margin:4px 0}
.map-detail li{padding:3px 0}
.map-detail .type-head{display:flex;align-items:center;gap:8px;font-weight:700;font-size:1rem}
.map-noscript{padding:20px;font-size:.95rem}
.map-noscript ul{padding-left:18px}
footer.map-foot{background:var(--head-bg);color:#90a4ae;padding:8px 14px;font-size:.78rem}
/* 行動版（<768px）：右側欄改為 bottom sheet */
@media(max-width:767px){
.map-wrap{display:block;height:auto;flex:none}
#map{height:62vh;min-height:320px}
.map-panel{position:fixed;left:0;right:0;bottom:0;z-index:50;border-left:none;border-top:2px solid var(--line);
border-radius:14px 14px 0 0;max-height:70vh;transform:translateY(calc(100% - 46px));transition:transform .25s ease;box-shadow:0 -6px 24px rgba(0,0,0,.35)}
.map-panel.open{transform:translateY(0)}
.panel-tab{display:flex;align-items:center;gap:8px;width:100%;padding:11px 14px;background:none;border:none;
color:var(--ink);font:inherit;font-weight:700;cursor:pointer}
.panel-tab .updated{margin-left:auto;flex:0 1 auto;min-width:0;max-width:62%}
/* 2026/9/17：左側告警數 span 不可折行（舊版被右側「產生時間」長串壓到 min-content、
   一 CJK 字一行）；右側縮得動＋ellipsis */
.panel-tab>span:first-child{white-space:nowrap;flex:none}
#panel-close{display:inline-flex;background:none;border:none;color:var(--muted);font-size:1rem;cursor:pointer;padding:4px}
.panel-body{padding-bottom:24px}
}
"""


def _json_embed(obj):
    """JSON 嵌入 <script type="application/json">：轉義 </ 防止提前閉合。"""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def _events_for_counties(events, counties):
    """本 repo 與該告警影響縣市相關的事件（front matter counties 交集），最新 5 筆。"""
    hits = [e for e in events if any(c in counties for c in e.get("counties", []))]
    hits.sort(key=lambda e: e["mtime"], reverse=True)
    return [{"name": e["name"], "url": "/".join(e["url"]), "status": e["status"]} for e in hits[:5]]


def _noscript_html(lang, fc, root_prefix):
    """無 JS fallback：靜態告警清單＋回總覽（靜態 SVG 總覽在首頁）。"""
    parts = [f'<p>{t(lang, "map_noscript")}</p>']
    feats = fc.get("features", [])
    alerts = [f for f in feats if f["properties"].get("type") != "rain"]
    if alerts:
        lis = []
        for f in alerts:
            p = f["properties"]
            eff = f'{p["effective"]} → {p["expires"]}' if p.get("expires") else (p.get("effective") or "")
            counties = "、".join(p.get("counties", [])) or "—"
            lis.append(f'<li><b>{p["type_name"]}</b>（{eff}）：{counties} — {p.get("description", "")}</li>')
        parts.append(f'<ul>{"".join(lis)}</ul>')
    else:
        parts.append(f'<p>{t(lang, "map_none")}</p>')
    rain = [f for f in feats if f["properties"].get("type") == "rain"]
    rain_top = [f for f in rain if not f["properties"].get("below")]
    rain_below = [f for f in rain if f["properties"].get("below")]
    if rain_top:
        parts.append(f'<p><b>{t(lang, "map_noscript_rain")} {len(rain_top)} 站</b></p>')
        parts.append(
            "<ul>" + "".join(
                f'<li>{f["properties"]["name"]}（{f["properties"].get("county", "")}'
                f'{f["properties"].get("township", "")}）：'
                f'{t(lang, "map_rain_p1hr")} {f["properties"]["p1hr"]}mm ／ '
                f'{t(lang, "map_rain_p24hr")} {f["properties"]["p24hr"]}mm</li>'
                for f in rain_top[:10]) + "</ul>")
    if rain_below:
        # 淡色底點：JS 關了也不影響這段（noscript fallback 本来就沒有圖層開關）
        parts.append(f'<p>{t(lang, "map_layer_rain_below")} {len(rain_below)} 站</p>')
    parts.append(f'<p><a href="{root_prefix}index.html">← {t(lang, "back_home")}</a></p>')
    return '<div class="map-noscript">' + "".join(parts) + "</div>"


def build(OUT, fc, events, warnings=None):
    """產出 public/map/index.html（繁中）與 public/ja/map/index.html。

    fc：map.geo.json 內容（FeatureCollection）；events：load_events() 結果
    （提供「本 repo 該區域相關災情紀錄」連結）。
    """
    OUT = Path(OUT)
    for lang in LANGS:
        assets = "../assets/" if is_default(lang) else "../../assets/"
        base = "../"  # /map/ → 本語言根

        # 每筆 feature 附上 repo 相關事件連結（build 端計算，前端只渲染）；
        # 雨量站點用單值 county 欄。
        for f in fc.get("features", []):
            p = f["properties"]
            counties = p.get("counties") or ([p["county"]] if p.get("county") else [])
            p["repo_links"] = _events_for_counties(events, counties)

        counts = {slug: 0 for slug in TYPES}
        for f in fc.get("features", []):
            slug = f["properties"]["type"]
            counts[slug] = counts.get(slug, 0) + 1
        layers_html = "".join(
            f'<label class="layer"><input type="checkbox" data-type="{slug}" checked>'
            f'<span class="swatch" style="background:{color}"></span>{t(lang, f"map_layer_{slug}")}'
            f'<span class="cnt">{counts[slug]}</span></label>'
            for slug, (_zh_name, color) in TYPES.items())
            # 層名走 i18n（cbph.TYPES 只有中文名，/ja/ 地圖頁因此曾外洩中文層名，2026-10-26 修）
        rain_feats = [f for f in fc.get("features", []) if f["properties"].get("type") == "rain"]
        rain_top = [f for f in rain_feats if not f["properties"].get("below")]
        rain_below = [f for f in rain_feats if f["properties"].get("below")]
        # 圖例顏色＝cwa.RAIN_LEVELS（與點本身同一來源；RAIN_LEVELS 由上而下＝l3→l1）
        from cwa import RAIN_BELOW as _RB, RAIN_LEVELS as _RL
        lv_colors = [c for _m1, _m24, c, _r in _RL][:3]
        top_color = lv_colors[0] if lv_colors else "#e11d48"
        if rain_top:
            layers_html += (
                f'<label class="layer"><input type="checkbox" data-type="rain" checked>'
                f'<span class="swatch round" style="background:{top_color}"></span>'
                f'{t(lang, "map_layer_rain")}<span class="cnt">{len(rain_top)}</span></label>')
            items = []
            for lv_key, color in zip(("map_rain_l3", "map_rain_l2", "map_rain_l1"), lv_colors):
                items.append(f'<span><i style="{_rain_legend_item(color)}"></i>{t(lang, lv_key)}</span>')
            layers_html += ('<div class="rain-legend">' + "<br>".join(items) + '</div>')
        if rain_below:
            # 第二個開關：未超閾值的淡色底點（2026-10-26 使用者定案全部上圖；嫌亂可自行關掉）
            layers_html += (
                f'<label class="layer"><input type="checkbox" data-type="rain_below" checked>'
                f'<span class="swatch round" style="background:{_RB["color"]};'
                f'opacity:{RAIN_STYLE["below_fill"]:.2f};border:1px solid {RAIN_STYLE["stroke"]}">'
                f'</span>{t(lang, "map_layer_rain_below")}'
                f'<span class="cnt">{len(rain_below)}</span></label>')

        warn_html = ""
        if fc.get("warnings"):
            warn_html = ('<div class="map-warn">'
                         + "<br>".join(f'⚠️ {w}' for w in fc["warnings"])
                         + "</div>")

        labels = json.dumps({
            "official": t(lang, "map_official"),
            "effective": t(lang, "map_effective"),
            "county": t(lang, "map_county"),
            "town": t(lang, "map_town"),
            "desc": t(lang, "map_desc"),
            "cmam": t(lang, "map_cmam"),
            "cb_on": t(lang, "map_cb_on"),
            "cb_off": t(lang, "map_cb_off"),
            "repo": t(lang, "map_repo"),
            "repo_none": t(lang, "map_no_repo"),
            "src": t(lang, "map_src"),
            "rain_loc": t(lang, "map_rain_loc"),
            "rain_p1hr": t(lang, "map_rain_p1hr"),
            "rain_p24hr": t(lang, "map_rain_p24hr"),
            "rain_pday": t(lang, "map_rain_pday"),
            "rain_obs": t(lang, "map_rain_obs"),
            "rain_note": t(lang, "map_rain_note"),
        }, ensure_ascii=False)

        n = len([f for f in fc.get("features", []) if f["properties"].get("type") != "rain"])
        none_p = json.dumps('<p class="muted">' + t(lang, "map_none") + "</p>", ensure_ascii=False)
        rain_style = json.dumps(RAIN_STYLE, ensure_ascii=False)
        land_style = json.dumps(LAND_STYLE, ensure_ascii=False)
        # §2-7c：兜底陸地的 ring 從 `taiwan_geo.FALLBACK_LAND`（lon,lat）轉成 Leaflet 習慣的
        # [lat,lng]——座標順序只在此處定一次，不得在 JS 再維護一套。
        land_rings = json.dumps([[[lat, lon] for lon, lat in ring] for ring in FALLBACK_LAND])
        page = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t(lang, "map_title")}</title>
<script>/* 避免閃爍：先還原主題偏好再渲染 */(function(){{var t=null;try{{t=localStorage.getItem("wtf-theme")}}catch(e){{}}if(t!=="light"&&t!=="dark")t="dark";document.documentElement.setAttribute("data-theme",t);}})();</script>
<style>{MAP_CSS}</style>
<link rel="stylesheet" href="{assets}leaflet/leaflet.css">
</head>
<body class="map-page">
<header class="site">
<div class="site-bar">
<a class="backlink" href="{base}index.html">{t(lang, "back_home")}</a>
<h1>{t(lang, "map_title_short")}</h1>
<span class="updated">{t(lang, "map_updated", ts=fc.get("generated_at", "?"))}</span>
</div>
</header>
<div class="map-wrap">
<div id="map">
<noscript>{_noscript_html(lang, fc, base)}</noscript>
</div>
<aside class="map-panel" id="panel">
<button class="panel-tab" id="panel-tab" aria-expanded="false">
<span>⚠️ {t(lang, "map_alert_count", n=n)}</span>
<span class="updated">{t(lang, "map_updated", ts=fc.get("generated_at", "?"))}</span>
<span id="panel-close" role="button" aria-label="{t(lang, "map_close")}">✕</span>
</button>
<div class="panel-body">
<p class="map-updated">{t(lang, "map_updated", ts=fc.get("generated_at", "?"))}</p>
{warn_html}
<h3>{t(lang, "map_layers")}</h3>
{layers_html}
<h3>{t(lang, "map_detail_title")}</h3>
<div class="map-detail" id="detail"><p class="muted">{t(lang, "map_detail_hint")}</p></div>
</div>
</aside>
</div>
<footer class="map-foot">{t(lang, "map_source")}　·　{t(lang, "map_osm")}</footer>
<script id="map-data" type="application/json">{_json_embed(fc)}</script>
<script src="{assets}leaflet/leaflet.js"></script>
<script>
(function(){{
  var raw = document.getElementById("map-data");
  var detail = document.getElementById("detail");
  var panel = document.getElementById("panel");
  var mapEl = document.getElementById("map");
  if (!raw || typeof L === "undefined") return;
  var DATA = JSON.parse(raw.textContent);
  var LABELS = {labels};

  var map = L.map(mapEl, {{minZoom:{MAP_ZOOM}, maxZoom:11}});
  map.setView({json.dumps(MAP_CENTER)}, {MAP_ZOOM});
  map.setMaxBounds({json.dumps(MAP_MAX_BOUNDS)});

  // §2-7c 兜底陸地層：**獨立 pane、zIndex 低於 tilePane（CSS 為 200）**——瓦片在的處永遠蓋住它，
  // 只在瓦片缺口處露出。需要它的理由：errorTileUrl 那張佔位底是**全透明**的（§2-7a），
  // 海色靠容器背景；若沒這層，缺瓦片處會連陸地一併消失（包括台灣自己）。
  // 陆地範圍由 build 端從 tiles.zoom_bbox() 推導（taiwan_geo.FALLBACK_LAND）。
  var LAND_STYLE = {land_style};
  var LAND = {land_rings};
  var landPane = map.createPane("land");
  landPane.style.zIndex = 1;
  for (var li = 0; li < LAND.length; li++) {{
    L.polygon(LAND[li], {{pane: "land", interactive: false, stroke: true,
      weight: LAND_STYLE.weight, color: LAND_STYLE.edge,
      fillColor: LAND_STYLE.fill, fillOpacity: 1}}).addTo(map);
  }}

  L.tileLayer("{assets}tiles/{{z}}/{{x}}_{{y}}.png",
    {{minZoom:{MAP_ZOOM}, maxZoom:11, errorTileUrl:"{assets}tiles/{BLANK_TILE_NAME}",
      attribution:"© OpenStreetMap contributors"}}).addTo(map);

  var RAIN_STYLE = {rain_style};

  // 半徑/命中圈隨縮放（見 RAIN_STYLE 註解）：circleMarker 的 radius 是螢幕 px，
  // 不處理的話拉進两级點還是同樣大 → 命中圈也同樣小、點不中。
  var ZOOM_ITEMS = [];   // {{m: layer, base: 基準半徑, hit: 是否命中圈}}
  function dotRadius(base) {{
    var k = map.getZoom() - RAIN_STYLE.zoom_ref;
    return Math.min(Math.max(3, base) * Math.pow(RAIN_STYLE.dot_zoom_factor, k), RAIN_STYLE.max_radius);
  }}
  function hitRadius(base) {{
    var k = map.getZoom() - RAIN_STYLE.zoom_ref;
    return Math.min(Math.max(base, 6) * Math.pow(RAIN_STYLE.hit_zoom_factor, k), RAIN_STYLE.max_hit);
  }}

  function rainMarker(ll, p) {{
    // 顔色/半徑來自 build 端（超閾值＝cwa.RAIN_LEVELS、未超閾值＝cwa.RAIN_BELOW，
    // 皆寫進 properties.color/radius）；形狀/描邊來自 RAIN_STYLE（同一來源）
    var r = dotRadius(p.radius || 6);
    if (p.below) {{   // 淡色底點：小、低透明度、細白環（不與超閾值點搶視線）
      return L.circleMarker(ll, {{radius: r, color: RAIN_STYLE.stroke, weight: RAIN_STYLE.below_weight,
        fillColor: p.color, fillOpacity: RAIN_STYLE.below_fill}});
    }}
    if (RAIN_STYLE.shape === "pin") {{
      var s = Math.round(r * 2.6);
      var html = '<svg width="' + s + '" height="' + s + '" viewBox="0 0 24 24">'
        + '<path d="M12 1.6C7.4 1.6 3.6 5.4 3.6 10c0 6.2 8.4 12.4 8.4 12.4s8.4-6.2 8.4-12.4'
        + 'C20.4 5.4 16.6 1.6 12 1.6z" fill="' + p.color + '" stroke="' + RAIN_STYLE.stroke
        + '" stroke-width="' + RAIN_STYLE.weight + '"/>'
        + '<circle cx="12" cy="9.8" r="2.6" fill="#fff"/></svg>';
      return L.marker(ll, {{icon: L.divIcon({{className: "rain-pin", html: html,
        iconSize: [s, s], iconAnchor: [Math.round(s / 2), Math.round(s * 0.78)]}})}});
    }}
    if (RAIN_STYLE.shape === "ring") {{
      return L.circleMarker(ll, {{radius: r, color: p.color,
        weight: Math.max(2, Math.round(r * 0.55)), fillColor: RAIN_STYLE.stroke,
        fillOpacity: 1, opacity: 1}});
    }}
    return L.circleMarker(ll, {{radius: r, color: RAIN_STYLE.stroke, weight: RAIN_STYLE.weight,
      fillColor: p.color, fillOpacity: RAIN_STYLE.fill}});
  }}

  var byType = {{}};
  DATA.features.forEach(function(f){{
    (byType[f.properties.type] = byType[f.properties.type] || []).push(f);
  }});
  var layerByType = {{}};

  function pointPolys(list) {{
    var out = [];
    list.forEach(function(f){{
      var p = f.properties;
      var ll = [f.geometry.coordinates[1], f.geometry.coordinates[0]];
      var mk = rainMarker(ll, p);
      ZOOM_ITEMS.push({{ m: mk, base: p.radius || 6, hit: false }});
      var tip = p.name + " " + (p.township || "") + "　" + LABELS.rain_p1hr + " " + p.p1hr + "mm";
      mk.bindTooltip(tip, {{sticky: true}});
      mk.on("click", function(){{ showRainDetail(p); }});
      out.push(mk);
      // 手機可點度：小點的命中區就是那個半徑 → 加一個透明大命中圈（同 layer、一起開關）
      var hitBase = Math.max(p.below ? RAIN_STYLE.below_hit : RAIN_STYLE.hit_min, (p.radius || 6) + 4);
      var hit = L.circleMarker(ll, {{radius: hitRadius(hitBase),
        stroke: false, fillColor: "#000", fillOpacity: 0.01, interactive: true}});
      ZOOM_ITEMS.push({{ m: hit, base: hitBase, hit: true }});
      hit.bindTooltip(tip, {{sticky: true}});
      hit.on("click", function(){{ showRainDetail(p); }});
      out.push(hit);
    }});
    return out;
  }}

  function polyPolys(list) {{
    var out = [];
    list.forEach(function(f){{
      var p = f.properties;
      var tip = p.type_name + (p.effective ? " " + p.effective + " → " + (p.expires || "") : "");
      var counties = (p.counties || []).join("、");
      if (counties) tip += "（" + counties + "）";
      (f.geometry.coordinates || []).forEach(function(ring){{
        var pg = L.polygon(ring.map(function(c){{ return [c[1], c[0]]; }}),
          {{color: p.color, weight: 2, fillColor: p.color, fillOpacity: 0.35}});
        pg.bindTooltip(tip, {{sticky: true}});
        pg.on("click", function(){{ showDetail(p); }});
        out.push(pg);
      }});
    }});
    return out;
  }}

  // 疊放順序是刻意的（不是 byType 鍵序）：淡色底點最下 → 告警 polygon → 超閾值點最上。
  // 否則 400+ 個淡點的透明命中圈會蓋住告警 polygon，點 polygon 變成點測站（設計定案）。
  var rainAll = byType["rain"] || [];
  var rainBelow = rainAll.filter(function(f){{ return f.properties.below; }});
  var rainTop = rainAll.filter(function(f){{ return !f.properties.below; }});
  if (rainBelow.length) layerByType.rain_below = L.layerGroup(pointPolys(rainBelow)).addTo(map);
  Object.keys(byType).forEach(function(type){{
    if (type === "rain") return;
    layerByType[type] = L.layerGroup(polyPolys(byType[type])).addTo(map);
  }});
  if (rainTop.length) layerByType.rain = L.layerGroup(pointPolys(rainTop)).addTo(map);

  // 半徑隨縮放：circleMarker 的 radius 是螢幕 px，不更新的話拉進兩級後點與命中圈都還是
  // 同樣小（2026-10-26 使用者實測反應「地圖拉進後圈還是一樣小、點擊不方便」）。
  // 只重算視野內（含 15% 邊界）的；關掉的層不從 ZOOM_ITEMS 移除，但 setRadius 對
  // 未加入地圖的 layer 是 no-op（Leaflet Circle._updatePath 會查 this._map）。
  function rescaleRain() {{
    var b = map.getBounds().pad(0.15);
    for (var i = 0; i < ZOOM_ITEMS.length; i++) {{
      var it = ZOOM_ITEMS[i];
      if (!b.contains(it.m.getLatLng())) continue;
      it.m.setRadius(it.hit ? hitRadius(it.base) : dotRadius(it.base));
    }}
  }}
  map.on("zoomend", rescaleRain);

  document.querySelectorAll(".layer input").forEach(function(cb){{
    cb.addEventListener("change", function(){{
      var lg = layerByType[cb.dataset.type];
      if (!lg) return;
      if (cb.checked) lg.addTo(map); else map.removeLayer(lg);
    }});
  }});

  function row(label, value){{
    var d = document.createElement("div"); d.className = "dl";
    var k = document.createElement("div"); k.className = "dt"; k.textContent = label;
    var v = document.createElement("div"); v.className = "dd"; v.textContent = value;
    d.appendChild(k); d.appendChild(v); detail.appendChild(d);
  }}
  function showDetail(p){{
    detail.innerHTML = "";
    var h = document.createElement("div"); h.className = "type-head";
    var sw = document.createElement("span"); sw.className = "swatch"; sw.style.background = p.color;
    var name = document.createElement("span"); name.textContent = p.type_name;
    h.appendChild(sw); h.appendChild(name); detail.appendChild(h);
    row(LABELS.official, p.official_id || "—");
    row(LABELS.effective, (p.effective || "—") + " → " + (p.expires || "—"));
    row(LABELS.county, (p.counties || []).join("、") || "—");
    if ((p.towns || []).length) row(LABELS.town, p.towns.join("、"));
    row(LABELS.desc, p.description || "—");
    row(LABELS.cmam, (p.cmam_text || "—") + (p.cb_enabled ? "（" + LABELS.cb_on + "）" : "（" + LABELS.cb_off + "）"));
    addRepo(p);
    if (p.source_url){{
      var s = document.createElement("p");
      var a2 = document.createElement("a");
      a2.href = p.source_url; a2.target = "_blank"; a2.rel = "noopener";
      a2.textContent = "↗ " + LABELS.src;
      s.appendChild(a2); detail.appendChild(s);
    }}
    panel.classList.add("open");
  }}
  function addRepo(p){{
    var repo = document.createElement("div"); repo.className = "dl";
    var rk = document.createElement("div"); rk.className = "dt"; rk.textContent = LABELS.repo;
    repo.appendChild(rk);
    var links = p.repo_links || [];
    if (links.length){{
      var ul = document.createElement("ul");
      links.forEach(function(e){{
        var li = document.createElement("li");
        var a = document.createElement("a"); a.href = "../" + e.url; a.textContent = e.name;
        li.appendChild(a); ul.appendChild(li);
      }});
      repo.appendChild(ul);
    }} else {{
      var none = document.createElement("div"); none.className = "dd"; none.textContent = LABELS.repo_none;
      repo.appendChild(none);
    }}
    detail.appendChild(repo);
  }}
  function showRainDetail(p){{
    detail.innerHTML = "";
    var h = document.createElement("div"); h.className = "type-head";
    var sw = document.createElement("span"); sw.className = "swatch round"; sw.style.background = p.color;
    var name = document.createElement("span"); name.textContent = p.name;
    h.appendChild(sw); h.appendChild(name); detail.appendChild(h);
    row(LABELS.rain_loc, [p.county, p.township].filter(Boolean).join(""));
    row(LABELS.rain_p1hr, p.p1hr + " mm");
    row(LABELS.rain_p24hr, p.p24hr + " mm");
    row(LABELS.rain_pday, p.pday + " mm");
    row(LABELS.rain_obs, p.obs || "—");
    addRepo(p);
    var note = document.createElement("p");
    note.className = "muted"; note.style.cssText = "font-size:.8rem;margin:10px 0 0";
    note.textContent = LABELS.rain_note;
    detail.appendChild(note);
    panel.classList.add("open");
  }}

  // 行動版 bottom sheet 開關
  var tab = document.getElementById("panel-tab");
  function toggle(){{
    var open = panel.classList.toggle("open");
    tab.setAttribute("aria-expanded", open ? "true" : "false");
  }}
  if (tab) tab.addEventListener("click", function(ev){{
    if (ev.target.id === "panel-close" || ev.target === tab) toggle();
  }});
  if (!DATA.features.length){{
    detail.innerHTML = {none_p};
  }}
}})();
</script>
</body>
</html>"""
        out_dir = OUT / ("map" if is_default(lang) else f"{lang}/map")
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(page, encoding="utf-8")
    return OUT

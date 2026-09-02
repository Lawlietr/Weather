"""災防告警地圖 /map/ 獨立頁（TODO §2 執行順序 3）。

設計（2026/9/1 定案）：
- Leaflet 只在此頁載入（自託 build/static/leaflet/、無 CDN）；首頁維持零 JS
  ＋現有靜態 SVG 軌跡圖，只加「查看地圖」入口。
- 離線自駕（硬需求）：瓦片為 build 時抓取之本地檔（見 tiles.py），
  Leaflet 指向 public/assets/tiles/ → 前端零外部請求。
- 佈局：全幅地圖（預設全台視角 z8）＋右側欄（行動版 bottom sheet）：
  點擊詳情卡＋圖例＋圖層開關＋「產生時間」（快照標示必顯示）。
- 資料：build/map.geo.json（cbph 災防告警快照，build 時由 cbph.py 先寫）；
  此模組只渲染、不新增抓取。顏色/等級閾值邏輯在 build 端，前端只負責渲染。
- 無 JS fallback：靜態告警清單＋回總覽連結（靜態 SVG 總覽在首頁）。
- 瓦片署名義務：頁尾必顯示「© OpenStreetMap contributors」（瓦片來源 OSM 德國社群 server tile.openstreetmap.de，2026/9/2 起；官方 server 對本機 IP 假 200 封鎖，見 tiles.py 註）。
"""
import json
from pathlib import Path

from i18n import t, LANGS, is_default
from cbph import TYPES  # slug → (中文名, 配色)，與 cbph UI 一致

# 預設全台視角中心（本島＋離島折衷）
MAP_CENTER = [23.8, 120.95]
MAP_ZOOM = 8
# 瓦片範圍稍寬於抓取 bbox，允許用戶稍微平移
MAP_MAX_BOUNDS = [[21.2, 117.4], [27.0, 122.7]]

THEME_VARS = """
:root{--red:#ef5350;--yellow:#ffb300;--green:#66bb6a;
--bg:#14181c;--card:#1d242c;--line:#2f3944;--ink:#e4e8ec;--muted:#98a3af;
--accent:#64b5f6;--chip-bg:#2a333e;--side-bg:#0f1317;--head-bg:#0c0f12;
color-scheme:dark;}
:root[data-theme="light"]{--red:#c62828;--yellow:#ef8f00;--green:#2e7d32;
--bg:#fff6dd;--card:#fffdf4;--line:#e6d7ae;--ink:#33280f;--muted:#7d6c48;
--accent:#a05e00;--chip-bg:#f5e8c3;--side-bg:#fbf1d4;--head-bg:#263238;
color-scheme:light;}
"""

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
.map-wrap{display:grid;grid-template-columns:minmax(0,1fr) 340px;height:calc(100vh - 49px)}
#map{min-height:320px;background:var(--bg)}
.leaflet-container{background:var(--bg);font:inherit}
.map-panel{background:var(--card);border-left:1px solid var(--line);overflow-y:auto}
.panel-tab{display:none}
.panel-body{padding:14px 16px}
.map-updated{font-size:.85rem;color:var(--muted);margin:0 0 10px}
.map-warn{background:var(--chip-bg);border:1px solid var(--yellow);border-radius:8px;padding:8px 12px;margin:8px 0;font-size:.85rem}
.map-panel h3{font-size:.95rem;border-bottom:1px solid var(--line);padding-bottom:4px;margin:18px 0 8px}
.layer{display:flex;align-items:center;gap:8px;padding:5px 2px;font-size:.9rem;cursor:pointer}
.layer input{accent-color:var(--accent);width:16px;height:16px;margin:0}
.swatch{width:14px;height:14px;border-radius:3px;flex:none}
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
.map-wrap{display:block;height:auto}
#map{height:62vh;min-height:320px}
.map-panel{position:fixed;left:0;right:0;bottom:0;z-index:50;border-left:none;border-top:2px solid var(--line);
border-radius:14px 14px 0 0;max-height:70vh;transform:translateY(calc(100% - 46px));transition:transform .25s ease;box-shadow:0 -6px 24px rgba(0,0,0,.35)}
.map-panel.open{transform:translateY(0)}
.panel-tab{display:flex;align-items:center;gap:8px;width:100%;padding:11px 14px;background:none;border:none;
color:var(--ink);font:inherit;font-weight:700;cursor:pointer}
.panel-tab .updated{margin-left:auto}
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
    if feats:
        lis = []
        for f in feats:
            p = f["properties"]
            eff = f'{p["effective"]} → {p["expires"]}' if p.get("expires") else (p.get("effective") or "")
            counties = "、".join(p.get("counties", [])) or "—"
            lis.append(f'<li><b>{p["type_name"]}</b>（{eff}）：{counties} — {p.get("description", "")}</li>')
        parts.append(f'<ul>{"".join(lis)}</ul>')
    else:
        parts.append(f'<p>{t(lang, "map_none")}</p>')
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

        # 每筆 feature 附上 repo 相關事件連結（build 端計算，前端只渲染）
        for f in fc.get("features", []):
            f["properties"]["repo_links"] = _events_for_counties(
                events, f["properties"].get("counties", []))

        counts = {slug: 0 for slug in TYPES}
        for f in fc.get("features", []):
            slug = f["properties"]["type"]
            counts[slug] = counts.get(slug, 0) + 1
        layers_html = "".join(
            f'<label class="layer"><input type="checkbox" data-type="{slug}" checked>'
            f'<span class="swatch" style="background:{color}"></span>{name}'
            f'<span class="cnt">{counts[slug]}</span></label>'
            for slug, (name, color) in TYPES.items())

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
        }, ensure_ascii=False)

        n = len(fc.get("features", []))
        none_p = json.dumps('<p class="muted">' + t(lang, "map_none") + "</p>", ensure_ascii=False)
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
  L.tileLayer("{assets}tiles/{{z}}/{{x}}_{{y}}.png",
    {{minZoom:{MAP_ZOOM}, maxZoom:11, attribution:"© OpenStreetMap contributors"}}).addTo(map);

  var byType = {{}};
  DATA.features.forEach(function(f){{
    (byType[f.properties.type] = byType[f.properties.type] || []).push(f);
  }});
  var layerByType = {{}};
  Object.keys(byType).forEach(function(type){{
    var polys = [];
    byType[type].forEach(function(f){{
      var p = f.properties;
      var tip = p.type_name + (p.effective ? " " + p.effective + " → " + (p.expires || "") : "");
      var counties = (p.counties || []).join("、");
      if (counties) tip += "（" + counties + "）";
      (f.geometry.coordinates || []).forEach(function(ring){{
        var pg = L.polygon(ring.map(function(c){{ return [c[1], c[0]]; }}),
          {{color: p.color, weight: 2, fillColor: p.color, fillOpacity: 0.35}});
        pg.bindTooltip(tip, {{sticky: true}});
        pg.on("click", function(){{ showDetail(p); }});
        polys.push(pg);
      }});
    }});
    var lg = L.layerGroup(polys).addTo(map);
    layerByType[type] = lg;
  }});

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
    if (p.source_url){{
      var s = document.createElement("p");
      var a2 = document.createElement("a");
      a2.href = p.source_url; a2.target = "_blank"; a2.rel = "noopener";
      a2.textContent = "↗ " + LABELS.src;
      s.appendChild(a2); detail.appendChild(s);
    }}
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

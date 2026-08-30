"""CWA Open Data API：build 時本機抓取並渲染「氣象總覽」區塊。

原則：
- API Key 只從環境變數 CWA_API_KEY 讀取，絕不寫入任何輸出檔案。
- 金鑰不支援 CORS，前端無法直接呼叫，所有資料都是 build 時寫死的靜態 HTML。
- 失敗降級：build/cwa_cache.json（本地、gitignore）。每個來源獨立成功/失敗，
  失敗的來源若快取有舊值則用舊值並標註「舊資料」。
- 「抓不到」與「沒有」視覺區分：抓不到顯示警示 + 快取時間，不會跟「無颱風」混淆。

回傳結構（2026/8/26 實測）：
- W-C0034-005: records.TropicalCyclones.TropicalCyclone[]，Fix 欄位為
  MovingSpeed/MovingDirection，風圈 Circle15ms/Circle25ms = {Radius: str}。
- W-C0034-001: records.info[]（CAP），parameter = [{valueName,value}]，
  description.typhoon-info 為 section 列表（含「警報類別」END/ACTIVE）。
- W-C0033-002: records.record[]，validTime = {startTime,endTime}（無時區，+08:00），
  contents.content = {contentLanguage,contentText}，
  hazard[].info.affectedAreas.location[].locationName。
- O-A0002-001: records.Station[]，GeoInfo.TownName/CountyName，值為字串。
"""
import json
import os
import re
import subprocess
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import i18n
from i18n import t
from taiwan_geo import ISLANDS

TZ_TW = timezone(timedelta(hours=8))

BASE = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"
CACHE = Path(__file__).resolve().parent / "cwa_cache.json"
TIMEOUT = 60
SOURCES = ("typhoons", "marine_alert", "reports", "rain")


# ---------------------------------------------------------------- 抓取

def _get_json(data_id, **params):
    key = os.getenv("CWA_API_KEY")
    if not key:
        raise RuntimeError("CWA_API_KEY 未設定（請寫入 ~/.zshrc 或專案 .env）")
    q = {"Authorization": key, "format": "JSON"}
    q.update(params)
    url = f"{BASE}/{data_id}?" + urllib.parse.urlencode(q)
    # 用 curl 而非 urllib：Python 3.14 的 OpenSSL 對 CWA 憑證鏈會
    # CERTIFICATE_VERIFY_FAILED（Missing Subject Key Identifier）。
    p = subprocess.run(["curl", "-s", "--max-time", str(TIMEOUT), url],
                       capture_output=True, text=True, timeout=TIMEOUT + 10)
    if p.returncode != 0:
        raise RuntimeError(f"{data_id}: curl 失敗（{p.returncode}）")
    data = json.loads(p.stdout)
    if data.get("success") == "false":
        raise RuntimeError(f"{data_id}: success=false（檢查 API Key 或 Data ID）")
    return data


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fetch_typhoons():
    """W-C0034-005 熱帶氣旋完整軌跡 + 預報。"""
    d = _get_json("W-C0034-005")
    tc = (d.get("records", {}).get("TropicalCyclones") or {})
    lst = tc.get("TropicalCyclone", []) if isinstance(tc, dict) else tc
    out = []
    for c in lst:
        out.append({
            "name": c.get("CwaTyphoonName", ""),
            "intl": c.get("TyphoonName", ""),
            "no": c.get("CwaTdNo", ""),
            "year": c.get("Year", ""),
            "analysis": (c.get("AnalysisData") or {}).get("Fix", []),
            "forecast": (c.get("ForecastData") or {}).get("Fix", []),
        })
    return out


def _cap_param_dict(info):
    """CAP parameter 列表 → dict。"""
    out = {}
    for p in info.get("parameter", []):
        out[p.get("valueName", "")] = p.get("value", "")
    return out


def fetch_marine_alert():
    """W-C0034-001 海上颱風警報（CAP）。回傳最新一筆（可能是解除）。"""
    d = _get_json("W-C0034-001")
    out = []
    for i in d.get("records", {}).get("info", []):
        param = _cap_param_dict(i)
        ti = (i.get("description") or {}).get("typhoon-info", [])
        if isinstance(ti, dict):
            ti = [ti]
        meta = {}
        for block in ti if isinstance(ti, list) else []:
            for s in block.get("section", []):
                meta[s.get("title", "")] = s.get("value")
        # 實際警報全文位於 description.section（命名與位置、強度與半徑…等 8 個 section）
        content_sections = (i.get("description") or {}).get("section", [])
        if isinstance(content_sections, dict):
            content_sections = [content_sections]
        content = "\n".join(
            f"【{s.get('title', '')}】{s.get('value', '')}"
            for s in content_sections
            if s.get("title") and s.get("value")
        )
        out.append({
            "title": param.get("alert_title", i.get("headline", "")),
            "severity": i.get("severity", ""),
            "report_no": meta.get("警報報數", ""),
            "category": meta.get("警報類別", ""),
            "typhoon_name": meta.get("颱風名稱", ""),
            "content": content,
            "effective": i.get("effective", ""),
        })
    return out


def fetch_reports():
    """W-C0033-002 災害性天氣特報（純文字＋影響區域）。"""
    d = _get_json("W-C0033-002")
    out = []
    for r in d.get("records", {}).get("record", []):
        info = r.get("datasetInfo", {})
        vt = info.get("validTime", {})
        if isinstance(vt, dict):
            valid = f'{vt.get("startTime", "")} ~ {vt.get("endTime", "")}'
        else:
            valid = vt
        content = (r.get("contents") or {}).get("content", {})
        if isinstance(content, dict):
            content = content.get("contentText", "")
        elif isinstance(content, list):
            content = content[0].get("contentText", "") if content else ""
        haz = (r.get("hazardConditions") or {}).get("hazards", {})
        hz = haz.get("hazard", []) if isinstance(haz, dict) else haz
        if isinstance(hz, dict):
            hz = [hz]
        phen, areas = [], []
        for h in hz:
            ih = h.get("info", h)
            phen.append(ih.get("phenomena", ""))
            for loc in (ih.get("affectedAreas") or {}).get("location", []):
                nm = loc.get("locationName", "")
                if nm and nm not in areas:
                    areas.append(nm)
        out.append({
            "name": info.get("datasetDescription", ""),
            "valid": valid,
            "issue": info.get("issueTime", ""),
            "content": content,
            "phenomena": [p for p in phen if p],
            "areas": areas,
        })
    return out


def fetch_rain():
    """O-A0002-001 雨量站。Now.Precipitation = 本日 0 時至目前累計（非 1 小時）。"""
    d = _get_json("O-A0002-001")
    out = []
    for s in d.get("records", {}).get("Station", []):
        el = s.get("RainfallElement", {})
        now = _num((el.get("Now") or {}).get("Precipitation")) or 0.0
        p1 = _num((el.get("Past1hr") or {}).get("Precipitation")) or 0.0
        p24 = _num((el.get("Past24hr") or {}).get("Precipitation")) or 0.0
        if now <= 0 and p24 <= 0:
            continue
        geo = s.get("GeoInfo", {})
        out.append({
            "name": s.get("StationName", ""),
            "county": geo.get("CountyName", ""),
            "township": geo.get("TownName", ""),
            "obs": (s.get("ObsTime") or {}).get("DateTime", ""),
            "now": now,
            "p1hr": p1,
            "p24hr": p24,
        })
    out.sort(key=lambda x: x["now"], reverse=True)
    return out[:10]


def load_snapshot():
    """回傳 (data, errors, stale, mode)。
    mode: live（全部成功）/ partial（部分成功）/ cache（全敗用快取）/ none（全敗無快取）
    """
    fetchers = {"typhoons": fetch_typhoons, "marine_alert": fetch_marine_alert,
                "reports": fetch_reports, "rain": fetch_rain}
    data, errors = {}, {}
    for name, fn in fetchers.items():
        try:
            data[name] = fn()
        except Exception as e:
            errors[name] = str(e)
    cached = None
    try:
        cached = json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception:
        pass
    stale = {}
    if errors and cached:
        for k in list(errors):
            v = cached.get("data", {}).get(k)
            if v is not None:
                data[k] = v
                stale[k] = cached.get("saved_at", "")
    now = datetime.now().strftime("%Y/%m/%d %H:%M")
    if not errors:
        mode = "live"
    elif data:
        mode = "partial"
    elif cached:
        data, errors, mode = cached.get("data", {}), {}, "cache"
    else:
        mode = "none"
    if data:
        try:
            CACHE.write_text(json.dumps({"saved_at": now, "data": data}, ensure_ascii=False),
                             encoding="utf-8")
        except Exception:
            pass
    return data, errors, stale, mode


# ---------------------------------------------------------------- 工具

def _t(s):
    """ISO / 'YYYY-MM-DD HH:MM:SS' → 2026/8/26 18:00（無時區視為 +08:00）。"""
    if not s:
        return "—"
    s = s.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is not None:
            dt = dt.astimezone(TZ_TW)  # 統一轉 +08:00 顯示
        return dt.strftime("%Y/%m/%d %H:%M")
    except ValueError:
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})", s)
        if m:
            return f"{m.group(1)}/{int(m.group(2))}/{int(m.group(3))} {m.group(4)}:{m.group(5)}"
        return s


def _t_range(s):
    """時間範圍 'A ~ B' → 'A ~ B'（兩端各自格式化）；單個時間原樣走 _t()。"""
    if not s:
        return "—"
    if "~" in s:
        parts = [p.strip() for p in s.split("~") if p.strip()]
        return " ~ ".join(_t(p) for p in parts) or "—"
    return _t(s)


def _ts_parse(s):
    """ISO / 'YYYY-MM-DD HH:MM:SS' → tz-aware datetime（無時區視為 +08:00）；解析失敗回 None。"""
    if not s:
        return None
    s = s.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})", s)
        if not m:
            return None
        dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ_TW)
    return dt.astimezone(TZ_TW)


def _classify(wind_ms):
    """回傳 i18n key；由呼叫端以 t(lang, key) 翻譯。"""
    if wind_ms is None:
        return None
    if wind_ms >= 51.0:
        return "ty_cat_super"
    if wind_ms >= 41.5:
        return "ty_cat_strong"
    if wind_ms >= 32.7:
        return "ty_cat_vstrong"
    if wind_ms >= 24.5:
        return "ty_cat_mod"
    if wind_ms >= 13.9:
        return "ty_cat_weak"
    return "ty_cat_td"


def _pos(fix):
    lat, lon = _num(fix.get("CoordinateLatitude")), _num(fix.get("CoordinateLongitude"))
    if lat is None or lon is None:
        return "—"
    return f"{lat:.1f}°N {lon:.1f}°E"


def _radius(fix, key):
    v = fix.get(key)
    if isinstance(v, dict):
        return _num(v.get("Radius"))
    return _num(v)


# ---------------------------------------------------------------- SVG 軌跡圖

LON0, LON1, LAT0, LAT1 = 115, 130, 16, 31
W, H = 540, 480
PX_PER_KM = (W / (LON1 - LON0)) / 101.0  # 約 23°N 處 1° 經度 ≈ 101 km


def _px(lon, lat):
    x = (lon - LON0) / (LON1 - LON0) * W
    y = (LAT1 - lat) / (LAT1 - LAT0) * H
    return x, y


# 台灣輪廓：本島＋澎湖／金門／馬祖／蘭嶼／綠島，各自獨立多邊形。
# 來源見 build/taiwan_geo.py（Natural Earth 1:10m + g0v/twgeojson 馬祖）。
CITIES = [("city_taipei", 121.56, 25.03), ("city_taichung", 120.67, 24.15),
          ("city_kaoxiong", 120.30, 22.62), ("city_hualien", 121.61, 23.99),
          ("city_taitung", 121.15, 22.75)]


def typhoon_svg(lang, cyclone):
    """單一氣旋：分析軌跡（實線）+ 預報（虛線）+ 最新位置 15 m/s 風圈。"""
    a, f = cyclone["analysis"], cyclone["forecast"]
    grid = []
    lon = LON0 + 2
    while lon < LON1:
        x, _ = _px(lon, LAT0)
        grid.append(f'<line x1="{x:.0f}" y1="0" x2="{x:.0f}" y2="{H}" stroke="var(--line)" stroke-width="0.5" opacity="0.5"/>')
        lon += 2
    lat = LAT0 + 2
    while lat < LAT1:
        _, y = _px(LON0, lat)
        grid.append(f'<line x1="0" y1="{y:.0f}" x2="{W}" y2="{y:.0f}" stroke="var(--line)" stroke-width="0.5" opacity="0.5"/>')
        lat += 2
    # 本島與各離島各自獨立 polygon；每島可能含多個 ring
    tai = "".join(
        f'<polygon points="{" ".join(f"{_px(lo, la)[0]:.0f},{_px(lo, la)[1]:.0f}" for lo, la in ring)}" '
        f'fill="var(--chip-bg)" stroke="var(--muted)" stroke-width="1.5"/>'
        for _, rings in ISLANDS for ring in rings if len(ring) >= 3)
    cities = "".join(
        f'<circle cx="{_px(lo, la)[0]:.0f}" cy="{_px(lo, la)[1]:.0f}" r="2" fill="var(--muted)"/>'
        f'<text x="{_px(lo, la)[0] + 5:.0f}" y="{_px(lo, la)[1] + 3:.0f}" font-size="10" fill="var(--muted)">{t(lang, n)}</text>'
        for n, lo, la in CITIES)
    parts = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{cyclone["name"]}">{"".join(grid)}'
             f"{tai}{cities}"]
    # 分析軌跡（實線）
    an_pts = []
    for fix in a:
        lo, la = _num(fix.get("CoordinateLongitude")), _num(fix.get("CoordinateLatitude"))
        if lo is None or la is None:
            continue
        an_pts.append((fix, lo, la))
    if an_pts:
        pts = " ".join(f"{_px(lo, la)[0]:.0f},{_px(lo, la)[1]:.0f}" for _, lo, la in an_pts)
        parts.append(f'<polyline points="{pts}" fill="none" stroke="var(--accent)" stroke-width="2"/>')
        for fix, lo, la in an_pts:
            x, y = _px(lo, la)
            parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="3" fill="var(--accent)"/>')
        # 最新位置：15 m/s 風圈 + 紅點 + 名稱
        lf = an_pts[-1][0]
        x, y = _px(an_pts[-1][1], an_pts[-1][2])
        r15 = _radius(lf, "Circle15ms")
        if r15:
            parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r15 * PX_PER_KM:.0f}" '
                         f'fill="none" stroke="var(--red)" stroke-width="1" stroke-dasharray="4 3" opacity="0.7"/>')
        parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="5" fill="var(--red)"/>')
        parts.append(f'<text x="{x + 8:.0f}" y="{y - 8:.0f}" font-size="12" font-weight="bold" fill="var(--red)">'
                     f'{t(lang, "latest_tag", name=cyclone["name"])}</text>')
    # 預報（虛線，接在最新分析點後）
    fc_pts = []
    for fix in f:
        lo, la = _num(fix.get("CoordinateLongitude")), _num(fix.get("CoordinateLatitude"))
        if lo is None or la is None:
            continue
        fc_pts.append((fix, lo, la))
    if fc_pts and an_pts:
        sx, sy = _px(an_pts[-1][1], an_pts[-1][2])
        pts = f"{sx:.0f},{sy:.0f} " + " ".join(f"{_px(lo, la)[0]:.0f},{_px(lo, la)[1]:.0f}" for _, lo, la in fc_pts)
        parts.append(f'<polyline points="{pts}" fill="none" stroke="var(--yellow)" stroke-width="1.5" stroke-dasharray="6 4"/>')
        for fix, lo, la in fc_pts:
            x, y = _px(lo, la)
            parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="3" fill="none" stroke="var(--yellow)" stroke-width="1.5"/>')
    parts.append(
        f'<g font-size="10" fill="var(--muted)">'
        f'<line x1="12" y1="{H-30}" x2="32" y2="{H-30}" stroke="var(--accent)" stroke-width="2"/><text x="36" y="{H-27}">{t(lang, "legend_analysis")}</text>'
        f'<line x1="96" y1="{H-30}" x2="116" y2="{H-30}" stroke="var(--yellow)" stroke-width="1.5" stroke-dasharray="5 3"/><text x="120" y="{H-27}">{t(lang, "legend_forecast")}</text>'
        f'<circle cx="186" cy="{H-30}" r="4" fill="none" stroke="var(--red)" stroke-dasharray="3 2"/><text x="195" y="{H-27}">{t(lang, "legend_wind")}</text>'
        f'</g></svg>')
    return "".join(parts)


# ---------------------------------------------------------------- 目前風險狀態

def current_risk_level(lang, data, stale, mode):
    """由 CWA 現況資料推導「目前風險狀態」（首頁頂部狀態列用）。

    與事件的歷史分級（severity）完全獨立：severity 是事件最終量級（固定），
    這裡只回答「現在有沒有危險」。依據：
    - 生效中熱帶氣旋（有分析資料）：max wind >= 24.5 m/s → red，否則 yellow
    - 海上颱風警報（未解除）→ red
    - 災害性天氣特報（未解除）：沿用 _sev_color 分級（紅/黃），綠色級別不計入
    雨量觀測值不計入：那是「過去累計」，不是當前危險信號。

    回傳 (level, items)：level ∈ red/yellow/green/unknown（mode=none → unknown）；
    items = [(level, i18n_key, params), ...]（green 不進 items）。
    stale 供呼叫端標註舊資料。
    """
    if mode == "none":
        return "unknown", []
    items = []
    d = data or {}
    for c in d.get("typhoons", []):
        fixes = c.get("analysis") or []
        if not fixes:
            continue
        wind = _num((fixes[-1] or {}).get("MaxWindSpeed"))
        level = "red" if (wind is not None and wind >= 24.5) else "yellow"
        name = c.get("name", "") or "（未命名）"
        if c.get("intl"):
            name += f"（{c['intl']}）"
        cat = _classify(wind)
        items.append((level, "risk_typhoon",
                      {"name": name, "cat": f"（強度：{t(lang, cat)}）" if cat else ""}))
    for m in d.get("marine_alert", []):
        if not m.get("title") or "解除" in m["title"] or m.get("category") == "END":
            continue
        items.append(("red", "risk_marine", {"title": m["title"]}))
    for r in d.get("reports", []):
        if not r.get("name") or "解除" in r["name"]:
            continue
        cls = _sev_color(r["name"], r["phenomena"])
        if cls == "sev-green":
            continue
        valid = _t_range(r.get("valid", ""))
        items.append((cls[4:], "risk_report", {"name": r["name"], "valid": valid}))
    level = "red" if any(l == "red" for l, _, _ in items) else ("yellow" if items else "green")
    return level, items


# ---------------------------------------------------------------- 區塊渲染

def render_typhoon_card(lang, typhoons, stale_at=None):
    """颱風卡永遠顯示：無資料時顯示「無活動中熱帶氣旋」。"""
    tag = f'　<span class="muted">{t(lang, "stale_tag", ts=stale_at)}</span>' if stale_at else ""
    if not typhoons:
        return f"""
<div class="card cwa-card">
<h3>{t(lang, "typhoon_title")}　<span class="meta">CWA W-C0034-005{tag}</span></h3>
<p>{t(lang, "typhoon_none")}</p>
</div>"""
    blocks = []
    for c in typhoons:
        a, f = c["analysis"], c["forecast"]
        if not a:
            continue
        last = a[-1]
        wind = _num(last.get("MaxWindSpeed"))
        gust = _num(last.get("MaxGustSpeed"))
        pressure = last.get("Pressure", "—")
        move = t(lang, "moving", dir=last.get("MovingDirection", "—"),
                 speed=last.get("MovingSpeed", "—"))
        if f:
            rows = []
            for fx in f:
                h = _num(fx.get("ForecastHour")) or 0
                try:
                    tstr = (datetime.fromisoformat(fx["InitialTime"]) + timedelta(hours=h)).strftime("%m/%d %H:%M")
                except (KeyError, ValueError):
                    tstr = f'+{int(h)}h'
                ws = _num(fx.get("MaxWindSpeed"))
                rows.append(f'<tr><td>{tstr}</td><td>{_pos(fx)}</td>'
                            f'<td>{f"{ws:.1f}" if ws is not None else "—"} m/s</td><td>{fx.get("Pressure", "—")} hPa</td></tr>')
            rows = "".join(rows)
        else:
            rows = f'<tr><td colspan="4" class="muted">{t(lang, "no_fc")}</td></tr>'
        no = t(lang, "typhoon_no", year=c.get("year", ""), no=c.get("no", "")) if c.get("no") else ""
        no = f'　<span class="muted">{no}</span>' if no else ""
        cat = t(lang, _classify(wind)) if _classify(wind) else "—"
        blocks.append(f"""
<div class="typhoon-row">
<div class="map">{typhoon_svg(lang, c)}</div>
<div class="typhoon-info">
<h4 style="margin:0 0 6px">{c['name']}{no}　<span class="muted">{c.get('intl','')}</span></h4>
<p style="margin:4px 0">{t(lang, "obs_line", ts=_t(last.get('DateTime')), pos=_pos(last), cat=cat, w=f"{wind:.1f}" if wind is not None else "—", g=gust if gust is not None else '—', p=pressure, move=move)}</p>
<h4 style="margin:10px 0 4px">{t(lang, "future_fc")}</h4>
<table><tr><th>{t(lang, "th_time")}</th><th>{t(lang, "th_pos")}</th><th>{t(lang, "th_wind")}</th><th>{t(lang, "th_pressure")}</th></tr>{rows}</table>
</div>
</div>""")
    return f"""
<div class="card cwa-card">
<h3>{t(lang, "typhoon_title")}　<span class="meta">CWA W-C0034-005{tag}</span></h3>
{"".join(blocks) or f'<p class="muted">{t(lang, "typhoon_nodata")}</p>'}
</div>"""


def _sev_color(name, phenomena):
    text = name + "".join(phenomena)
    if any(k in text for k in ("豪雨", "極端", "強豪雨")):
        return "sev-red"
    if any(k in text for k in ("大雨", "強風")):
        return "sev-yellow"
    return "sev-green"


# 已解除（解除/END）的警報/特報超過此時數後不再渲染：
# CWA 的 CAP 端點只保留「最新一筆」（含解除報），何時被覆蓋由 CWA 端決定，
# 我們自行設 TTL 淘汰，避免舊解除報永久佔位。
LIFTED_TTL_HOURS = 48


def render_alert_card(lang, marine, reports, stale_at=None, now=None):
    """警報/特報卡：皆無 → 整張卡隱藏（回傳空字串）。

    海上颱風警報與災害性天氣特報混排、按時間倒序（最新在最上）；
    已解除（解除/END）項目置底、灰色 badge，超過 LIFTED_TTL_HOURS 則整筆移除。
    """
    now = now or datetime.now(TZ_TW)
    items = []
    for m in marine:
        if not m.get("title"):
            continue
        lifted = "解除" in m["title"] or m.get("category") == "END"
        ts = _ts_parse(m.get("effective"))
        if lifted and ts is not None and (now - ts) > timedelta(hours=LIFTED_TTL_HOURS):
            continue
        cls = "sev-grey" if lifted else "sev-red"
        note = t(lang, "lifted_note") if lifted else ""
        body = ""
        if m.get("content"):
            body = f'<details><summary class="muted">{t(lang, "view_full")}</summary><pre class="report-text">{m["content"].strip()}</pre></details>'
        items.append((lifted, ts, f'<div class="alert-item"><span class="badge {cls}">{t(lang, "marine_badge")}</span>　'
                     f'<b>{m["title"]}</b>'
                     + (t(lang, "report_no", n=m["report_no"]) if m.get("report_no") else "")
                     + (f'｜{t(lang, "typhoon_label", n=m["typhoon_name"])}' if m.get("typhoon_name") else "")
                     + note
                     + f'<div class="meta">{t(lang, "effective", ts=_t(m.get("effective")))}</div>'
                     + body + '</div>'))
    for r in reports:
        if not r.get("name"):
            continue
        lifted = "解除" in r["name"]
        ts = _ts_parse(r.get("issue"))
        if lifted and ts is not None and (now - ts) > timedelta(hours=LIFTED_TTL_HOURS):
            continue
        cls = "sev-grey" if lifted else _sev_color(r["name"], r["phenomena"])
        note = t(lang, "lifted_note") if lifted else ""
        phen = "、".join(r["phenomena"])
        body = ""
        if r.get("content"):
            body = f'<details><summary class="muted">{t(lang, "view_full")}</summary><pre class="report-text">{r["content"].strip()}</pre></details>'
        items.append((lifted, ts, f'<div class="alert-item"><span class="badge {cls}">{r["name"]}</span>　'
                     f'<b>{phen}</b>{note}　'
                     f'<span class="meta">{t(lang, "issued", ts=_t(r["issue"]))}｜{t(lang, "valid", ts=_t_range(r["valid"]))}</span>'
                     + (f'<div>{t(lang, "affected", a="、".join(r["areas"]))}</div>' if r["areas"] else "") + body + '</div>'))
    # 未解除在前、已解除置底；同組內按時間倒序（ts 無法解析者視為最新，保顯示）
    def _k(it):
        return (it[1] or now).timestamp()
    items = sorted((i for i in items if not i[0]), key=_k, reverse=True) + \
            sorted((i for i in items if i[0]), key=_k, reverse=True)
    items = [html for _, _, html in items]
    if not items:
        return ""
    tag = f'　<span class="muted">{t(lang, "stale_tag", ts=stale_at)}</span>' if stale_at else ""
    return f"""
<div class="card cwa-card">
<h3>{t(lang, "alert_title")}　<span class="meta">CWA W-C0034-001 / W-C0033-002{tag}</span></h3>
{"".join(items)}
</div>"""


def render_rain_card(lang, rain, has_active_event, stale_at=None):
    """雨量站 TOP 10：有 active 事件時展開；無事件時收合。
    ⚠️ Now = 本日 0 時至目前累計（非 1 小時雨量）。"""
    if not rain:
        return ""
    tag = f'　<span class="muted">{t(lang, "stale_tag", ts=stale_at)}</span>' if stale_at else ""
    rows = "".join(
        f'<tr><td>{s["name"]}</td><td>{s["county"]}{s["township"]}</td><td>{s["now"]:,.0f}</td>'
        f'<td>{s["p1hr"]:,.0f}</td><td>{s["p24hr"]:,.0f}</td></tr>'
        for s in rain)
    obs = rain[0].get("obs", "")
    table = f"""<table><tr><th>{t(lang, "rain_th_station")}</th><th>{t(lang, "rain_th_area")}</th><th>{t(lang, "rain_th_today")}</th><th>{t(lang, "rain_th_1h")}</th><th>{t(lang, "rain_th_24h")}</th></tr>{rows}</table>
<p class="meta">{t(lang, "rain_note", ts=_t(obs))}</p>"""
    inner = table if has_active_event else f'<details><summary>{t(lang, "rain_details")}</summary>{table}</details>'
    return f"""
<div class="card cwa-card">
<h3>{t(lang, "rain_title")}{tag}</h3>
{inner}
</div>"""


def cwa_section_html(lang, data, errors, stale, mode, has_active_event):
    """回傳「氣象總覽」section 的 HTML（mode=none 時只有警示）。"""
    note = f'<p class="meta">{t(lang, "cwa_data_note")}</p>' if t(lang, "cwa_data_note") else ""
    if mode == "none":
        why = next(iter(errors.values()), "未知錯誤") if errors else "未知錯誤"
        return f"""
<section class="cwa">
<h2>{t(lang, "cwa_title")}</h2>
<div class="card cwa-card cwa-fail">{t(lang, "cwa_fail")}<br>
<span class="meta">{t(lang, "cwa_fail_fix", why=why)}</span></div>
</section>"""
    parts = []
    if mode == "partial":
        bad = "、".join(sorted(errors))
        parts.append(f'<div class="cwa-warn">{t(lang, "cwa_warn_partial", bad=bad)}</div>')
    elif mode == "cache":
        parts.append(f'<div class="cwa-warn">{t(lang, "cwa_warn_cache")}</div>')
    parts.append(render_typhoon_card(lang, data.get("typhoons", []), stale.get("typhoons")))
    parts.append(render_alert_card(lang, data.get("marine_alert", []), data.get("reports", []),
                                   stale.get("marine_alert", stale.get("reports"))))
    parts.append(render_rain_card(lang, data.get("rain", []), has_active_event, stale.get("rain")))
    return f"""
<section class="cwa">
<h2>{t(lang, "cwa_title")}</h2>
{note}
{"".join(p for p in parts if p)}
</section>"""

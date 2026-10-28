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
import math
import os
import re
import subprocess
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import i18n
from i18n import t
import dgpa
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


# /map/ 雨量站觀測層三級閾值（2026/9/16 定案、真實資料校準）：
# 條件為「p1hr ≥ 閾值 **或** p24hr ≥ 閾值」，同時滿足多級時取最高級。
# 校準例（2026/9/16 14:50，淡雨日）：L3 0 站 / L2 1 站 / L1 13 站——淡雨日
# 點數可控，颱風期間高自然上升。詳見 design/map.md（執行順序 4a）。
# 2026-10-26 §2-4a-follow 定案（B3）：色相走「紫 → 洋紅 → 玫紅」（越嚴重越紅，保
# 「紅=危險」語意），刻意避開 OSM 底圖幹道/高速公路的橘（色相約 20–40°）與 §2-7 後的
# 海面淡藍 #aad3df；半徑 11/8/5 → 17/12/9（現行 r5 在 z8 只有 4px、且與橘色路線糊在
# 一起，使用者反映「太小＋混淆」）。半徑固定 px、不隨縮放變（2026-10-26 決策：先固定）。
RAIN_LEVELS = (
    # (p1hr 閾值 mm, p24hr 閾值 mm, 顏色, 半徑 px)
    # ⚠️ 三級色要同時避開 cbph 四個告警圖層的官方色（cbph.TYPES：cells #f59e0b、
    # tywinds #ef4444、mountainstorms #7c3aed、largesurfs #0ea5e9）——點會畫在 polygon 上面，
    # 同色就分不清誰是誰。2026-10-26 第一版用 #7c3aed 做 L1，實測發现舆 mountainstorms
    # 完全同色（已改）；L3 也不用 #ef4444 相近的亮紅，改用较深的玫紅 #be123c。
    (50.0, 250.0, "#be123c", 17),   # 玫紅（越嚴重越紅，保「紅=危險」語意）
    (25.0, 100.0, "#c026d3", 12),   # 洋紅
    (10.0, 50.0, "#4338ca", 9),     # 深靛藍（舆 mountainstorms 的 #7c3aed 拉開色相+明度）
)

# 未超閾值測站的「淡色底點」（2026-10-26 使用者定案：全部上圖）。理由：CWA 全網絡 1315 站，
# 淡雨日超閾值站為 0 → 舊版地圖上一個點都沒有，使用者無法分辨「查過但沒超標」與「壞了」。
# 中性石板灰（不與級別色相抢意）、r 4px、低 fillOpacity → 整體讀作「測站網絡」而非資料點。
# ⚠️ 1315 點＝2630 個 SVG path（含命中圈）——命中圈半徑較小且在疊放最下層，
# 免得吃掉告警 polygon 的點擊；效能與開關見 design/map.md。
RAIN_BELOW = {"color": "#5b6b7b", "radius": 4}


def fetch_rain_points():
    """O-A0002-001 超閾值雨量站 → /map/ 觀測層 Point features（map_page.py 渲染）。

    - 座標必須取 `GeoInfo.Coordinates` 中 **WGS84** 一筆（另有 TWD67，與 OSM
      瓦片座標系不符、會偏移）。
    - 超閾值者按 `RAIN_LEVELS` 上色；未超閾值者以 `RAIN_BELOW` 淡色底點上圖並標
      `properties.below = True`（前端分開圖層/開關，並把他們疊在告警 polygon 之下）。
      與 fetch_rain()（首頁 top 10）各自獨立抓取
      （每次 build 多一次 HTTP、可接受；故障互相獨立，單層失敗不影響他層）。
    - obs 統一轉「YYYY/M/D HH:MM」（UTC+8）。
    - 回傳依 p1hr 降序（noscript fallback 取前 10 即雨量最大者）。
    """
    d = _get_json("O-A0002-001")
    out = []
    for s in d.get("records", {}).get("Station", []):
        el = s.get("RainfallElement", {})
        p1 = _num((el.get("Past1hr") or {}).get("Precipitation")) or 0.0
        p24 = _num((el.get("Past24hr") or {}).get("Precipitation")) or 0.0
        pday = _num((el.get("Now") or {}).get("Precipitation")) or 0.0
        lvl = next(
            ((color, radius) for m1, m24, color, radius in RAIN_LEVELS
             if p1 >= m1 or p24 >= m24),
            None)
        below = lvl is None
        color, radius = lvl if lvl else (RAIN_BELOW["color"], RAIN_BELOW["radius"])
        geo = s.get("GeoInfo", {})
        lat = lon = None
        for c in geo.get("Coordinates", []):
            if c.get("CoordinateName") == "WGS84":
                lat, lon = _num(c.get("StationLatitude")), _num(c.get("StationLongitude"))
                break
        if lat is None or lon is None:
            continue
        obs_raw = (s.get("ObsTime") or {}).get("DateTime", "")
        try:
            obs = datetime.fromisoformat(obs_raw).astimezone(TZ_TW).strftime("%Y/%-m/%-d %H:%M")
        except (TypeError, ValueError):
            obs = obs_raw
        out.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "type": "rain",
                "type_name": "雨量站",
                "color": color,
                "radius": radius,
                "name": s.get("StationName", ""),
                "county": geo.get("CountyName", ""),
                "township": geo.get("TownName", ""),
                "p1hr": p1, "p24hr": p24, "pday": pday,
                "below": below,
                "obs": obs,
                "source": "CWA O-A0002-001",
            },
        })
    # 超閾值在前（noscript fallback 取前 10 即雨量最大者），未超閾值排在後面
    out.sort(key=lambda f: (bool(f["properties"].get("below")), -f["properties"]["p1hr"]))
    return out


# ------------------------------------ 地圖用颱風軌跡／風圈（design/map.md §2-4b，2026-10-27）

# 顏色＝單一事實來源：寫進 map.geo.json 的 properties.color，前端（map_page.py）只管
# 「怎麼畫」（粗細/虛線/填色，見 map_page.TYPHOON_STYLE），兩邊都不再寫第二份 hex。
# ⚠️ 必須避開同一張圖上已有的色：cbph 四色（cells #f59e0b／tywinds #ef4444／
#   mountainstorms #7c3aed／largesurfs #0ea5e9）、雨量三級（#be123c／#c026d3／#4338ca）
#   與淡點 #5b6b7b——同色就分不清誰是誰（§2-4a-follow 的教訓）。
# 地圖画布兩主題都是亮的（海＝tiles.OCEAN_CSS #aad3df、陸＝LAND_STYLE #f2efe9），
# 所以用**深色**線條；且 Leaflet 把 color 寫進 SVG 顯示屬性 → 不得使用 var(--xxx)。
TYPHOON_COLORS = {
    "track_obs": "#1f2937",    # 觀測軌跡（實線）——中性近黑，讀作「走過的路」
    "track_fc": "#b45309",     # 預報軌跡（虛線）——暗琥珀；與 cells 的 #f59e0b 靠明度＋虛線拉開
    "wind15": "#b91c1c",       # 15 m/s 暴風圈（環）——與 tywinds polygon（#ef4444 實心填充）不同形同明度
    "r70": "#475569",          # 70% 暴風半徑（環）——石板灰，不與任何層搶色相
    "center_obs": "#b91c1c",   # 最新分析點（與其風圈同色系）
    "center_fc": "#b45309",    # 預報點（與其軌跡同色系）
    "fix_obs": "#1f2937",      # 過往分析點
}

# 風圈環的取樣數（象限半徑線性插值後沿方位角取樣）。風圈 ≤ 500 km，32 點已夠圓。
RING_STEPS = 32
_QUAD_AZ = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SW": 225, "W": 270, "NW": 315}


def _circles(fix, key):
    """Circle15ms/Circle25ms → (平均半徑 km or None, {象限: 半徑 km})。

    實測（2026-10-27 W-C0034-005）：**分析** Fix 的風圈帶 `QuadrantRadii.Radius[]`
    （dir＝NE/SE/SW/NW，四值常不相等，故風圈不是正圓）；**預報** Fix 只有單值 `Radius`；
    熱帶性低氣壓階段（未達 15 m/s）整組缺 → 回 (None, {})，呼叫端據此跳過該環。
    """
    d = fix.get(key)
    if not isinstance(d, dict):
        return None, {}
    base = _num(d.get("Radius"))
    quads = {}
    for r in ((d.get("QuadrantRadii") or {}).get("Radius") or []):
        if not isinstance(r, dict):   # CWA 欄位形態不穩（曾整欄回字串/None）→ 跳過不炸 build
            continue
        v = _num(r.get("value"))
        if v is not None and r.get("dir"):
            quads[r["dir"]] = v
    if base is None and quads:
        base = round(sum(quads.values()) / len(quads))
    return base, quads


def _radius_at(quads, az):
    """象限半徑 → 方位角 az（度，0=北、順時針）的半徑：沿圓周線性插值；無資料回 None。"""
    pts = sorted((a, quads[d]) for d, a in _QUAD_AZ.items() if d in quads)
    if not pts:
        return None
    if len(pts) == 1:
        return pts[0][1]
    n = len(pts)
    for i in range(n):
        a0, r0 = pts[i]
        a1, r1 = pts[(i + 1) % n]
        span = (a1 - a0) % 360
        d = (az - a0) % 360
        if d <= span:
            return r0 + (r1 - r0) * (d / span)
    return pts[0][1]


def _wind_ring(lon, lat, radius_km, quads=None, steps=RING_STEPS):
    """中心＋半徑 km（或象限半徑 dict）→ GeoJSON 閉合環 `[[lon,lat],...]`。

    等圓柱近似：1° 緯度 ≈ 110.574 km、1° 經度 ≈ 111.320·cos(lat)。本專案風圈 ≤ 500 km，
    誤差遠小於資料本身的不確定性，不值得為它引入投影庫依賴（且 build 端零外部依賴是原則）。
    """
    if not quads and not radius_km:
        return []
    dlat = 1.0 / 110.574
    dlon = 1.0 / (111.320 * max(0.2, math.cos(math.radians(lat))))
    ring = []
    for i in range(steps):
        az = 360.0 * i / steps
        r = _radius_at(quads, az) if quads else radius_km
        if r is None:
            return []
        a = math.radians(az)
        ring.append([round(lon + r * math.sin(a) * dlon, 4), round(lat + r * math.cos(a) * dlat, 4)])
    ring.append(ring[0])
    return ring


def _fix_props(fix, is_fc):
    """單個 Fix（分析或預報）→ 詳情卡用的欄位（數值在 build 端算好，前端只渲染）。"""
    move_pred = ""
    for mp in (fix.get("MovingPrediction") or []):
        if not isinstance(mp, dict):   # 同 _circles：CWA 多語欄位形態不穩 → 跳過不炸
            continue
        if mp.get("lang", "").startswith("zh"):
            move_pred = mp.get("value", "")
            break
    r15, q15 = _circles(fix, "Circle15ms")
    r25, _q25 = _circles(fix, "Circle25ms")
    out = {
        "time": _t(fix.get("DateTime") if not is_fc else fix.get("InitialTime")),
        "fc_hour": _num(fix.get("ForecastHour")) if is_fc else None,
        "wind": _num(fix.get("MaxWindSpeed")),
        "gust": _num(fix.get("MaxGustSpeed")),
        "pressure": _num(fix.get("Pressure")),
        "move_speed": _num(fix.get("MovingSpeed")),
        "move_dir": fix.get("MovingDirection") or "",
        "move_pred": move_pred,
        "r15": r15,
        "r25": r25,
        "r70": _num(fix.get("Radius70PercentProbability")),  # ⚠️ 實測為公里半徑，非百分比
        "cat": _classify(_num(fix.get("MaxWindSpeed"))) or "",
    }
    if q15:
        g = lambda v: ("%g" % v) if v is not None else "—"
        out["r15_quads"] = "NE {}／SE {}／SW {}／NW {} km".format(
            g(q15.get("NE")), g(q15.get("SE")), g(q15.get("SW")), g(q15.get("NW")))
    return out


def typhoon_map_features(typhoons):
    """活動氣旋（W-C0034-005）→ /map/ 圖元清單（design/map.md 執行順序 4b，2026-10-27）。

    每個氣旋產四種幾何，全部 `properties.type = "typhoon"`（前端一個開關控整個氣旋層），
    以 `properties.kind` 分別繪製方式：

      track_obs   LineString  分析軌跡（實線）
      fix_obs     Point       過往分析點（最新點除外）
      center_obs  Point       最新分析點（＋其風圈）
      wind_obs    Polygon     最新分析點的 15 m/s 暴風圈（有象限資料→非正圓）
      track_fc    LineString  預報軌跡（虛線，從最新分析點接出）
      center_fc   Point       每個預報點（+6h…+120h，可點、詳情卡含該點數值）
      wind_fc     Polygon     最遠預報點的 15 m/s 暴風圈
      radius70    Polygon     最遠預報點的 70% 暴風半徑（AGENTS 的「可能影響台灣」判準就是它）

    風圈刻意只畫兩處（最新分析＋最遠預報）：9 個預報點各画一組會糊成一團、無法讀；
    中間點的半徑數值放進 properties，點下去就看得到。`latest: True` 標出放大的中心點。
    空清單＝目前無活動氣旋（前端圖層空，維持「空＝查過」原則；抓取失敗由 site.py 記 warning）。
    """
    feats = []
    for c in typhoons or []:
        an = [f for f in (c.get("analysis") or [])
              if _num(f.get("CoordinateLongitude")) is not None
              and _num(f.get("CoordinateLatitude")) is not None]
        fc = [f for f in (c.get("forecast") or [])
              if _num(f.get("CoordinateLongitude")) is not None
              and _num(f.get("CoordinateLatitude")) is not None]
        an.sort(key=lambda f: f.get("DateTime") or "")
        fc.sort(key=lambda f: _num(f.get("ForecastHour")) or 0)
        if not an and not fc:
            continue
        base = {
            "type": "typhoon",
            # type_name 用作詳情卡標題與 tooltip（CWA 資料不翻譯 → 各語言同為中文原文，
            # 與 site.py 的 cwa_data_note 同一原則）；編號一律 CWA `CwaTdNo`（AGENTS 規範）
            "type_name": "{}（{} 號）".format(c.get("name") or c.get("intl") or "?",
                                              c.get("no") or "—"),
            "name": c.get("name") or "",
            "intl": c.get("intl") or "",
            "no": c.get("no") or "",
            "year": c.get("year") or "",
            "n_obs": len(an),
            "n_fc": len(fc),
            "source": "CWA W-C0034-005",
        }
        pt = lambda f: [_num(f.get("CoordinateLongitude")), _num(f.get("CoordinateLatitude"))]
        add = lambda geom, kind, color, extra=None: feats.append({
            "type": "Feature",
            "geometry": geom,
            "properties": dict(base, kind=kind, color=color, **(extra or {})),
        })

        # ── 觀測軌跡（實線）＋過往點
        if len(an) >= 2:
            add({"type": "LineString", "coordinates": [pt(f) for f in an]},
                "track_obs", TYPHOON_COLORS["track_obs"],
                {"obs_from": _t(an[0].get("DateTime")), "obs_to": _t(an[-1].get("DateTime"))})
        for f in an[:-1]:
            add({"type": "Point", "coordinates": pt(f)}, "fix_obs", TYPHOON_COLORS["fix_obs"],
                _fix_props(f, False))

        # ── 最新分析點＋其 15 m/s 風圈（象限非正圓）
        latest = None
        if an:
            latest = an[-1]
            r15, q15 = _circles(latest, "Circle15ms")
            add({"type": "Point", "coordinates": pt(latest)}, "center_obs",
                TYPHOON_COLORS["center_obs"], dict(_fix_props(latest, False), latest=True))
            ring = _wind_ring(*pt(latest), r15, q15)
            if ring:
                add({"type": "Polygon", "coordinates": [ring]}, "wind_obs",
                    TYPHOON_COLORS["wind15"], _fix_props(latest, False))

        # ── 預報軌跡（虛線，從最新分析點接出）＋各預報點
        if fc:
            line = [pt(latest)] if latest else []
            line += [pt(f) for f in fc]
            if len(line) >= 2:
                add({"type": "LineString", "coordinates": line}, "track_fc", TYPHOON_COLORS["track_fc"],
                    {"fc_from": _t(fc[0].get("InitialTime")),
                     "fc_hours": "{}–{}h".format(fc[0].get("ForecastHour", ""),
                                                 fc[-1].get("ForecastHour", ""))})
            for f in fc:
                add({"type": "Point", "coordinates": pt(f)}, "center_fc", TYPHOON_COLORS["center_fc"],
                    _fix_props(f, True))
            # 最遠預報點：風圈＋70% 暴風半徑（數值取自該點，非平均）
            far = fc[-1]
            r15f, _qf = _circles(far, "Circle15ms")
            ring = _wind_ring(*pt(far), r15f)
            if ring:
                add({"type": "Polygon", "coordinates": [ring]}, "wind_fc",
                    TYPHOON_COLORS["wind15"], dict(_fix_props(far, True), latest=True))
            # ⚠️ 欄位名叫 `Radius70PercentProbability`，但實測是**公里半徑**不是百分比（煙花
            # +72h: r15=200 km / R70P=210；+120h: r15=220 / R70P=410——機率圓必然大於現行暴風圈）。
            r70 = _num(far.get("Radius70PercentProbability"))
            ring70 = _wind_ring(*pt(far), r70)
            if ring70:
                add({"type": "Polygon", "coordinates": [ring70]}, "radius70",
                    TYPHOON_COLORS["r70"], dict(_fix_props(far, True), latest=True))
    return feats


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



# 「解除」判定：CWA 的 W-C0033-002 只有「大雨特報」這種名稱，**解除與否寫在內文**
# （例：「由於降雨趨於緩和…故解除大雨特報。」），且解除報**不附 hazardConditions**
# （phenomena 空）。2026-10-25 03:25 那筆就是名稱無「解除」但內文明載解除，
# 舊碼只查名稱 → 把解除當生效，風險列被推成黃/紅。
LIFT_RE = re.compile(r"解除[^\n。]{0,12}(?:特報|警報)")


def is_lifted_report(r):
    """特報是否已解除。名稱含「解除」，或（phenomena 為空且內文寫明解除…特報/警報）。
    要求 phenomena 為空是必要的：生效中的特報一定有 hazard/phenomena（2026-10-25 實測：
    陸上強風特報有 phenomena=['陸上強風']，解除的大雨特報 phenomena=[]）。"""
    if "解除" in (r.get("name") or ""):
        return True
    return not r.get("phenomena") and bool(LIFT_RE.search(r.get("content") or ""))


def alert_typhoon_names(m):
    """從海上颱風警報（CAP）一筆記錄抽出它指的是哪個颱風。
    實測（2026-10-24 20:30 解除報）：parameter/typhoon-info 的「颱風名稱」欄是空的，
    但 description 的「命名與位置」內文寫「輕度颱風 薔琵（國際命名 CHAMPI）」→ 從內文補。"""
    names = set()
    n = (m.get("typhoon_name") or "").strip()
    if n:
        names.add(n)
    for mm in re.finditer(r"([\u4e00-\u9fff]{2,4})（國際命名", m.get("content") or ""):
        names.add(mm.group(1))
    return names


def typhoon_alert_state(c, marine):
    """這個熱帶氣旋目前與「颱風警報」的關係：active / lifted / none。

    - active：有**未解除**的海上（或陸上）颱風警報指名它
    - lifted：只有「解除颱風警報／END」那筆指名它（警報已解除，但 CWA 仍持續發布定位）
    - none：從沒為它發過警報（例如外海僅有分析資料的煙花）
    注意：CWA 的 W-C0034-001 只留「最新一筆」CAP，所以 lifted 的判斷依據就是那筆 END；
    若同時有 active 筆（多颱風）则以 active 為準。
    """
    name = (c.get("name") or "").strip()
    if not name:
        return "none"
    state = "none"
    for m in marine or []:
        if not m.get("title"):
            continue
        if name not in alert_typhoon_names(m) and name not in (m.get("title") or ""):
            continue
        if "解除" in (m.get("title") or "") or m.get("category") == "END":
            state = "lifted" if state == "none" else state
        else:
            return "active"
    return state


# ---------------------------------------------------------------- 目前風險狀態

def current_risk_level(lang, data, stale, mode):
    """由 CWA 現況資料推導「目前風險狀態」（首頁頂部狀態列用）。

    與事件的歷史分級（severity）完全獨立：severity 是事件最終量級（固定），
    這裡只回答「現在有沒有危險」。依据：
    - 生效中熱帶氣旋（**僅計入警報未解除的**，見 typhoon_alert_state）：
      max wind >= 24.5 m/s → red，否則 yellow
      （過時氣旋依 TYPHOON_STALE_HOURS 淘汰，與首頁颱風卡同規則，避免已消散氣旋推高狀態列）
    - 海上颱風警報（未解除）→ red
    - 災害性天氣特報（未解除，見 is_lifted_report）：沿用 _sev_color 分級（紅/黃），綠色級別不計入
    雨量觀測值不計入：那是「過去累計」，不是當前危險信號。

    回傳 (level, items)：level ∈ red/yellow/green/neutral/unknown（mode=none → unknown）；
    items = [(level, i18n_key, params), ...]。無生效中項目時：
    - 有已解除（且未超過 LIFTED_TTL_HOURS）的警報/特報 → neutral，附最近解除紀錄；
    - 連解除紀錄都無 → green（risk_none）。
    stale 供呼叫端標註舊資料。
    """
    if mode == "none":
        return "unknown", []
    items = []
    lifted_recent = []  # 已解除且未過 TTL 的警報/特報（供中性狀態列註記）
    d = data or {}
    now = datetime.now(TZ_TW)
    for c in filter_typhoon_stale(d.get("typhoons", []), d.get("marine_alert", []), now=now):
        fixes = c.get("analysis") or []
        if not fixes:
            continue
        # 只有「警報生效中」的氣旋才是危險信號。CWA 對已解除警報的氣旋（薔琵 25日08時
        # 仍在定位）與純外海追蹤的氣旋（煙花，從未發警報）都持續給分析資料，
        # 但那不是危險信號——舊碼把兩支都算進去，造成解警後風險列仍顯示「生效中」。
        state = typhoon_alert_state(c, d.get("marine_alert", []))
        if state != "active":
            if state == "lifted":
                ts = _ts_parse((fixes[-1] or {}).get("DateTime"))
                if ts is not None and (now - ts) <= timedelta(hours=LIFTED_TTL_HOURS):
                    lifted_recent.append(f'{(c.get("name") or "")} 颱風警報（已解除）')
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
        if not m.get("title"):
            continue
        if "解除" not in m["title"] and m.get("category") != "END":
            items.append(("red", "risk_marine", {"title": m["title"]}))
        else:  # 已解除（解除/END）：不計入風險，只供中性狀態列註記
            ts = _ts_parse(m.get("effective"))
            if ts is not None and (now - ts) <= timedelta(hours=LIFTED_TTL_HOURS):
                lifted_recent.append(f'{m["title"]}（生效 {_t(m.get("effective"))}）')
    for r in d.get("reports", []):
        if not r.get("name"):
            continue
        if is_lifted_report(r):
            ts = _ts_parse(r.get("issue"))
            if ts is not None and (now - ts) <= timedelta(hours=LIFTED_TTL_HOURS):
                lifted_recent.append(f'{r["name"]}（發布 {_t(r["issue"])}）')
            continue
        cls = _sev_color(r["name"], r["phenomena"])
        if cls == "sev-green":
            continue
        valid = _t_range(r.get("valid", ""))
        items.append((cls[4:], "risk_report", {"name": r["name"], "valid": valid}))
    if not items and lifted_recent:
        return "neutral", [("neutral", "risk_neutral", {"recent": "、".join(lifted_recent[:3])})]
    level = "red" if any(l == "red" for l, _, _ in items) else ("yellow" if items else "green")
    return level, items


# ---------------------------------------------------------------- 區塊渲染

# 颱風卡 TTL：最新一筆 analysis fix 超過此時數即從首頁移除。
# CWA 對活動中氣旋每 6 小時更新一次 fix，漏 4 個週期（24h）代表 CWA
# 已停止追蹤（消散／不再關注，例：科羅旺 2026/9/7 後 API 仍回傳但無新 fix）。
# 例外：W-C0034-001 對該氣旋有生效中（未解除）海上颱風警報者保留（防 API 延遲）。
# 注意：/map/ 用原始 fetch_typhoons() 全量軌跡，只有首頁卡用過濾後子集（design/site.md、design/map.md）。
TYPHOON_STALE_HOURS = 24


def filter_typhoon_stale(typhoons, marine, now=None):
    """淘汰過時氣旋（見 TYPHOON_STALE_HOURS 註解）。全部淘汰時回傳空清單，
    render_typhoon_card 會顯示「無活動中熱帶氣旋」空狀態。"""
    now = now or datetime.now(TZ_TW)
    active_names, has_active = set(), False
    for m in marine:
        if not m.get("title"):
            continue
        if "解除" in m["title"] or m.get("category") == "END":
            continue
        has_active = True
        n = (m.get("typhoon_name") or "").strip()
        if n:
            active_names.add(n)
    kept = []
    for c in typhoons:
        a = c.get("analysis") or []
        ts = _ts_parse(a[-1].get("DateTime")) if a else None
        stale = ts is not None and (now - ts) > timedelta(hours=TYPHOON_STALE_HOURS)
        if stale and ((c.get("name") or "").strip() in active_names
                      or (has_active and not active_names)):  # 有海警但名稱解析失敗→全保留（fail-safe）
            stale = False
        if not stale:
            kept.append(c)
    return kept


def render_typhoon_card(lang, typhoons, stale_at=None, marine=None):
    """颱風卡永遠顯示：無資料時顯示「無活動中熱帶氣旋」。

    marine（W-C0034-001 警報列）用於推導每支氣旋的**警報狀態**（見 typhoon_alert_state）：
    CWA 對已解除警報的氣旋與從未發警報的外海氣旋都持續發布分析資料，
    不標狀態會被當成「生效中」（2026-10-25 實測：薔琵 24日20:30 已解警、煙花從未發警報，
    兩者都被列為生效中）。
    """
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
        # 警報狀態 badge：active=警報生效中、lifted=警報已解除、none=未發警報（仍持續定位）
        st = typhoon_alert_state(c, marine or [])
        badge_cls, badge_key = {"active": ("sev-red", "state_active"),
                                "lifted": ("sev-grey", "state_lifted"),
                                "none": ("sev-grey", "state_watch")}[st]
        state_tag = f'<span class="badge {badge_cls}">{t(lang, badge_key)}</span>'
        blocks.append(f"""
<div class="typhoon-row">
<div class="map">{typhoon_svg(lang, c)}</div>
<div class="typhoon-info">
<h4 style="margin:0 0 6px">{c['name']}{no}　<span class="muted">{c.get('intl','')}</span>　{state_tag}</h4>
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
        lifted = is_lifted_report(r)
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


def cwa_section_html(lang, data, errors, stale, mode, has_active_event, susp=None):
    """回傳「氣象總覽」section 的 HTML（mode=none 時只有警示）。

    susp：dgpa.fetch() 的 (entries, ok, ts) 或 None（抓取失敗不顯示）。卡片置位（2026/9/15 定案）：
    - 有 currently 相關停班停課公告 → 停班卡**頂位**（層級高於颱風動態）；
    - 無 → 收起卡置於卡片區**底部**；
    - 抓取失敗 → 不顯示（dgpa.render_card 回傳空字串）。
    """
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
    # 排序（2026/9/13 定案、方案 A）：有活動氣旋 → 颱風卡頂位；無活動氣旋且資料抓取正常 → 置底
    #（警報／特報卡承接當下風險訊號）；抓取失敗（stale）仍維持頂位——警示狀態不降級。
    typhoons_live = filter_typhoon_stale(data.get("typhoons", []), data.get("marine_alert", []))
    typhoon_card = render_typhoon_card(lang, typhoons_live, stale.get("typhoons"),
                                       data.get("marine_alert", []))
    typhoon_first = bool(typhoons_live) or bool(stale.get("typhoons"))  # 只有「空＋抓取正常」才置底
    # 停班停課卡置位（2026/9/15 定案）：有 currently 相關公告 → 頂位（高於颱風卡）；
    # 無 → 收起卡置底；susp=None（抓取失敗）→ 不顯示。dgpa 為獨立法令來源，不在 CWA stale 體系內。
    susp_html = dgpa.render_card(lang, susp) if susp is not None else ""
    susp_live = (susp is not None and susp[1]
                 and any(dgpa.is_current(e) for e in susp[0]))
    if susp_live:
        parts.append(susp_html)
    if typhoon_first:
        parts.append(typhoon_card)
    parts.append(render_alert_card(lang, data.get("marine_alert", []), data.get("reports", []),
                                   stale.get("marine_alert", stale.get("reports"))))
    parts.append(render_rain_card(lang, data.get("rain", []), has_active_event, stale.get("rain")))
    if not typhoon_first:
        parts.append(typhoon_card)
    if susp_html and not susp_live:
        parts.append(susp_html)  # 收起卡置底
    return f"""
<section class="cwa">
<h2>{t(lang, "cwa_title")}</h2>
{note}
{"".join(p for p in parts if p)}
</section>"""

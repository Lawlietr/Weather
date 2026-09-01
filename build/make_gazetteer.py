#!/usr/bin/env python3
"""產生 build/gazetteer.json（鄉鎮/縣市座標對照表，供地圖頁使用）。

用途：
- 大雨特報文字、cbph 告警的 county[]/town[]、災情新聞的鄉鎮名 → 地圖座標
- 查不到的鄉鎮回退縣級（counties）；縣級也無（理論上不會）則不上圖

資料來源：
- towns（優先用）：CWA Open Data C-B0074-001/002（有人/無人測站基本資料）的
  「現存測站」，站點 Location 欄位解析出「縣+鄉鎮」，同鄉鎮取站點座標平均
  （source = "cwa_station"）。解析規則（依序）：
  1. Location 先 台→臺 正規化；若以縣名開頭（如「臺中市雙十路…」）先去掉
     縣名再比對，避免解析出「臺中市臺中市」這種垃圾 key；
  2. 行首空白分隔 token 與該縣界線鄉名完全一致 → 直接採用；
  3. 行首 1–4 字＋鄉/鎮/區/市（regex，後接「道」不算），候選名再用該縣
     界線鄉名正規化：完全一致 → 唯一前綴（如「平鎮」→「平鎮區」）→
     唯一包含（如「東山服務區」⊃「東山區」）→ 去尾綴唯一前綴
     （如舊地名「頭份市」→「頭份鎮」）；都無法判定時保留候選原樣。
- towns（補位）：g0v/twgeojson twTown1982.geo.json（MIT，
  https://github.com/g0v/twgeojson）鄉鎮界線，缺站鄉鎮取最大多邊形的質心
  （source = "boundary"）。實測此檔為「2010 五都改制後、2014 桃園升格前」的
  混合快照：五都已是現行區名，桃園縣仍為 1982 鄉鎮名 → 桃園縣一律換算
  「桃園市 X 區」；含 (海) 的離岸海域 feature 排除；全名 台→臺 正規化。
- counties：22 縣市的現存測站座標平均（代表點，非行政中心）。

本腳本是「產生器」，只需在測站/界線資料變動時重跑（需 CWA_API_KEY）；
最終資料 gazetteer.json 為靜態、已 commit，build 直接讀取。
執行：`python3 build/make_gazetteer.py`
"""
import json
import os
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"
TOWN_URL = ("https://raw.githubusercontent.com/g0v/twgeojson/master/"
            "json/twTown1982.geo.json")
TOWN_CACHE = HERE / "_geo_cache_town1982.json"
STATION_CACHES = {
    "C-B0074-001": HERE / "_geo_cache_cwa_stations_001.json",
    "C-B0074-002": HERE / "_geo_cache_cwa_stations_002.json",
}
OUT = HERE / "gazetteer.json"

# Location 行首解析：1–4 字＋鄉/鎮/區/市（lazy，取最前面的行政區）；
# 後接「道」視為鄉道/省道路名（如「○○鄉道」），不算鄉鎮名。
TOWN_RE = re.compile(r"^(.{1,4}?)(鄉|鎮|區|市)(?!道)")

# 手動補位（界線快照與測站都缺的鄉鎮；key 格式同 towns，值 = (lat, lon)）。
# 2026/9/1 逐縣比對官方行政區劃後確認：界線檔＋現存測站已覆蓋全部 170
# 個現行鄉鎮市，此表目前為空（保留機制，未來界線檔更新或測站異動再補）。
MANUAL_TOWNS: dict[str, tuple[float, float]] = {}


def norm(name):
    """台→臺：gazetteer key 一律用官方 臺字系（CWA 用字）。"""
    return name.replace("台", "臺")


def _fetch_json(url, cache, key=None):
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    if key:
        url = f"{url}?Authorization={key}&format=JSON"
    p = subprocess.run(["curl", "-fsS", "--max-time", "90", url],
                       capture_output=True, text=True, timeout=100)
    if p.returncode != 0:
        raise RuntimeError(f"curl 失敗（{p.returncode}）：{p.stderr[:200]}")
    data = json.loads(p.stdout)
    cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def parse_town(location, county, bnames):
    """從 Location 解析鄉鎮名；回傳鄉鎮全名（含後綴）或 None。

    bnames：該縣界線檔的鄉鎮正式名集合（已正規化），用於把 regex 候選
    （如「平鎮」「頭份市」「東山服務區」）對回官方正式名。
    """
    loc = norm((location or "").strip())
    if loc == county:
        return None
    # Location 以縣名開頭（「臺中市雙十路451號」「嘉義市嘉義市東區 親水路…」）：
    # 去掉前綴（最多兩層）再比對；去掉後為空＝只有縣名，視為解析失敗。
    if loc.startswith(county) and len(loc) > len(county):
        rest = loc[len(county):].lstrip()
        if rest.startswith(county):
            rest = rest[len(county):].lstrip()
        if not rest:
            return None
        loc = rest
    names = bnames.get(county, [])
    # 行首 token 直接命中（「大安 忠孝路」「大甲 文武路」）
    token = loc.split(None, 1)[0] if loc else ""
    if len(token) >= 2:
        if token in names:
            return token
        pre = [n for n in names if n.startswith(token)]
        if len(pre) == 1:
            return pre[0]
    m = TOWN_RE.match(loc)
    if not m:
        return None
    cand = m.group(1) + m.group(2)
    if cand in names:
        return cand
    pre = [n for n in names if n.startswith(cand)]  # 平鎮 → 平鎮區
    if len(pre) == 1:
        return pre[0]
    sup = [n for n in names if cand.startswith(n)]  # 東山服務區 ⊃ 東山區
    if len(sup) == 1:
        return sup[0]
    stem = cand[:-1] if cand[-1] in "鄉鎮區市" else cand
    if stem != cand:  # 舊地名：頭份市 → 頭份（→ 頭份鎮）
        pre = [n for n in names if n.startswith(stem)]
        if len(pre) == 1:
            return pre[0]
    return cand


def ring_area(ring):
    a = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        a += x1 * y2 - x2 * y1
    return a * 0.5


def ring_centroid(ring):
    """Shoelace 質心；退化（面積≈0）時回傳點平均。"""
    a = ring_area(ring)
    if abs(a) < 1e-9:
        n = len(ring)
        return (sum(p[0] for p in ring) / n, sum(p[1] for p in ring) / n)
    cx = cy = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        f = x1 * y2 - x2 * y1
        cx += (x1 + x2) * f
        cy += (y1 + y2) * f
    return (cx / (6 * a), cy / (6 * a))


def largest_ring(geom):
    polys = (geom["coordinates"] if geom["type"] == "MultiPolygon"
             else [geom["coordinates"]])
    best, best_a = None, -1.0
    for poly in polys:
        ring = poly[0]
        a = abs(ring_area(ring))
        if a > best_a:
            best, best_a = ring, a
    return best


def main():
    key = os.getenv("CWA_API_KEY")
    if not key:
        raise SystemExit("需要 CWA_API_KEY（測站座標為 gazetteer 主來源）")

    # --- 1. CWA 測站 ---
    stations = []
    for ds in ("C-B0074-001", "C-B0074-002"):
        data = _fetch_json(f"{BASE_URL}/{ds}", STATION_CACHES[ds], key=key)
        for s in data["records"]["data"]["stationStatus"]["station"]:
            if s.get("status") != "現存測站":
                continue
            stations.append(s)
    print(f"現存測站：{len(stations)}")

    # --- 2. 鄉鎮界線（先取正式名集合供測站解析正規化，之後再補位） ---
    geo = _fetch_json(TOWN_URL, TOWN_CACHE)
    bnames, boundary_feats = {}, []  # 縣 -> set(鄉鎮正式名)；(name, county, geom)
    skipped_sea, taoyuan_converted = 0, 0
    for f in geo["features"]:
        p = f["properties"]
        name, county = norm(p.get("TOWNNAME") or ""), norm(p.get("COUNTYNAME"))
        if not name or any(ch in name for ch in "()（）"):
            skipped_sea += 1
            continue  # (海)/(海區) 離岸海域 feature
        if county == "桃園縣":  # 2014 升格未更新：桃園縣 → 桃園市 X 區
            county = "桃園市"
            if name[-1] in "鄉鎮市":
                name = name[:-1] + "區"
            taoyuan_converted += 1
        bnames.setdefault(county, set()).add(name)
        boundary_feats.append((name, county, f["geometry"]))

    # --- 3. 解析測站 縣+鄉鎮，匯總 ---
    town_pts = {}   # (縣, 鄉鎮) -> [(lon, lat), ...]
    county_pts = {} # 縣 -> [(lon, lat), ...]（含解析失敗的站，座標仍有效）
    unparsed = []
    for s in stations:
        lat, lon = float(s["StationLatitude"]), float(s["StationLongitude"])
        county = norm(s["CountyName"])
        county_pts.setdefault(county, []).append((lon, lat))
        town = parse_town(s.get("Location"), county, bnames)
        if town is None:
            unparsed.append((county, s["StationName"], s.get("Location", "")))
            continue
        town_pts.setdefault((county, norm(town)), []).append((lon, lat))
    print(f"解析出鄉鎮站點：{sum(len(v) for v in town_pts.values())}，"
          f"唯一 縣+鄉鎮：{len(town_pts)}，解析失敗：{len(unparsed)}")

    # --- 4. 合併：測站優先，界線補位，手動補位 ---
    towns = {}
    for (county, town), pts in sorted(town_pts.items()):
        n = len(pts)
        towns[f"{county}{town}"] = {
            "lat": round(sum(p[1] for p in pts) / n, 5),
            "lon": round(sum(p[0] for p in pts) / n, 5),
            "source": "cwa_station",
            "stations": n,
        }
    boundary_added = 0
    for name, county, geom in boundary_feats:
        key = f"{county}{name}"
        if key in towns:
            continue  # 已有測站座標（測站優先；同名不同縣為正常，key 含縣名）
        lon, lat = ring_centroid(largest_ring(geom))
        towns[key] = {"lat": round(lat, 5), "lon": round(lon, 5),
                      "source": "boundary", "stations": 0}
        boundary_added += 1
    for key, (lat, lon) in MANUAL_TOWNS.items():
        if key not in towns:
            towns[key] = {"lat": lat, "lon": lon,
                          "source": "manual", "stations": 0}

    counties = {}
    for c, pts in sorted(county_pts.items()):
        n = len(pts)
        counties[c] = {
            "lat": round(sum(p[1] for p in pts) / n, 5),
            "lon": round(sum(p[0] for p in pts) / n, 5),
            "station_count": n,
        }

    out = {
        "meta": {
            "generated": "2026-09-01",
            "sources": {
                "cwa_station": "CWA Open Data C-B0074-001/002 現存測站（官方座標）",
                "boundary": "g0v/twgeojson twTown1982.geo.json（MIT，界線質心；"
                            "2010 五都後/2014 桃園升格前快照，桃園縣已換算為桃園市）",
                "manual": "手動補位（界線快照漏收且無測站的鄉鎮）",
            },
            "keys": "「縣+鄉鎮」全名，官方 臺字系（如 臺中市霧峰區）",
            "normalization": "比對端請將查詢名先 台→臺 正規化再查本表；"
                             "查不到回退 counties（縣級），縣級也無則不上圖",
        },
        "counties": counties,
        "towns": towns,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")

    # --- 報告 ---
    n_st = sum(1 for v in towns.values() if v["source"] == "cwa_station")
    n_bd = sum(1 for v in towns.values() if v["source"] == "boundary")
    n_mn = sum(1 for v in towns.values() if v["source"] == "manual")
    print(f"輸出 {OUT.name}：towns {len(towns)}（測站 {n_st}＋界線 {n_bd}"
          f"＋手動 {n_mn}），counties {len(counties)}")
    print(f"界線補位 {boundary_added}，桃園換算 {taoyuan_converted}，"
          f"排除海域 feature {skipped_sea}")
    print("Location 解析失敗（降級縣級，共 %d）：" % len(unparsed))
    for c, n, loc in unparsed:
        print(f"  {c} / {n} / {loc}")


if __name__ == "__main__":
    main()

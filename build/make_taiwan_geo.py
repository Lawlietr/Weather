#!/usr/bin/env python3
"""產生 build/taiwan_geo.py（台灣本島＋5 離島群的簡化海岸線座標）。

資料來源：
- 本島、澎湖、金門、蘭嶼、綠島：Natural Earth 1:10m admin0 countries（公有領域，
  https://github.com/nvkelso/natural-earth-vector ，Taiwan feature 為 MultiPolygon）。
- 馬祖（連江縣）：Natural Earth 1:10m 的 Taiwan feature 不包含馬祖，改取 g0v/twgeojson
  twCounty2010.geo.json（MIT，https://github.com/g0v/twgeojson ）的 連江縣。

做法：把每個島/島群的 GeoJSON 座標（lon, lat）以 Douglas–Peucker 簡化後，
以「(名稱對應的 i18n key, [(lon,lat),...]]）列表」寫入 taiwan_geo.py。
本腳本是「產生器」，只需在修改輪廓時執行一次；最終資料 taiwan_geo.py 為靜態、可離線使用。
"""
import json
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
NE_URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
          "master/geojson/ne_10m_admin_0_countries.geojson")
G0V_URL = ("https://cdn.jsdelivr.net/gh/g0v/twgeojson@master/"
           "json/twCounty2010.geo.json")
NE_CACHE = HERE / "_geo_cache_ne.json"
G0V_CACHE = HERE / "_geo_cache_tw.json"


def _fetch(url, cache):
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    p = subprocess.run(["curl", "-s", "--max-time", "60", url],
                       capture_output=True, text=True, timeout=70)
    if p.returncode != 0:
        raise RuntimeError(f"curl 失敗（{p.returncode}）")
    data = json.loads(p.stdout)
    cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


# ---- Douglas–Peucker（純 Python，無相依）----

def _dist(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def _perp(p, a, b):
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    if dx == 0 and dy == 0:
        return _dist(p, a)
    # |cross| / |ab|
    return abs((dy * p[0] - dx * p[1]) + (dx * a[1] - dy * a[0])) / ((dx ** 2 + dy ** 2) ** 0.5)


def douglas_peucker(pts, eps):
    if len(pts) < 3:
        return list(pts)
    idx = [0, len(pts) - 1]
    dmax = 0.0
    for i in range(1, len(pts) - 1):
        d = _perp(pts[i], pts[0], pts[-1])
        if d > dmax:
            dmax = d
            maxidx = i
    if dmax > eps:
        left = douglas_peucker(pts[:maxidx + 1], eps)
        right = douglas_peucker(pts[maxidx:], eps)
        return left[:-1] + right
    return [pts[0], pts[-1]]


def ring_to_xy(ring):
    # 閉合環：去掉重複的最後一點
    r = list(ring)
    if r and r[0] == r[-1]:
        r = r[:-1]
    return r


def simplify_ring(ring, eps_deg):
    return douglas_peucker(ring_to_xy(ring), eps_deg)


def polygon_points(poly, eps_deg):
    """poly = [[lon,lat],...]（外環）。回傳簡化後的 [(lon,lat),...]。"""
    if not poly:
        return []
    outer = simplify_ring(poly[0], eps_deg)
    # 忽略內孔（洞）：小圖不需要
    return outer


def is_coord(g):
    return (isinstance(g, list) and len(g) == 2
            and isinstance(g[0], (int, float)) and isinstance(g[1], (int, float)))


def parse_rings(g):
    """從 GeoJSON geometry.coordinates 解析出所有 ring。
    每個 ring = [(lon, lat), ...]。區分座標(2 數值)/ring/多邊形/多邊形集合。
    """
    if isinstance(g, list):
        if g and is_coord(g[0]):
            return [[(c[0], c[1]) for c in g if is_coord(c)]]
        out = []
        for x in g:
            out.extend(parse_rings(x))
        return out
    return []


def area(ring):
    s = 0.0
    for i in range(len(ring)):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % len(ring)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def main():
    ne = _fetch(NE_URL, NE_CACHE)
    tw = _fetch(G0V_URL, G0V_CACHE)

    # --- Natural Earth： Taiwan feature ---
    taiwan = None
    for f in ne["features"]:
        if str(f["properties"].get("NAME", "")).lower() == "taiwan":
            taiwan = f["geometry"]
            break
    if taiwan is None:
        raise RuntimeError("NE 找不到 Taiwan")
    ne_polys = taiwan["coordinates"]  # MultiPolygon: [ [ [ring], ... ], ... ]

    # 依面積由大到小排序多邊形：最大=本島，其餘為離島
    ne_groups = []
    for mp in ne_polys:
        rings = [r for r in parse_rings(mp) if area(ring_to_xy(r)) > 1e-6]
        if not rings:
            continue
        total = area(ring_to_xy(rings[0]))
        ne_groups.append((total, rings))
    ne_groups.sort(key=lambda x: x[0], reverse=True)

    # --- g0v：連江縣（馬祖）---
    matsu = None
    for f in tw["features"]:
        if str(f["properties"].get("name", "")) == "連江縣":
            matsu = f["geometry"]["coordinates"]
            break
    if matsu is None:
        raise RuntimeError("g0v 找不到 連江縣")
    matsu_rings = [r for r in parse_rings(matsu) if area(ring_to_xy(r)) > 1e-6]
    matsu_rings.sort(key=area, reverse=True)
    matsu_total = area(ring_to_xy(matsu_rings[0])) if matsu_rings else 0.0

    # --- 判別各 NE 多邊形的身分 ---
    # 本島 = 面積最大；澎湖群 = 面積 0.02~1.0 deg² 且 lon<120；
    # 金門=lon<119 & lat>24；蘭嶼=lat<22.15；綠島=lat 22.6~22.7 & lon>121.4
    ISLAND_GROUPS = []  # (i18n key, list_of_rings)
    main_rings = []
    penghu_rings = []
    kinmen_rings = []
    lanyu_rings = []
    green_rings = []
    others = []
    for total, rings in ne_groups:
        # 用外環質心分類
        cx = sum(r[0][0] for r in rings) / len(rings)
        cy = sum(r[0][1] for r in rings) / len(rings)
        if total == ne_groups[0][0]:
            main_rings = rings
            continue
        if cx < 119.0 and cy > 24.2:        # 金門
            kinmen_rings += rings
        elif cy < 22.15 and cx > 121.3:     # 蘭嶼
            lanyu_rings += rings
        elif 22.55 < cy < 22.80 and cx > 121.3:  # 綠島
            green_rings += rings
        elif cx < 120.2 and 23.2 < cy < 23.85:   # 澎湖群
            penghu_rings += rings
        else:
            others.append((total, rings))
    # 其餘零散小島各成一島
    for total, rings in sorted(others, key=lambda x: x[0], reverse=True):
        ISLAND_GROUPS.append((f"island_other_{len(ISLAND_GROUPS) + 1}", rings))

    MIN_PTS = 3  # 小於此點數的 ring 視為雜訊（如 2 點退化邊），捨去

    def emit(rings, eps_deg):
        out = []
        for r in rings:
            r = simplify_ring(r, eps_deg)
            if len(r) >= MIN_PTS:
                out.append(r)
        return out

    # 簡化 epsilon（度）：本島稍細，離島可粗些
    main_pts = emit(main_rings, 0.02)
    penghu_pts = emit(penghu_rings, 0.03)
    kinmen_pts = emit(kinmen_rings, 0.02)
    lanyu_pts = emit(lanyu_rings, 0.02)
    green_pts = emit(green_rings, 0.02)
    matsu_pts = emit(matsu_rings, 0.015)

    def fmt(rings):
        # rings = list of rings; each ring = [(lon, lat), ...]
        # 每個 ring 輸出一個 "[[lon,lat],[lon,lat],...]"
        return ",\n            ".join(
            "[" + ", ".join(f"[{lon:.4f}, {lat:.4f}]" for lon, lat in r) + "]"
            for r in rings)

    def block(key, rings, indent="            "):
        return f'("{key}", [\n{indent}{fmt(rings)}\n        ])'

    lines = []
    lines.append('"""台灣輪廓資料：本島＋離島海岸線（簡化後座標 lon,lat）。')
    lines.append('')
    lines.append('來源：本島／澎湖／金門／蘭嶼／綠島 = Natural Earth 1:10m（公有領域）')
    lines.append('；馬祖（連江縣）= g0v/twgeojson（MIT）。由 build/make_taiwan_geo.py 產生，')
    lines.append('不要手改；要改請改產生器後重跑。')
    lines.append('"""')
    lines.append('')
    lines.append('# 每個元素：(i18n 標籤 key, [(lon, lat), ...]) 閉合多邊形。')
    lines.append('# 本島與各離島各自獨立 polygon，避免用本島凸包把海峽包進來。')
    lines.append('ISLANDS = [')
    blocks = [
        block("island_main", main_pts),
        block("island_penghu", penghu_pts),
        block("island_kinmen", kinmen_pts),
        block("island_lanyu", lanyu_pts),
        block("island_green", green_pts),
        block("island_matsu", matsu_pts),
    ] + [block(k, r) for k, r in ISLAND_GROUPS]
    lines.append("            " + ",\n            ".join(blocks))
    lines.append("]")
    lines.append("")

    (HERE / "taiwan_geo.py").write_text("\n".join(lines), encoding="utf-8")

    # 報告
    def npts(rings):
        return sum(len(r) for r in rings)
    print("ISLANDS:", ", ".join(k for k, _ in [("main", main_pts),("penghu", penghu_pts),("kinmen", kinmen_pts),("lanyu", lanyu_pts),("green", green_pts),("matsu", matsu_pts)] + [(k,r) for k,r in ISLAND_GROUPS]))
    print("points -> main:", npts(main_pts), "penghu:", npts(penghu_pts),
          "kinmen:", npts(kinmen_pts), "lanyu:", npts(lanyu_pts),
          "green:", npts(green_pts), "matsu:", npts(matsu_pts),
          "total_pts:", sum(npts(r) for _, r in
                            [("main", main_pts),("penghu", penghu_pts),("kinmen", kinmen_pts),
                             ("lanyu", lanyu_pts),("green", green_pts),("matsu", matsu_pts)]
                            + [(k, r) for k, r in ISLAND_GROUPS]))


if __name__ == "__main__":
    main()

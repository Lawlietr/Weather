#!/usr/bin/env python3
"""產生 build/taiwan_geo.py（台灣本島＋5 離島群的簡化海岸線座標、地圖兜底陸地層）。

資料來源：
- 本島、澎湖、金門、蘭嶼、綠島：Natural Earth 1:10m admin0 countries（公有領域，
  https://github.com/nvkelso/natural-earth-vector ，Taiwan feature 為 MultiPolygon）。
- 馬祖（連江縣）：Natural Earth 1:10m 的 Taiwan feature 不包含馬祖，改取 g0v/twgeojson
  twCounty2010.geo.json（MIT，https://github.com/g0v/twgeojson ）的 連江縣。
- 兜底陸地層 FALLBACK_LAND（§2-7c）：Natural Earth 10m land（同一來源、含各國陸地），
  裁剪到「地圖可能露出瓦片缺口的範圍」＝ `tiles.zoom_bbox()` 各層聯集 ⊕ MARGIN。之所以
  需要：`errorTileUrl` 只補海色，缺瓦片處會變成「整片海」——台灣自己在瓦片缺口處也會消失。

做法：把每個島/島群的 GeoJSON 座標（lon, lat）以 Douglas–Peucker 簡化後，
以「(名稱對應的 i18n key, [(lon,lat),...]]）列表」寫入 taiwan_geo.py；兜底層則以
矩形裁剪（Sutherland–Hodgman）＋面積自適應簡化後寫入 FALLBACK_LAND。
本腳本是「產生器」，只需在修改輪廓時執行一次；最終資料 taiwan_geo.py 為靜態、可離線使用。

⚠️ 改 `tiles.MAP_MAX_BOUNDS`／`ZOOMS` 後必須重跑本腳本——兜底層的範圍由瓦片視野推導，
   兩者不同步就會出現「瓦片有缺口但兜底層沒蓋到那區」（§2-7 的漂移教訓，見 design/map.md）。
"""

import json
import math
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tiles  # 地圖視野的單一事實來源（兜底層範圍由 `tiles.zoom_bbox()` 推導，§2-7）

NE_URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
          "master/geojson/ne_10m_admin_0_countries.geojson")
NE_LAND_URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
               "master/geojson/ne_10m_land.geojson")
G0V_URL = ("https://cdn.jsdelivr.net/gh/g0v/twgeojson@master/"
           "json/twCounty2010.geo.json")
NE_CACHE = HERE / "_geo_cache_ne.json"
NE_LAND_CACHE = HERE / "_geo_cache_ne_land.json"
G0V_CACHE = HERE / "_geo_cache_tw.json"

# 兜底陸地層（§2-7c）參數
FALLBACK_MARGIN_DEG = 0.5   # 瓦片 bbox 之外再留裕度（視口比 maxBounds 寬時的溢出＋橡皮筋拖曳）
FALLBACK_EPS_DEG = 0.003    # 簡化上限（≈330m）；小島依面積自適應調小，避免整島被吸掉
FALLBACK_MIN_PTS = 4        # 少於此點數的環＝簡化後退化，丟棄


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


# ---- 矩形裁剪＋迭代簡化（兜底層專用；大陸/大島的環可達數萬點，遞迴版會爆 stack）----

def clip_rect(rect, ring):
    """Sutherland–Hodgman 對矩形裁剪（四個軸對齊半平面）。回傳窗內部分（邊界沿裁剪邊切割）。"""
    x0, y0, x1, y1 = rect
    out = list(ring)

    def isect(p, q, axis, val):
        a, b = (p[0], q[0]) if axis == 0 else (p[1], q[1])
        if a == b:
            return p
        t = (val - a) / (b - a)
        return (val, p[1] + t * (q[1] - p[1])) if axis == 0 else (p[0] + t * (q[0] - p[0]), val)

    for inside, axis, val in ((lambda p: p[0] >= x0, 0, x0), (lambda p: p[1] >= y0, 1, y0),
                              (lambda p: p[0] <= x1, 0, x1), (lambda p: p[1] <= y1, 1, y1)):
        inp, out = out, []
        if not inp:
            break
        for i, cur in enumerate(inp):
            nxt = inp[(i + 1) % len(inp)]
            ci, ni = inside(cur), inside(nxt)
            if ci:
                out.append(cur)
            if ci != ni:
                out.append(isect(cur, nxt, axis, val))
    return out


def _perp2(p, a, b):
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    if dx == 0 and dy == 0:
        return ((p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2) ** 0.5
    return abs(dy * p[0] - dx * p[1] + dx * a[1] - dy * a[0]) / ((dx ** 2 + dy ** 2) ** 0.5)


def douglas_peucker_iter(pts, eps):
    """迭代版 Douglas–Peucker（閉合環：先固定首尾＋距首尾連線最遠點）。
    大環用這個——上面的遞迴版對數萬點的環會超過 recursion limit。"""
    if len(pts) < 4:
        return list(pts)
    dmax, k = 0.0, 1
    for i in range(1, len(pts) - 1):
        d = _perp2(pts[i], pts[0], pts[-1])
        if d > dmax:
            dmax, k = d, i
    keep = [False] * len(pts)
    keep[0] = keep[-1] = keep[k] = True
    stack = [(0, k), (k, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 2:
            continue
        dm, m = 0.0, a
        for i in range(a + 1, b):
            d = _perp2(pts[i], pts[a], pts[b])
            if d > dm:
                dm, m = d, i
        if dm > eps:
            keep[m] = True
            stack.append((a, m))
            stack.append((m, b))
    return [p for p, kp in zip(pts, keep) if kp]


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


def fallback_land():
    """兜底陸地層（§2-7c）：裁剪到「地圖可能露出瓦片缺口的範圍」的陸地輪廓。

    範圍由 `tiles.zoom_bbox()` 各層聯集 ⊕ `FALLBACK_MARGIN_DEG` **推導**（不寫死座標矩陣，
    與離線瓦片同一事實來源）。來源 Natural Earth 10m land（公有領域、含各國陸地）。
    回傳 `(rect, rings)`；rings 由大而小排序。
    """
    bs = [tiles.zoom_bbox(z) for z in tiles.ZOOMS]
    rect = (min(b[0] for b in bs) - FALLBACK_MARGIN_DEG,
            min(b[1] for b in bs) - FALLBACK_MARGIN_DEG,
            max(b[2] for b in bs) + FALLBACK_MARGIN_DEG,
            max(b[3] for b in bs) + FALLBACK_MARGIN_DEG)
    land = _fetch(NE_LAND_URL, NE_LAND_CACHE)
    rings = []
    for f in land["features"]:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            r = [(c[0], c[1]) for c in poly[0]]      # 只取外環（內孔＝湖，本區無關）
            if r and r[0] == r[-1]:
                r = r[:-1]
            if len(r) < FALLBACK_MIN_PTS:
                continue
            xs = [p[0] for p in r]
            ys = [p[1] for p in r]
            # 先做 bbox 粗篩再裁剪——大陸的環動輒數萬點，不相交就不必進裁剪
            if max(xs) < rect[0] or min(xs) > rect[2] or max(ys) < rect[1] or min(ys) > rect[3]:
                continue
            c = clip_rect(rect, r)
            if len(c) >= FALLBACK_MIN_PTS:
                rings.append(c)
    out = []
    for r in rings:
        a = area(r)
        # 面積自適應 eps：大環用上限（0.003°≈330m）；小島用約 0.12×邊長，
        # 否則與那國/宮古這類小島會被整個簡化掉（實測固定 eps=0.003 會丟 9 環）
        eps = min(FALLBACK_EPS_DEG, max(0.0004, 0.12 * (a ** 0.5)))
        s = douglas_peucker_iter(r, eps)
        if len(s) >= FALLBACK_MIN_PTS:
            out.append(s)
    out.sort(key=area, reverse=True)
    return rect, out


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
    fb_rect, fb_land = fallback_land()

    lines.append('"""台灣輪廓資料：本島＋離島海岸線（簡化後座標 lon,lat）＋地圖兜底陸地層。')
    lines.append('')
    lines.append('來源：本島／澎湖／金門／蘭嶼／綠島 = Natural Earth 1:10m（公有領域）')
    lines.append('；馬祖（連江縣）= g0v/twgeojson（MIT）；FALLBACK_LAND = Natural Earth 10m land。')
    lines.append('由 build/make_taiwan_geo.py 產生，不要手改；要改請改產生器後重跑。')
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
    lines.append("# 兜底陸地層（§2-7c）：缺瓦片時 errorTileUrl 只補海色，沒這層的話瓦片缺口會連")
    lines.append("# 台灣自己在圖上消失。這層保底顯示「可能露出瓦片缺口範圍」內的陸地。")
    lines.append(f"# 範圍 (lon_min, lat_min, lon_max, lat_max) = ({fb_rect[0]:.2f}, {fb_rect[1]:.2f}, "
                 f"{fb_rect[2]:.2f}, {fb_rect[3]:.2f})")
    lines.append("#   ＝ tiles.zoom_bbox() 各層聯集 ⊕ margin（改 tiles 視野後要重跑產生器，否則兜底層不會跟著長）")
    lines.append("# 每條 ring = [(lon, lat), ...] 閉合多邊形（不含重複尾點），由大而小排序；")
    lines.append("# 矩形裁剪造成的沿邊直線邊（大陸/大島被窗切開處）屬預期，該處本就是視野邊緣。")
    lines.append("FALLBACK_LAND = [")
    lines.append("            " + ",\n            ".join(
        "[" + ", ".join(f"[{lon:.4f}, {lat:.4f}]" for lon, lat in r) + "]" for r in fb_land))
    lines.append("]")
    lines.append("")

    (HERE / "taiwan_geo.py").write_text("\n".join(lines), encoding="utf-8")

    # 報告
    def npts(rings):
        return sum(len(r) for r in rings)
    fb_pts = sum(len(r) for r in fb_land)
    print(f"FALLBACK_LAND -> rings={len(fb_land)} pts={fb_pts} "
          f"bbox=({fb_rect[0]:.2f},{fb_rect[1]:.2f})~({fb_rect[2]:.2f},{fb_rect[3]:.2f}) "
          f"inline≈{len(fmt(fb_land))/1024:.0f} KB")
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

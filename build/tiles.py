"""離線地圖瓦片抓取（TODO §2「離線自駕」硬需求）。

build 時從 OSM 抓台灣 bbox 內的瓦片 → 快取 build/_tile_cache/（持久化、缺什麼補什麼，
幾乎不變）→ 複製到 public/assets/tiles/{z}/{x}_{y}.png；Leaflet 指向本地瓦片
→ 前端零外部請求（災發時網路最不稳定，離線靠得住）。

瓦片來源：OSM 德國社群 tile server（tile.openstreetmap.de，免 key）——2026/9/2 實測
OSM 官方 server（含 a./c. 副域）對本機 IP 回「假 200＋封鎖頁 PNG」（967 張全中）、
換 UA 無效；CARTO 全端點需 API key（瓦片帶浮水印）。OSM.de 經 20 張抽樣全數
200＋合法 PNG（含海域稀疏空瓦片），穩定可用。署名「© OpenStreetMap contributors」。
注意：社群伺服器有流量上限，本專案 build 時一次性抓 967 張＋之後 cache 命中，
符合其政策；若 OSM.de 日後也封，改抓其他 OSM 鏡像即可（URL 一處）。

守則：
- 單張失敗 → 跳過＋warning、不中斷 build（沿用 RSS/cbph 守則）；缺的瓦片顯示空白底。
- HTTP 狀態碼 ≠ 200 或 PNG signature 不對 → 視為失敗（防 OSM 式「假 200 封鎖頁」）。
- 快取已存在（>100 位元組）→ 不重抓。
- 自訂 User-Agent；地圖頁頁尾顯示「© OpenStreetMap contributors」（署名義務）。
"""
import math
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

TILE_SERVER = "https://tile.openstreetmap.de"
USER_AGENT = "WeatherSite/1.0 (offline tiles for weather.avpclub.eu.org; contact: lawliet@avpclub.eu.org)"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
# bbox (lon_min, lat_min, lon_max, lat_max)：本島＋澎湖／金門／馬祖／蘭嶼／綠島
BBOX = (118.0, 21.9, 122.0, 26.4)
ZOOMS = (8, 9, 10, 11)
TIMEOUT = 15
WORKERS = 8
MIN_TILE_BYTES = 100  # 小於此視為无效（空 tile/錯誤頁）


def _tile_xy(lon, lat, z):
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    lat_r = math.radians(lat)
    y = int((1 - math.asinh(math.tan(lat_r)) / math.pi) / 2 * n)
    return x, y


def tile_list(bbox=BBOX, zooms=ZOOMS):
    """回傳 [(z, x, y), ...]（bbox 角點外推的完整網格）。"""
    lon0, lat0, lon1, lat1 = bbox
    out = []
    for z in zooms:
        xa, ya = _tile_xy(lon0, lat1, z)
        xb, yb = _tile_xy(lon1, lat0, z)
        for x in range(xa, xb + 1):
            for y in range(ya, yb + 1):
                out.append((z, x, y))
    return out


def _fetch_one(z, x, y, cache):
    """抓單張瓦片進快取（先寫 .tmp 再改名，避免中斷留下殘檔）。回傳 fetched/cached/failed。"""
    dest = cache / str(z) / f"{x}_{y}.png"
    if dest.exists() and dest.stat().st_size >= MIN_TILE_BYTES:
        return "cached"
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".png.tmp")
    url = f"{TILE_SERVER}/{z}/{x}/{y}.png"
    try:
        p = subprocess.run(
            ["curl", "-s", "--max-time", str(TIMEOUT), "-A", USER_AGENT,
             "-w", "%{http_code}", "-o", str(tmp), url],
            capture_output=True, text=True, timeout=TIMEOUT + 10)
        status = p.stdout.strip()[-3:] if p.stdout else ""
        ok = (p.returncode == 0 and status == "200" and tmp.exists()
              and tmp.stat().st_size >= MIN_TILE_BYTES)
        if ok:
            with open(tmp, "rb") as f:
                ok = f.read(8) == PNG_MAGIC
        if ok:
            tmp.rename(dest)
            return "fetched"
    except (subprocess.TimeoutExpired, OSError):
        pass
    tmp.unlink(missing_ok=True)
    return "failed"


def fetch_tiles(cache_dir, out_dir, warnings=None):
    """抓缺的瓦片 → 快取 → 全部複製到 out_dir/tiles/{z}/{x}_{y}.png。

    回傳 (total, fetched, cached, failed)。任何失敗不 raise（呼叫端仍應再包 try）。
    """
    cache, out = Path(cache_dir), Path(out_dir)
    tiles = tile_list()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        results = list(ex.map(lambda t: _fetch_one(*t, cache), tiles))
    for (z, x, y), _r in zip(tiles, results):
        src = cache / str(z) / f"{x}_{y}.png"
        if src.exists() and src.stat().st_size >= MIN_TILE_BYTES:
            dest = out / "tiles" / str(z)
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / f"{x}_{y}.png")
    fetched, failed = results.count("fetched"), results.count("failed")
    if failed and warnings is not None:
        warnings.append(f"map tiles: {failed} 張瓦片抓取失敗（該處顯示空白底）")
    return len(tiles), fetched, len(tiles) - fetched - failed, failed

"""離線地圖瓦片抓取＋地圖視野常數（design/map.md「離線自駕」硬需求、§2-7 底圖視野擴展）。

build 時從 OSM 抓瓦片 → 快取 build/_tile_cache/（持久化、缺什麼補什麼，幾乎不變）
→ 複製到 public/assets/tiles/{z}/{x}_{y}.png；Leaflet 指向本地瓦片
→ 前端零外部請求（災發時網路最不穩定，離線靠得住）。

⚠️ 本模組是「地圖視野」的單一事實來源：`MAP_CENTER`／`MAP_ZOOM`／`MAP_MAX_BOUNDS`
定義在此，`map_page.py` 由此 import（不在兩處各寫一份、避免漂移）。每一 zoom 層的瓦片
bbox 由 `zoom_bbox(z)` 從 maxBounds 推導，**不寫死座標矩陣**。

瓦片來源：OSM 德國社群 tile server（tile.openstreetmap.de，免 key）——2026/9/2 實測
OSM 官方 server（含 a./c. 副域）對本機 IP 回「假 200＋封鎖頁 PNG」（當時 967 張全中）、
換 UA 無效；CARTO 全端點需 API key（瓦片帶浮水印）。OSM.de 經 20 張抽樣全數
200＋合法 PNG（含海域稀疏空瓦片），穩定可用。署名「© OpenStreetMap contributors」。
注意：社群伺服器有流量上限，本專案 build 時一次性抓完、之後 cache 命中，符合其政策；
若 OSM.de 日後也封，改抓其他 OSM 鏡像即可（URL 一處）。

守則：
- 單張失敗 → 跳過＋warning、不中斷 build（沿用 RSS/cbph 守則）；缺的瓦片由前端
  `errorTileUrl` 補一張**全透明**佔位底（`BLANK_TILE_NAME`），海色來自容器背景
  （`--sea`＝`OCEAN_RGB`）、陸地來自 §2-7c 兜底陸地層（獨立 pane、zIndex 低於 tilePane）。
  ⚠️ 佔位底不得改成實色：§2-7 曾用不透明的海色 `_ocean.png`，結果它蓋在兜底陸地層之上
  → 缺瓦片處只剩一片海、連台灣自己都不見（2026-10-27 實測發現、已改）。
- HTTP 狀態碼 ≠ 200 或 PNG signature 不對 → 視為失敗（防 OSM 式「假 200 封鎖頁」）。
- 快取已存在（>100 位元組）→ 不重抓。
- 自訂 User-Agent；地圖頁頁尾顯示「© OpenStreetMap contributors」（署名義務）。
"""
import math
import shutil
import struct
import subprocess
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

TILE_SERVER = "https://tile.openstreetmap.de"
USER_AGENT = "WeatherSite/1.0 (offline tiles for weather.avpclub.eu.org; contact: lawliet@avpclub.eu.org)"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
TIMEOUT = 15
WORKERS = 8
MIN_TILE_BYTES = 100  # 小於此視為無效（空 tile/錯誤頁）

# ── 地圖視野（§2-7，2026/10/26 定案；背景與實測 → design/map.md「底圖視野擴展」）─────
# ⚠️ 不變項：MAP_MAX_BOUNDS 的中心必須恆等於 MAP_CENTER。Leaflet 1.9.4 `setView` 對
#    maxBounds clamp——視口寬於 bounds 經度跨度時會把整個視口對齊 bounds 中心（2026/9/16
#    實測：舊 bounds 中心 120.05 導致開圖偏西 0.9°）。
MAP_CENTER = [23.7, 121.3]  # [lat, lon]：往東 0.35°，右側留太平洋（颱風來向、巨浪告警、風圈）
MAP_ZOOM = 8                # 開圖 zoom，同時是前端 minZoom
ZOOMS = (8, 9, 10, 11)      # 離線瓦片層；前端 maxZoom 同為 11
MAP_MAX_BOUNDS = [[20.7, 118.3], [26.7, 124.3]]  # [[lat_min,lon_min],[lat_max,lon_max]]，中心＝(23.7, 121.3)
# ⚠️ 不變項：每一 zoom 層的瓦片 bbox 必須涵蓋「視口可能到的範圍」，否則該處只剩海色底。
#    低 zoom 時桌面視口比 maxBounds 寬（z8 1920px＝10.6° 經度 > bounds 的 6.0°）→ 兩側各
#    溢出 2.27°，z8 需要更寬瓦片帶；高 zoom 視口（z11 1920px＝1.3°）比 bounds 窄 → 蓋 bounds 就夠。
VIEWPORT_PX = (1920, 1200)  # 依最大常用桌面視口估算；2560px 以上 ultrawide 時 z8 最外側刻意露海色
ELASTIC_DEG = 0.3           # maxBoundsViscosity=0 拖曳橡皮筋的暫時溢出裕度
# 缺瓦片處：海色由 CSS 容器背景提供（與瓦片自帶的海洋同色 → 出範圍看到的是「海」不是「沒畫完」）；
# errorTileUrl 那張佔位底則必須**全透明**，否則會蓋住 tilePane 下方的兜底陸地層（見上方守則）。
OCEAN_RGB = (0xAA, 0xD3, 0xDF)
OCEAN_CSS = "#%02x%02x%02x" % OCEAN_RGB     # CSS/JS 用的單一字串來源（免與 OCEAN_RGB 漂移）
BLANK_TILE_NAME = "_blank.png"              # errorTileUrl：256×256 全透明 PNG
LEGACY_OCEAN_TILE = "_ocean.png"            # 舊的不透明檔：要從 public/ 清掉，免上傳舊檔


def _tile_xy(lon, lat, z):
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    lat_r = math.radians(lat)
    y = int((1 - math.asinh(math.tan(lat_r)) / math.pi) / 2 * n)
    return x, y


def _deg_per_px(z):
    """本層 1 px 對應的經度（Web Mercator：全球寬 256·2^z px）。"""
    return 360.0 / (256 * 2 ** z)


def zoom_bbox(z):
    """本層瓦片 bbox `(lon_min, lat_min, lon_max, lat_max)`。

    ＝ `MAP_MAX_BOUNDS` ⊕ 該層桌面視口溢出量 ⊕ `ELASTIC_DEG`。採推導而非寫死矩陣：改
    `MAP_MAX_BOUNDS`／`VIEWPORT_PX` 後各層 bbox 自動跟上，不會再出現「maxBounds 比瓦片寬」
    的漂移（§2-7 的成因正是舊 maxBounds 東界 123.6°E 超出舊瓦片東界 122°E）。
    """
    (lat0, lon0), (lat1, lon1) = MAP_MAX_BOUNDS
    d = _deg_per_px(z)
    vlon, vlat = VIEWPORT_PX[0] * d, VIEWPORT_PX[1] * d
    mlon = max(0.0, (vlon - (lon1 - lon0)) / 2) + ELASTIC_DEG
    mlat = max(0.0, (vlat - (lat1 - lat0)) / 2) + ELASTIC_DEG
    return (lon0 - mlon, lat0 - mlat, lon1 + mlon, lat1 + mlat)


def tile_list(zooms=ZOOMS):
    """回傳 `[(z, x, y), ...]`（每層用自己的 `zoom_bbox(z)`、角點外推的完整網格）。"""
    out = []
    for z in zooms:
        lon0, lat0, lon1, lat1 = zoom_bbox(z)
        xa, ya = _tile_xy(lon0, lat1, z)
        xb, yb = _tile_xy(lon1, lat0, z)
        for x in range(xa, xb + 1):
            for y in range(ya, yb + 1):
                out.append((z, x, y))
    return out


def blank_png():
    """256×256 **全透明** PNG（RGBA、stdlib zlib 手寫、不依賴 Pillow）——`errorTileUrl` 的佔位底。

    透明而非實色：缺瓦片時要同時露出「容器背景的海色」與「tilePane 下方的兜底陸地層」（§2-7c）；
    實色底會把兩者都蓋住。
    """
    w = h = 256
    raw = (b"\x00" + bytes(4) * w) * h        # 每行：filter 0 + RGBA 全 0（alpha 0＝全透明）

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    return (PNG_MAGIC
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))   # 6＝RGBA
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


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
    """抓缺的瓦片 → 快取 → 全部複製到 out_dir/tiles/{z}/{x}_{y}.png，並寫出透明佔位瓦片。

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
    # §2-7a/2-7c 缺瓦片佔位底（前端 errorTileUrl）：每次重寫；必須全透明（見 blank_png 註解）
    (out / "tiles").mkdir(parents=True, exist_ok=True)
    (out / "tiles" / BLANK_TILE_NAME).write_bytes(blank_png())
    legacy = out / "tiles" / LEGACY_OCEAN_TILE
    if legacy.exists():
        legacy.unlink()      # 舊的不透明海色檔：不清就會留在 public/ 被上傳
    fetched, failed = results.count("fetched"), results.count("failed")
    if failed and warnings is not None:
        warnings.append(f"map tiles: {failed} 張瓦片抓取失敗（該處顯示海色底）")
    return len(tiles), fetched, len(tiles) - fetched - failed, failed

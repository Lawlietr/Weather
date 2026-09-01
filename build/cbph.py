"""cbph.cwa.gov.tw 災防告警（PWS）抓取。

資料源：CWA「預報中心資訊發布查詢系統」公開 JSON API（免 key）。
非 Open Data 正式目錄、無 SLA → 容錯守則：任何類型失敗跳過＋warning、不中斷 build。

Endpoints（2026/9/1 實測）：
- GET /api/global/  — 目前告警，依 4 類分組
- GET /api/{type}/  — 歷史（預設最新 50 筆；county= 過濾不可靠，抓全量自行 filter）

陷阱（實測）：
- 空類型回 503（如 largesurfs）→ 503/404 一律容錯跳過。
- 預設回傳 is_active 可能全 True → build 端自行驗 is_active＋expires。
- 時間皆 UTC（Z 結尾）→ 一律轉 UTC+8（沿用固定 UTC+8 慣例）。
- polygon 欄位為字串「lat,lon lat,lon ...」，多 ring 以「;」分開＝官方影響區域座標。
- 官方頁 deep link：https://cbph.cwa.gov.tw/ui/?type={type}&identifier={identifier}

UI 引用措辭：「資料來源：中央氣象署災防告警系統（PWS）」。
"""
import json
import subprocess
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

TZ_TW = timezone(timedelta(hours=8))
BASE = "https://cbph.cwa.gov.tw/api"
TIMEOUT = 30

# slug → (類型中文名, 建議配色)；配色沿用 cbph UI（大雷雨/颱風強風），其餘自定。
TYPES = {
    "cells":          ("大雷雨即時訊息", "#f59e0b"),
    "tywinds":        ("颱風強風告警",  "#ef4444"),
    "mountainstorms": ("山區暴雨警示",  "#7c3aed"),
    "largesurfs":     ("巨浪告警",      "#0ea5e9"),
}


class CbphFetchError(RuntimeError):
    pass


def _get_json(path):
    """curl 抓取 cbph JSON；非 200 一律 raise（由呼叫端容錯）。"""
    url = BASE + path
    p = subprocess.run(
        ["curl", "-s", "--max-time", str(TIMEOUT), "-w", "\n%{http_code}", url],
        capture_output=True, text=True, timeout=TIMEOUT + 10)
    if p.returncode != 0:
        raise CbphFetchError(f"curl 失敗（returncode={p.returncode}）")
    body, _, code = p.stdout.rpartition("\n")
    if code.strip() != "200":
        raise CbphFetchError(f"HTTP {code or '?'}")
    return json.loads(body)


def _parse_ts(value):
    """UTC ISO8601（Z 結尾）→ UTC+8 datetime；空值回 None。"""
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.astimezone(TZ_TW)


def parse_polygon(s):
    """cbph polygon 字串 → GeoJSON multi-ring：[[[lon,lat],...],...]。

    格式「lat,lon lat,lon ...」，多 ring 以「;」分開；空/ malformed 回 []。
    """
    rings = []
    if not s:
        return rings
    for ring_str in s.split(";"):
        ring = []
        for pair in ring_str.split():
            try:
                lat, lon = pair.split(",")
                ring.append([float(lon), float(lat)])  # GeoJSON 為 [lon, lat]
            except (ValueError, TypeError):
                continue
        if len(ring) >= 3:
            rings.append(ring)
    return rings


def _normalize(slug, item):
    """單筆 cbph 告警 → 標準化 dict（時間皆 UTC+8）。"""
    zh_name, color = TYPES[slug]
    expires = _parse_ts(item.get("expires"))
    is_active = bool(item.get("is_active"))
    return {
        "identifier": item.get("identifier", ""),
        "official_id": item.get("official_id", ""),
        "type": slug,
        "type_name": zh_name,
        "color": color,
        "is_active": is_active,
        "still_valid": is_active and (expires is None or expires > datetime.now(TZ_TW)),
        "sent": _parse_ts(item.get("sent")),
        "effective": _parse_ts(item.get("effective")),
        "expires": expires,
        "description": item.get("description", ""),
        "cmam_text": item.get("cmam_text", ""),
        "cb_enabled": bool(item.get("cb_enabled")),
        "counties": item.get("county") or [],
        "towns": item.get("town") or [],
        "coastal_counties": item.get("coastal_county") or [],
        "coastal_towns": item.get("coastal_town") or [],
        "polygon": parse_polygon(item.get("polygon")),
        "source_url": f"https://cbph.cwa.gov.tw/ui/?type={slug}&identifier={urllib.parse.quote(item.get('identifier', ''))}",
    }


def fetch_alerts(only_active=False, warnings=None):
    """抓 4 類告警並標準化。單類失敗 → 記 warning、跳過，不中斷。

    only_active=True：只回「仍生效」（is_active 且 expires 未過）的告警。
    warnings：可選 list，累積 warning 字串（呼叫端可用於 build log）。
    """
    alerts = []
    for slug in TYPES:
        try:
            data = _get_json(f"/{slug}/")
        except (CbphFetchError, json.JSONDecodeError, subprocess.TimeoutExpired) as e:
            msg = f"cbph {slug}: 抓取失敗（{e}）— 跳過"
            print(f"[warning] {msg}")
            if warnings is not None:
                warnings.append(msg)
            continue
        items = data if isinstance(data, list) else []
        for item in items:
            a = _normalize(slug, item)
            if only_active and not a["still_valid"]:
                continue
            alerts.append(a)
    return alerts


def fetch_map_features(only_active=True, warnings=None):
    """fetch_alerts() → map.geo.json 用 GeoJSON Feature 列表。"""
    features = []
    for a in fetch_alerts(only_active=only_active, warnings=warnings):
        props = {
            "level": "red",  # 目前 4 類皆為告警級；日後特報/雨量層再擴充 🟡/🟢
            "type": a["type"],
            "type_name": a["type_name"],
            "color": a["color"],
            "source": "cbph",
            "identifier": a["identifier"],
            "official_id": a["official_id"],
            "effective": a["effective"].strftime("%Y/%-m/%-d %H:%M") if a["effective"] else None,
            "expires": a["expires"].strftime("%Y/%-m/%-d %H:%M") if a["expires"] else None,
            "counties": a["counties"],
            "towns": a["towns"],
            "description": a["description"],
            "cmam_text": a["cmam_text"],
            "cb_enabled": a["cb_enabled"],
            "source_url": a["source_url"],
        }
        geo = {"type": "MultiPolygon", "coordinates": a["polygon"]} if a["polygon"] else None
        if geo is None:
            # 無 polygon 的告警：暫不上圖（後續可用 gazetteer 對鄉鎮中心點補點層）。
            continue
        features.append({"type": "Feature", "geometry": geo, "properties": props})
    return features


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--county", help="只列出影響該縣市的告警（採集測試用）")
    args = ap.parse_args()

    alerts = fetch_alerts(only_active=True)
    if args.county:
        alerts = [a for a in alerts if args.county in a["counties"]]

    print(f"目前生效告警共 {len(alerts)} 筆" + (f"（限定 {args.county}）" if args.county else ""))
    for a in alerts:
        eff = a["effective"].strftime("%-m/%-d %H:%M") if a["effective"] else "?"
        exp = a["expires"].strftime("%-m/%-d %H:%M") if a["expires"] else "?"
        rings = sum(len(r) for r in a["polygon"])
        print(f"\n[{a['type_name']}] {a['identifier']}")
        print(f"  official_id: {a['official_id']}")
        print(f"  生效: {eff} → {exp} (UTC+8)")
        print(f"  縣市: {'、'.join(a['counties']) or '—'}")
        print(f"  鄉鎮: {'、'.join(a['towns'][:12]) or '—'}{'…' if len(a['towns']) > 12 else ''}")
        print(f"  海岸: {'、'.join(a['coastal_counties']) or '—'}")
        print(f"  polygon: {len(a['polygon'])} ring / {rings} 點")
        print(f"  細胞廣播: {'ON' if a['cb_enabled'] else 'OFF'}")
        print(f"  description: {a['description'][:120]}")

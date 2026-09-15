"""人事行政總處（DGPA）停班停課 CAP feed：build 時本機抓取，產出首頁「停班停課」卡。

來源（2026/9/15 查證，免 key）：
- Atom feed：FEED_URL（alerts.ncdr.nat.gov.tw＝中央災害防救通信網 NCDR 災防警報平台託管；
  data.gov.tw 資料集 20457 正式公開、政府資料開放授權條款 v1）。
  內容＝「天然災害停止上班停止上課情形」，由各縣市政府經人事總處公告。
- 每筆 <entry> 統一結構（2026/9/15 實測 14 筆全同型）：a:id（CAP id，無 urn 前綴）、
  a:updated（ISO8601 公告/更新時間）、a:summary（通知原文）、a:link[@rel=alternate]
  （完整 CAP URL）、cap:effective／cap:expires（**中文 12 小時制**，如「2026/8/22 下午 02:10:00」；
  「上午 12 點」＝00:00）。CAP 抓取成功時以 ISO8601 覆蓋 feed 解析值，並補 areaDesc。

實測陷阱（2026/9/15）：
- feed 是**滾動近期視窗**，不是「目前生效中」清單——舊公告會留存數週，
  是否「目前仍相關」由 is_current() 以 expires/ sent 判斷，不可直接全顯示。
- feed 或單筆 CAP 可能 404/超時：該筆跳過＋warning，**不中斷 build**（同 cbph/RSS 慣例）。
- CAP <area><areaDesc> 是「縣市/鄉鎮」文字（如「屏東縣/恒春鎮/車城乡...」）；
  geocode 用 Taiwan_Geocode_103 縣市代碼（供未來地圖層使用）。

發布機制（官方，供卡面提示）：全日或上午停班須**前一日 19:00–22:00 前**發布；
下午或晚間停班**當日上午 10:30 前**發布。
"""
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from i18n import t

FEED_URL = "https://alerts.ncdr.nat.gov.tw/RssAtomFeed.ashx?AlertType=33"
QUERY_URL = "https://www.dgpa.gov.tw/typh/daily/nds.html"  # 2026/9/15 修正：apex（無 www）連線失敗，官方僅 www 可用
TIMEOUT = 30
_TZ = timezone(timedelta(hours=8))
_NS = {"a": "http://www.w3.org/2005/Atom",
        "cap": "urn:oasis:names:tc:emergency:cap:1.1"}  # feed 宣告於 <feed> 根元素


def _get(url):
    """curl 抓取（同 cwa._get_json 慣例：Python 3.14 OpenSSL 對部分政府站憑證鏈有問題）。"""
    p = subprocess.run(["curl", "-sL", "--max-time", str(TIMEOUT), url],
                       capture_output=True, text=True, timeout=TIMEOUT + 10)
    if p.returncode != 0:
        raise RuntimeError(f"curl 失敗（{p.returncode}）：{url}")
    return p.stdout


def _iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.strip())
    except ValueError:
        return None


_CN_TIME = re.compile(
    r"(\d{4})/(\d{1,2})/(\d{1,2})\s*(上午|下午)?\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(AM|PM)?")


def _cn_time(s):
    """feed 的 cap:effective/expires 用中文 12 小時制（如 '2026/8/23 上午 12:00:00'）。
    注意「上午 12 點」＝ 00:00（中午是「下午 12 點」）。CAP 抓不到時的 fallback。"""
    m = _CN_TIME.search(s or "")
    if not m:
        return None
    y, mo, d, ap, hh, mm, ss, ap2 = m.groups()
    hh = int(hh)
    ap = ap or ("上午" if (ap2 or "").upper() == "AM" else "下午" if (ap2 or "").upper() == "PM" else "")
    if ap == "下午" and hh < 12:
        hh += 12
    elif ap == "上午" and hh == 12:
        hh = 0
    return datetime(int(y), int(mo), int(d), hh, int(mm), int(ss or 0), tzinfo=_TZ)


def fetch(now=None):
    """抓 feed＋每筆完整 CAP，回傳 (entries, ok, ts_str)。

    entries: [{id, sent, effective, expires, area, text, cap_url}]
    ok=False＝feed 本身抓不到（呼叫端不顯示卡）；單筆 CAP 失敗只影響該筆。
    """
    now = now or datetime.now(_TZ)
    ts_str = now.strftime("%Y/%-m/%-d %H:%M")
    body = _get(FEED_URL)
    root = ET.fromstring(body)
    entries = []
    for e in root.findall("a:entry", _NS):
        def txt(tag):
            return (e.findtext(tag, "", _NS) or "").strip()
        cap_id = txt("a:id")  # feed 用 Atom id 欄放 CAP id（無 urn: 前綴）
        link_el = e.find("a:link[@rel='alternate']", _NS)
        cap_url = link_el.get("href") if link_el is not None else None
        if not cap_id or not cap_url:
            continue
        text = re.sub(r"\s+", " ", txt("a:summary") or txt("a:title"))
        sent = _iso(txt("a:updated")) or _iso(txt("a:published"))
        entry = {"id": cap_id, "sent": sent,
                 "effective": _cn_time(txt("cap:effective")),  # feed 中文格式先解析（fallback）
                 "expires": _cn_time(txt("cap:expires")),
                 "area": "", "text": text, "cap_url": cap_url}
        # 完整 CAP：ISO8601 時間覆蓋 feed 解析值＋影響區域 areaDesc（供未來地圖層）
        try:
            cap_root = ET.fromstring(_get(cap_url))
            info = cap_root.find("info")
            if info is not None:
                entry["effective"] = _iso((info.findtext("effective") or "").strip()) or entry["effective"]
                entry["expires"] = _iso((info.findtext("expires") or "").strip()) or entry["expires"]
                areas = "、".join((a.text or "").strip() for a in info.findall("area/areaDesc")
                                  if (a.text or "").strip())
                entry["area"] = areas
        except Exception as exc:  # 單筆 CAP 失敗：保留 feed 解析值（同為官方資料）
            print(f"warning: DGPA CAP 抓取失敗（{cap_id}）：{exc}")
        entries.append(entry)
    return entries, True, ts_str


def is_current(e, now=None):
    """該公告目前是否仍相關：影響日（expires）為今天或之後，或公告（sent）不超過 24 小時。

    ⚠️ CAP 的 effective≈公告時間、expires≈「影響日 00:00」（全日停班＝影響日午夜；
    半日停班＝當日晚間）——影響日当天 expires 剛好是午夜，故用「expires >= 今天 0 時」
    而非「expires >= now」，才能涵蓋影響日全天。
    """
    now = now or datetime.now(_TZ)
    today0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
    exp, sent = e.get("expires"), e.get("sent")
    if exp is not None:
        if exp >= today0:
            return True
    if sent is not None and (now - sent) <= timedelta(hours=24):
        return True
    return False


def _fmt(dt):
    return dt.strftime("%-m/%-d %H:%M") if dt else ""


def render_card(lang, susp, now=None):
    """「停班停課」卡。susp = fetch() 的 (entries, ok, ts)；None（抓取失敗）→ 不顯示。

    - 有 currently 相關公告 → 展開卡（呼叫端置於颱風卡之上）
    - 無 → 收起卡（呼叫端置於卡片區底部）
    """
    if susp is None:
        return ""
    entries, ok, ts = susp
    if not ok:
        return ""
    now = now or datetime.now(_TZ)
    cur = [e for e in entries if is_current(e, now)]
    src = f'{t(lang, "susp_source")}　<a href="{QUERY_URL}" target="_blank" rel="noopener">{t(lang, "susp_page")}</a>'
    if not cur:
        return f"""
<div class="card susp-card collapsed">
<p class="muted">{t(lang, "susp_none")}　<span class="meta">{t(lang, "susp_asof", ts=ts)}　{src}</span></p>
</div>"""
    lis = []
    for e in cur:
        when = t(lang, "susp_window", a=_fmt(e.get("effective")), b=_fmt(e.get("expires")))
        sent = t(lang, "susp_sent", ts=_fmt(e.get("sent"))) if e.get("sent") else ""
        lis.append(f"""<li>
<p style="margin:2px 0">{e['text']}</p>
<p class="meta">{when}　{sent}　<a href="{e['cap_url']}" target="_blank" rel="noopener">{t(lang, "susp_cap")}</a></p>
</li>""")
    return f"""
<div class="card cwa-card susp-card">
<h3>{t(lang, "susp_title")}　<span class="chip">{t(lang, "susp_count", n=len(cur))}</span></h3>
<ul class="susp-list">{''.join(lis)}</ul>
<p class="meta">{t(lang, "susp_note", ts=ts)}<br>{src}</p>
</div>"""

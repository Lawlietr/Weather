#!/usr/bin/env python3
"""RSS 災情候選清單產出（半自動方案；見 TODO.md §1）。

流程：讀 rss_sources.json → 批次抓取所有 verified 來源（勿呼叫 failed_sources）
→ 去重＋時間過濾＋關鍵詞初判 → 產出 rss_candidates.json。

原則（與 AGENTS.md「災情新聞人工把關」一致）：
- 程式**只負責抓取＋結構化＋初判**（時間過濾、關鍵詞 flag），**不判定相關性**。
- 相關性／縣市歸類由人 / LLM 審查 rss_candidates.json 後，
  挑中者寫入事件 markdown 的「災情新聞來源」區塊（build 會自動渲染）。
- 單一來源 404/超時**不中斷 build**：跳過＋記 warning（沿用 CWA 失敗降級設計）。

用法：python rss.py（由 build.sh 呼叫；失敗不影響 site.py）
環境變數：RSS_LOOKBACK_HOURS（時間過濾窗口，預設 48 小時）
"""
import html
import json
import os
import re
import subprocess
import sys
import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
SOURCES_FILE = HERE / "rss_sources.json"
OUT_FILE = HERE / "rss_candidates.json"
TIMEOUT = 20          # 單 feed 秒
MAX_ITEMS_PER_FEED = 30
LOOKBACK_HOURS = int(os.getenv("RSS_LOOKBACK_HOURS", "48"))
TZ_TW = datetime.timezone(datetime.timedelta(hours=8))

# 關鍵詞初判：命中僅為 flag（供審查者優先看），不做過濾
KEYWORDS = [
    "颱風", "豪雨", "豪大雨", "大雨", "暴雨", "強風", "狂風", "陣風",
    "淹水", "積水", "洪水", "土石流", "崩坡", "落石", "樹倒", "斷樹", "電線",
    "停電", "斷電", "停水", "停課", "停班", "封路", "封閉",
    "浪高", "storm surge", "暴潮", "高潮位", "雷擊", "閃電",
    "疏散", "避難", "撤離", "災情", "搶修", "救災", "應變", "水患",
]


def fetch(url: str) -> bytes:
    """用 curl 抓（與 cwa.py 一致：Python 3.14 OpenSSL 對部分憑證鏈有問題）。
    回傳 bytes（可能含 BOM）；失敗回傳 None。"""
    p = subprocess.run(
        ["curl", "-s", "--max-time", str(TIMEOUT), "-L", url],
        capture_output=True, timeout=TIMEOUT + 10,
    )
    if p.returncode != 0 or not p.stdout:
        return None
    return p.stdout


def strip_html(text: str, limit: int = 200) -> str:
    """去 HTML tag、解 entity、壓縮空白，截斷到 limit 字。"""
    if not text:
        return ""
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit]


def parse_date(s: str):
    """解析 RSS 2.0（RFC 822）或 Atom（ISO 8601）日期；失敗回 None。"""
    if not s:
        return None
    s = s.strip()
    try:
        dt = parsedate_to_datetime(s)  # RFC 822
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ_TW)
        return dt
    except (TypeError, ValueError, IndexError):
        pass
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_feed(raw: bytes, fmt: str):
    """回傳 [(title, link, published_dt, summary), ...]。解析失敗丟異常。"""
    # utf-8-sig 處理 LTN 檔頭 BOM
    root = ET.fromstring(raw.decode("utf-8-sig", errors="replace"))
    items = []
    if fmt == "atom":
        ns = re.match(r"^\{(.+)\}", root.tag).group(1) if root.tag.startswith("{") else ""
        for e in root.findall(f"{{{ns}}}entry"):
            title = (e.findtext(f"{{{ns}}}title") or "").strip()
            link_el = e.find(f"{{{ns}}}link[@rel='alternate']")
            if link_el is None:
                link_el = e.find(f"{{{ns}}}link")
            link = (link_el.get("href") if link_el is not None else "").strip()
            pub = parse_date(e.findtext(f"{{{ns}}}published") or e.findtext(f"{{{ns}}}updated") or "")
            summ = strip_html(e.findtext(f"{{{ns}}}summary") or e.findtext(f"{{{ns}}}content") or "")
            if title and link:
                items.append((title, link, pub, summ))
    else:  # rss20
        for e in root.iter("item"):
            title = (e.findtext("title") or "").strip()
            link = (e.findtext("link") or "").strip()
            pub = parse_date(e.findtext("pubDate") or e.findtext("dc:date") or "")
            summ = strip_html(e.findtext("description") or "")
            if title and link:
                items.append((title, link, pub, summ))
    return items


def main():
    cfg = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    now = datetime.datetime.now(TZ_TW)
    cutoff = now - datetime.timedelta(hours=LOOKBACK_HOURS)

    seen_url = set()      # 跨來源同 URL 去重
    seen_title = set()     # 同來源同標題去重（同一則新聞常出現在多家 feed 的多個分類，URL 可能不同）
    candidates = []
    feeds = []
    warnings = []

    for src in cfg.get("sources", []):
        for u in src.get("urls", []):
            url, category = u["url"], u.get("category", "")
            n = 0
            try:
                raw = fetch(url)
                if raw is None:
                    raise RuntimeError(f"curl 失敗（returncode 非 0 或空回應）")
                head = raw[:200].lstrip(b"\xef\xbb\xbf")
                if b"<" not in head:
                    raise RuntimeError(f"非 XML 內容（前 200 字：{head[:60]!r}）")
                for title, link, pub, summ in parse_feed(raw, src.get("format", "rss20")):
                    if n >= MAX_ITEMS_PER_FEED:
                        break
                    n += 1
                    if link.rstrip("/").lower() in seen_url:
                        continue
                    norm_title = re.sub(r"\s+", "", html.unescape(strip_html(title)))
                    if (src["name"], norm_title) in seen_title:
                        continue
                    seen_url.add(link.rstrip("/").lower())
                    seen_title.add((src["name"], norm_title))
                    # 時間過濾：無日期者不收（避免舊聞）；只看窗口內
                    if pub is None or pub.astimezone(TZ_TW) < cutoff:
                        continue
                    text = title + " " + summ
                    kw = [k for k in KEYWORDS if k in text]
                    candidates.append({
                        "title": title,
                        "url": link,
                        "source": src["name"],
                        "category": category,
                        "published": pub.astimezone(TZ_TW).strftime("%Y/%-m/%-d %H:%M"),
                        "flag": bool(kw),
                        "keywords": kw,
                        "summary": summ,
                    })
                feeds.append({"source": src["name"], "category": category, "url": url,
                              "status": "ok", "items": n})
            except Exception as ex:  # 單一來源失敗不中斷（跳過＋記 warning）
                msg = f"{src['name']}（{category}）{url}: {ex}"
                warnings.append(msg)
                feeds.append({"source": src["name"], "category": category, "url": url,
                              "status": "error", "error": str(ex)})
                print(f"warning: {msg}")

    # 排序：先時間倒序，再穩定地按 flag 分組（flag 在前，組內維持時間倒序）
    candidates.sort(key=lambda c: c["published"], reverse=True)
    candidates.sort(key=lambda c: not c["flag"])
    out = {
        "$note": "RSS 災情候選清單（半自動）：build 自動抓取＋結構化＋關鍵詞初判，相關性須人工/LLM 審查後才寫入事件 markdown 的『災情新聞來源』區塊。flag 僅為關鍵詞初判。",
        "generated_at": now.strftime("%Y/%-m/%-d %H:%M"),
        "lookback_hours": LOOKBACK_HOURS,
        "total": len(candidates),
        "flagged": sum(1 for c in candidates if c["flag"]),
        "feeds": feeds,
        "warnings": warnings,
        "candidates": candidates,
    }
    OUT_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"RSS 候選清單：{len(candidates)} 則（關鍵詞命中 {out['flagged']}）｜"
          f"feeds ok {sum(1 for f in feeds if f['status'] == 'ok')}/{len(feeds)}"
          + (f"｜warning {len(warnings)}" if warnings else "")
          + f" → {OUT_FILE.name}")


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:  # RSS 失敗不影響後續 site.py
        print(f"warning: RSS 候選清單產出失敗（不影響 build）：{ex}")
        sys.exit(0)

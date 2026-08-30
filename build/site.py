#!/usr/bin/env python3
"""災情與氣象彙整網站 build 腳本（事件為中心；CWA 氣象總覽 build 時本機抓取，見 cwa.py）。

用法：./build.sh（自動建 venv 並裝 python-markdown）
輸出：public/（純靜態 HTML，可部署於 GitHub Pages / Cloudflare Pages）

相容性原則（GitHub Pages + Cloudflare Pages 通用）：
- 所有連結一律「相對路徑」（不用 / 起頭），兩個平台子路徑/自訂網域都正確。
- 純靜態 HTML，僅一小段 inline JS（日夜主題 + 手機側欄），無外部資源、無 service worker。
- 日夜主題預設黑夜；偏好寫入 localStorage（key: wtf-theme）。
"""
import re
import sys
import datetime
from pathlib import Path

import cwa
from urllib.parse import quote

import i18n
from i18n import t, LANGS, DEFAULT_LANG

try:
    import markdown
except ImportError:
    sys.exit("缺少 python-markdown。請改用 ./build.sh 執行（自動建 venv）。")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "public"
SRC_DIRS = [ROOT / "災情", ROOT / "颱風"]

COUNTIES = [
    "台北市", "新北市", "桃園市", "台中市", "台南市", "高雄市",
    "基隆市", "新竹市", "嘉義市", "新竹縣", "苗栗縣", "彰化縣",
    "南投縣", "雲林縣", "嘉義縣", "屏東縣", "宜蘭縣", "花蓮縣",
    "台東縣", "澎湖縣", "金門縣", "連江縣",
    # 別名 → 正式縣名（地點欄常用簡稱）
]
COUNTY_ALIAS = {
    "台北": "台北市", "新北": "新北市", "淡水": "新北市", "八里": "新北市",
    "三重": "新北市", "中和": "新北市", "烏來": "新北市", "三峽": "新北市",
    "大台北": "台北市", "台中": "台中市", "台南": "台南市", "高雄": "高雄市",
    "桃園": "桃園市", "基隆": "基隆市", "新竹": "新竹市", "苗栗": "苗栗縣",
    "彰化": "彰化縣", "南投": "南投縣", "雲林": "雲林縣", "嘉義": "嘉義縣",
    "屏東": "屏東縣", "恆春": "屏東縣", "宜蘭": "宜蘭縣", "花蓮": "花蓮縣",
    "台東": "台東縣", "東東": "台東縣", "澎湖": "澎湖縣", "金門": "金門縣",
    "馬祖": "連江縣", "連江": "連江縣",
    "蘭嶼": "台東縣", "龜山島": "新北市", "東港": "屏東縣",
    "枋寮": "屏東縣", "萬丹": "屏東縣", "新園": "屏東縣", "舊泰武": "屏東縣",
}
SEV_KEY = {"red": ("sev_red", "sev-red"), "yellow": ("sev_yellow", "sev-yellow"), "green": ("sev_green", "sev-green")}

# GitHub 倉庫網址（顯示於首頁右上角 icon）
GITHUB_URL = "https://github.com/Lawlietr/Weather"

GITHUB_ICON_SVG = ('<svg viewBox="0 0 16 16" width="20" height="20" fill="currentColor" aria-hidden="true">'
                   '<path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg>')

# 雙主題：預設黑夜；[data-theme="light"] 為琥珀色淺色主題（非純白）
CSS = """
:root{--red:#ef5350;--yellow:#ffb300;--green:#66bb6a;
--bg:#14181c;--card:#1d242c;--line:#2f3944;--ink:#e4e8ec;--muted:#98a3af;
--accent:#64b5f6;--chip-bg:#2a333e;--side-bg:#0f1317;--side-ink:#c9d1d9;
--head-bg:#0c0f12;--table-head:#252e38;--ph-bg:#241f12;--ph-line:#6e5a1e;--ph-ink:#d3bd7d;
color-scheme:dark;}
:root[data-theme="light"]{--red:#c62828;--yellow:#ef8f00;--green:#2e7d32;
--bg:#fff6dd;--card:#fffdf4;--line:#e6d7ae;--ink:#33280f;--muted:#7d6c48;
--accent:#a05e00;--chip-bg:#f5e8c3;--side-bg:#fbf1d4;--side-ink:#4d3f22;
--head-bg:#263238;--table-head:#f7edd0;--ph-bg:#fff8e1;--ph-line:#c9a227;--ph-ink:#6d5410;
color-scheme:light;}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Noto Sans TC","PingFang TC","Microsoft JhengHei","Hiragino Kaku Gothic ProN","Hiragino Sans","Noto Sans JP","Yu Gothic","Meiryo",sans-serif;color:var(--ink);background:var(--bg);line-height:1.7;font-size:16px}
/* 版面：左側欄 + 右側內容（內容置中） */
.layout{display:grid;grid-template-columns:250px minmax(0,1fr);min-height:100vh}
.sidebar{background:var(--side-bg);border-right:1px solid var(--line);position:sticky;top:0;height:100vh;overflow-y:auto;padding:16px 10px}
.nav-group{font-size:.72rem;letter-spacing:.1em;color:var(--muted);margin:18px 10px 6px}
.nav-item{display:flex;align-items:flex-start;gap:8px;padding:8px 10px;border-radius:8px;color:var(--side-ink);font-size:.88rem;line-height:1.45}
.nav-item:hover{background:var(--chip-bg);text-decoration:none}
.nav-item.nav-current{background:var(--chip-bg);color:var(--ink);font-weight:700}
/* 側欄二層收合清單（純 CSS details/summary） */
.nav-sub{margin:0}
.nav-sub summary{display:flex;align-items:center;gap:2px;list-style:none;cursor:pointer}
.nav-sub summary::-webkit-details-marker{display:none}
.nav-sub summary:hover .nav-item{background:var(--chip-bg)}
.nav-sub .caret{flex:none;font-size:.7rem;color:var(--muted);transition:transform .15s;margin:0 0 0 4px}
.nav-sub[open] .caret{transform:rotate(90deg)}
.nav-counties{margin:2px 0 6px 16px;border-left:1px solid var(--line);padding-left:4px}
.nav-counties .nav-subitem{font-size:.8rem;padding:5px 8px}
.dot{width:9px;height:9px;border-radius:50%;flex:none;margin-top:6px}
.dot-red{background:var(--red)}.dot-yellow{background:var(--yellow)}.dot-green{background:var(--green)}
.page{display:flex;flex-direction:column;min-width:0}
header.site{background:var(--head-bg);color:#fff;padding:10px 0;position:sticky;top:0;z-index:40}
.site-bar{max-width:900px;margin:0 auto;padding:2px 16px;display:flex;align-items:center;gap:8px}
.site-bar.updated-bar{justify-content:flex-end}
header.site h1{font-size:1.1rem;margin:0;flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.updated{color:#b0bec5;font-size:.8rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.icon-btn{background:none;border:none;border-radius:8px;color:inherit;padding:6px;display:inline-flex;cursor:pointer;line-height:0;flex:none}
.icon-btn:hover{background:rgba(255,255,255,.15)}
.lang-switch{display:inline-flex;gap:2px;flex:none}
.lang-switch a,.lang-switch .on{padding:2px 9px;border-radius:6px;font-size:.78rem;line-height:1.6}
.lang-switch a{color:#b0bec5}
.lang-switch a:hover{text-decoration:none;background:rgba(255,255,255,.15)}
.lang-switch .on{background:rgba(255,255,255,.18);color:#fff;font-weight:700}
#nav-toggle{display:none}
[data-theme="dark"] .icon-moon{display:none}
[data-theme="light"] .icon-sun{display:none}
main.wrap{flex:1;width:100%;max-width:900px;margin:0 auto;padding:16px}
section{margin:28px 0}
h2{font-size:1.15rem;border-bottom:2px solid var(--line);padding-bottom:6px}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px;margin:12px 0}
/* hero：正常卡片底色 + 實色邊框（不填色），依嚴重度著色 */
.hero{border:2px solid var(--line)}
.hero.sev-red{border-color:var(--red)}
.hero.sev-yellow{border-color:var(--yellow)}
.hero.sev-green{border-color:var(--green)}
.hero h2{font-size:1.45rem;font-weight:800;line-height:1.45;margin-top:0}
.hero h2 a{color:var(--ink)}
.hero h2 a:hover{color:var(--accent)}
.hero .meta{color:var(--muted);font-size:.9rem}
.hero-cta{display:inline-block;margin-top:16px;padding:8px 20px;border-radius:8px;background:var(--accent);color:var(--head-bg);font-size:.95rem;font-weight:700;text-decoration:none}
.hero-cta:hover{filter:brightness(1.15);text-decoration:underline}
/* 徽章：實心色塊小標籤（severity 背景色只限徽章，不污染卡片） */
.badge{display:inline-block;padding:3px 12px;border-radius:12px;font-size:.85rem;font-weight:700;vertical-align:middle}
.badge.sev-red{background:var(--red);color:#fff}
.badge.sev-yellow{background:var(--yellow);color:#3e2723}
.badge.sev-green{background:var(--green);color:#fff}
.badge.sev-grey{background:#9e9e9e;color:#fff}
.chips{margin:10px 0}
.chip{display:inline-block;background:var(--chip-bg);border-radius:14px;padding:2px 12px;margin:2px 4px 2px 0;font-size:.85rem}
.chip-link{color:var(--accent);text-decoration:none}
.chip-link:hover{text-decoration:underline}
.county-card{scroll-margin-top:88px}
.meta{color:var(--muted);font-size:.85rem}
table{border-collapse:collapse;width:100%;margin:10px 0;font-size:.9rem;background:var(--card)}
th,td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}
th{background:var(--table-head)}
ul.timeline{list-style:none;padding:0;margin:8px 0}
ul.timeline li{padding:8px 0;border-bottom:1px dashed var(--line)}
ul.timeline li:last-child{border-bottom:none}
ul.news-list{list-style:none;margin:6px 0 0;padding-left:4px}
ul.news-list li{padding:2px 0;font-size:.85rem}
ul.news-list li a{word-break:break-all}
.t-time{font-weight:700}
.t-type{color:var(--accent);font-weight:600}
.muted{color:var(--muted)}
.placeholder{background:var(--ph-bg);border:1px dashed var(--ph-line);border-radius:10px;padding:14px;color:var(--ph-ink)}
/* CWA 氣象總覽 */
.cwa-warn{background:var(--chip-bg);border:1px solid var(--yellow);border-radius:8px;padding:10px 14px;margin:8px 0}
.cwa-fail{border-color:var(--yellow)}
/* 目前風險狀態列：由 CWA 目前之警報/特報推導（與事件歷史 severity 無關） */
.risk-bar{border:2px solid var(--line);border-radius:10px;padding:12px 18px;margin:14px 0;background:var(--card)}
.risk-bar.risk-red{border-color:var(--red);background:var(--red-bg)}
.risk-bar.risk-yellow{border-color:var(--yellow);background:var(--yellow-bg)}
.risk-bar.risk-green{border-color:var(--green)}
.risk-bar.risk-unknown{border-style:dashed}
.risk-bar .risk-label{font-weight:800;font-size:1rem}
.risk-bar ul{list-style:none;margin:6px 0 0;padding:0}
.risk-bar li{padding:2px 0;font-size:.95rem}
.typhoon-row{display:flex;gap:18px;align-items:flex-start;margin:10px 0}
.typhoon-row .map{flex:0 0 340px;max-width:46%}
.typhoon-row .map svg{width:100%;height:auto;display:block;border:1px solid var(--line);border-radius:8px;background:var(--bg)}
.typhoon-row .typhoon-info{flex:1;min-width:0}
.typhoon-row .typhoon-info table{font-size:.85rem}
.alert-item{padding:10px 0;border-bottom:1px dashed var(--line)}
.alert-item:last-child{border-bottom:none}
.report-text{white-space:pre-wrap;font-size:.85rem;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:10px;margin:8px 0 0}
@media(max-width:767px){.typhoon-row{flex-direction:column}.typhoon-row .map{max-width:100%;flex-basis:auto}}
.event-content{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:20px;overflow-x:auto}
.event-content h1{font-size:1.3rem}
.event-content h2{border-bottom:1px solid var(--line)}
.event-content blockquote{border-left:4px solid var(--accent);margin:12px 0;padding:4px 14px;background:var(--chip-bg)}
.event-content img{max-width:100%}
.archive-list{list-style:none;padding:0}
.archive-list li{padding:10px 0;border-bottom:1px solid var(--line)}
footer{background:var(--head-bg);color:#cfd8dc;padding:20px 0;font-size:.85rem;margin-top:40px}
footer .wrap{max-width:900px;margin:0 auto;padding:0 16px}
.backlink{display:inline-block;margin-bottom:10px}
.scrim{display:none}
/* 平板與手機（<1024px）：側欄改為抽屜式 */
@media (max-width:1023px){
.layout{display:block}
.sidebar{position:fixed;left:0;top:0;bottom:0;width:280px;transform:translateX(-100%);transition:transform .25s ease;z-index:60;box-shadow:0 0 30px rgba(0,0,0,.45)}
.sidebar.open{transform:translateX(0)}
#nav-toggle{display:inline-flex}
.scrim{display:block;position:fixed;inset:0;background:rgba(0,0,0,.5);opacity:0;pointer-events:none;transition:opacity .25s;z-index:55}
.scrim.show{opacity:1;pointer-events:auto}
main.wrap{padding:12px}
section{margin:20px 0}
.card{padding:14px}
.t-time{white-space:normal}
}
@media print{
.sidebar,#scrim,.icon-btn{display:none}
.layout{display:block}
header.site,footer{background:none;color:#000}
.card,.event-content{border-color:#999;break-inside:avoid}
a::after{content:" (" attr(href) ")";font-size:.75em;color:#555}
}
"""

# inline JS：日夜主題切換（寫入 localStorage）+ 手機側欄開關
JS = """
(function(){
  var root = document.documentElement;
  var themeBtn = document.getElementById('theme-toggle');
  if (themeBtn) themeBtn.addEventListener('click', function(){
    var t = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', t);
    try { localStorage.setItem('wtf-theme', t); } catch (e) {}
  });
  var sb = document.getElementById('sidebar'),
      sc = document.getElementById('scrim'),
      hb = document.getElementById('nav-toggle');
  function close(){ if(sb) sb.classList.remove('open'); if(sc) sc.classList.remove('show'); }
  if (hb) hb.addEventListener('click', function(){
    sb.classList.toggle('open'); sc.classList.toggle('show');
  });
  if (sc) sc.addEventListener('click', close);
  if (sb) sb.querySelectorAll('a').forEach(function(a){ a.addEventListener('click', close); });
})();
"""


def parse_front_matter(text: str):
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            fm = {}
            for line in text[3:end].strip().splitlines():
                if ":" not in line:
                    continue
                k, v = line.split(":", 1)
                k, v = k.strip(), v.strip()
                if v.startswith("[") and v.endswith("]"):
                    fm[k] = [x.strip() for x in v[1:-1].split(",") if x.strip()]
                else:
                    fm[k] = v
            return fm, text[end + 4:].lstrip("\n")
    return {}, text


def dedupe_last_modified(body: str) -> str:
    """檔首只顯示最新一筆「最後修改：」。
    舊慣例是「每次修改新增一筆」，會使檔首堆疊多行並全數渲染到事件頁；
    此處只處理檔首連續的該類行（保留第一行＝最新），正文其餘位置不受影響。
    新慣例為原地更新單行（見 AGENTS.md），此函式僅為防線。"""
    lines = body.splitlines()
    block = 0
    while block < len(lines) and re.match(r"^\s*最後修改：", lines[block]):
        block += 1
    if block > 1:
        lines = [lines[0], *lines[block:]]
    return "\n".join(lines)


def extract_news_by_county(body: str):
    """解析「### XX災情新聞來源」章節的 markdown 連結，回傳 {縣名: [(標題, URL, 媒體), ...]}。
    標題與媒體相同時以連結文字為準；行格式：- [標題](URL) — 媒體名"""
    news = {}
    section = None
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("#"):
            title = s.lstrip("#").strip()
            section = title if title.endswith("新聞來源") else None
            if section:
                m = re.match(r"(.+?)災情?新聞來源", title)
                if m:
                    name = m.group(1)
                    c = next((x for x in COUNTIES if x in name), None)
                    section = c or ""
            continue
        if not section:
            continue
        m = re.match(r"\s*[-+]+\s*\[([^\]]+)\]\((https?://[^)\s]+)\)\s*(?:—|–|-)\s*([^\s\-–—][^—–-]*)$", s)
        if m:
            news.setdefault(section, []).append((m.group(1), m.group(2), m.group(3).strip()))
    return news


def extract_table_rows(body: str):
    """提取所有「日期時間|地點|類型|說明」表格的行，並記錄所在章節標題。"""
    rows = []
    section = ""
    county_section = ""  # 最近一個含縣名的標題（外層 ## 不會被 ### 蓋掉）
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if line.startswith("#"):
            section = line.lstrip("#").strip()
            if any(c in section for c in COUNTIES):
                county_section = section
            i += 1
            continue
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 4 and ("日期" in cells[0] or "時間" in cells[0]) and "地點" in cells[1]:
                i += 1
                while i < len(lines) and lines[i].strip().startswith("|"):
                    cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                    i += 1
                    if len(cells) < 4 or all(re.fullmatch(r":?-{2,}:?", c or "----") for c in cells):
                        continue
                    rows.append({"time": cells[0], "place": cells[1], "type": cells[2], "desc": cells[3],
                                "section": section, "county_section": county_section})
                continue
        i += 1
    return rows


def find_county(row):
    if "中國" in row["place"] or "中國" in row["section"]:
        return "中國大陸"
    for c in COUNTIES:
        if c in row.get("county_section", ""):
            return c
    for c in COUNTIES:
        if c in row["section"]:
            return c
    text = row["place"]
    for alias, county in COUNTY_ALIAS.items():
        if alias in text:
            return county
    for c in COUNTIES:
        if c in text:
            return c
    return None


def load_events():
    events = []
    for d in SRC_DIRS:
        if not d.exists():
            continue
        for p in sorted(d.rglob("*.md")):
            text = p.read_text(encoding="utf-8")
            fm, body = parse_front_matter(text)
            if not fm:
                continue
            body = dedupe_last_modified(body)
            events.append({
                "path": p,
                "rel": ["events", *p.relative_to(ROOT).with_suffix(".html").parts],  # 磁碟路徑（原始中文）
                "url": ["events"] + [quote(s) for s in p.relative_to(ROOT).with_suffix(".html").parts],  # 網頁連結
                "name": fm.get("event", p.stem),
                "status": fm.get("status", "ended"),
                "severity": fm.get("severity", "green"),
                "counties": fm.get("counties", []),
                "period": fm.get("period", ""),
                "summary": fm.get("summary", ""),
                "sources": fm.get("sources", []),
                "mtime": p.stat().st_mtime,
                "rows": extract_table_rows(body),
                "news": extract_news_by_county(body),  # 先暫存，稍後掛到對應行
                "body": body,
            })
            for r in events[-1]["rows"]:
                c = find_county(r)
                if c in events[-1]["news"]:
                    r["news"] = events[-1]["news"][c]
    events.sort(key=lambda e: e["mtime"], reverse=True)
    return events


# 用 __X__ 佔位符 + replace，避免 CSS/JS 大括號與 format 衝突
PAGE_TMPL = """<!DOCTYPE html>
<html lang="__LANG__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>__CSS__</style>
<script>/* 避免閃爍：先還原主題偏好再渲染 */(function(){var t=null;try{t=localStorage.getItem("wtf-theme")}catch(e){}if(t!=="light"&&t!=="dark")t="dark";document.documentElement.setAttribute("data-theme",t);})();</script>
</head>
<body id="top">
<div class="layout">
<aside class="sidebar" id="sidebar">
__NAV__
</aside>
<div class="scrim" id="scrim"></div>
<div class="page">
<header class="site">
<div class="site-bar">
<button id="nav-toggle" class="icon-btn" aria-label="開啟事件清單"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M3 6h18M3 12h18M3 18h18"/></svg></button>
<h1><a href="__HOME_LINK__" style="color:#fff;text-decoration:none">__TITLE__</a></h1>
<span class="lang-switch">__LANG_SWITCH__</span>
__GITHUB__
<button id="theme-toggle" class="icon-btn" aria-label="切換日夜主題">
<svg class="icon-sun" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="5"/><path d="M12 1v2m0 18v2M4.2 4.2l1.4 1.4m12.8 12.8 1.4 1.4M1 12h2m18 0h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"/></svg>
<svg class="icon-moon" viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>
</button>
</div>
<div class="site-bar updated-bar"><span class="updated">__UPDATED__</span></div>
</header>
<main class="wrap">
__CONTENT__
</main>
<footer><div class="wrap">
<p>__FOOTER__</p>
</div></footer>
</div>
</div>
<script>__JS__</script>
</body>
</html>"""


def github_icon_html(lang):
    # 右上角 GitHub icon。GITHUB_URL 非空時為可點擊連結，並顯示。
    if GITHUB_URL:
        return (f'<a class="icon-btn" href="{GITHUB_URL}" target="_blank" rel="noopener" '
                f'title="GitHub" aria-label="GitHub">{GITHUB_ICON_SVG}</a>')
    return f'<span class="icon-btn" title="{t(lang, "github_pending")}" aria-label="GitHub">{GITHUB_ICON_SVG}</span>'


def lang_switch_html(lang, home_link):
    """語言切換：目前語言顯示實心標籤，其餘為連結（跳回該語言首頁）。"""
    # home_link = 目前頁 → 目前語言根頁；base_root = 目前語言根目錄前綴
    base_root = home_link[: -len("index.html")] if home_link.endswith("index.html") else home_link
    items = []
    for l in LANGS:
        label = t(l, "lang_self")
        if l == lang:
            items.append(f'<span class="on">{label}</span>')
        elif l == DEFAULT_LANG:
            # 預設語言在根目錄；非預設語言頁需多上一層（ja/ 是根目錄子目錄）
            href = base_root + ("index.html" if i18n.is_default(lang) else "../index.html")
        else:
            href = base_root + f"{l}/index.html"
        if l != lang:
            items.append(f'<a href="{href}">{label}</a>')
    return "".join(items)


def build_nav(lang, events, home_link, base, current_url, groups):
    """左側事件導覽。base：從目前頁到根目錄的前綴（首頁為空字串）；
    groups：首頁「各縣市災情」的縣名集合（決定 side bar 二層清單的錨點是否有效）。"""
    parts = ['<nav>']
    cls = " nav-current" if current_url == "__home__" else ""
    parts.append(f'<a class="nav-item{cls}" href="{home_link}">{t(lang, "nav_home")}</a>')

    def item(e):
        cls = " nav-current" if current_url == "/".join(e["url"]) else ""
        return (f'<a class="nav-item{cls}" href="{base}{"/".join(e["url"])}">'
                f'<span class="dot dot-{e["severity"]}"></span><span>{e["name"]}</span></a>')

    def county_sublist(counties):
        """事件下二層縣市清單：有對應首頁區塊者為錨點連結，否則純文字。"""
        items = []
        for c in counties:
            if c in groups:
                href = f'{base}index.html#{quote(c, safe="")}'
                items.append(f'<a class="nav-item nav-subitem" href="{href}">{c}</a>')
            else:
                items.append(f'<span class="nav-item nav-subitem muted" title="{t(lang, "nav_no_county")}">{c}</span>')
        return f'<div class="nav-counties">{"".join(items)}</div>'

    active = [e for e in events if e["status"] == "active"]
    ended = [e for e in events if e["status"] != "active"]
    if active:
        parts.append(f'<div class="nav-group">{t(lang, "nav_active")}</div>')
        # 主 active 事件（與首頁 hero 一致）加二層收合的縣市清單
        if active[0].get("counties"):
            e = active[0]
            cls = " nav-current" if current_url == "/".join(e["url"]) else ""
            link = (f'<a class="nav-item{cls}" href="{base}{"/".join(e["url"])}">'
                    f'<span class="dot dot-{e["severity"]}"></span><span>{e["name"]}</span></a>')
            parts.append(f'<details class="nav-sub" open><summary><span class="caret" aria-hidden="true">▸</span>{link}</summary>'
                         f'{county_sublist(e["counties"])}</details>')
            parts += [item(x) for x in active[1:]]
        else:
            parts += [item(e) for e in active]
    if ended:
        parts.append(f'<div class="nav-group">{t(lang, "nav_ended")}</div>')
        parts += [item(e) for e in ended]
    parts.append('</nav>')
    return "".join(parts)


def render_page(lang, title, ts, home_link, nav_html, content):
    page = PAGE_TMPL
    for k, v in (("__LANG__", lang), ("__TITLE__", title), ("__HOME_LINK__", home_link),
                 ("__UPDATED__", t(lang, "updated", ts=ts)),
                 ("__LANG_SWITCH__", lang_switch_html(lang, home_link)),
                 ("__GITHUB__", github_icon_html(lang)), ("__NAV__", nav_html),
                 ("__FOOTER__", t(lang, "footer")),
                 ("__CSS__", CSS), ("__JS__", JS), ("__CONTENT__", content)):
        page = page.replace(k, v)
    return page


def badge(lang, sev):
    key, cls = SEV_KEY.get(sev, SEV_KEY["green"])
    return f'<span class="badge {cls}">{t(lang, key)}</span>'


def inline_html(text):
    """渲染表格單格內的行內 markdown（粗體、連結等）。"""
    h = markdown.markdown(text, extensions=["tables"])
    h = re.sub(r"^<p>", "", h)
    h = re.sub(r"</p>$", "", h)
    return h


def row_html(row):
    return (f'<li><span class="t-time">{inline_html(row["time"])}</span>｜{inline_html(row["place"])}｜'
            f'<span class="t-type">{inline_html(row["type"])}</span>｜{inline_html(row["desc"])}</li>')


def news_list_html(rows):
    """縣市卡內的新聞清單：由該縣所有災情行附帶的新聞合併去重（依 URL）。"""
    seen, items = set(), []
    for r in rows:
        for t, u, m in r.get("news", []):
            if u in seen:
                continue
            seen.add(u)
            items.append(f'<li><a href="{u}" target="_blank" rel="noopener">{inline_html(t)}</a> <span class="muted">— {m}</span></li>')
    return f'<ul class="news-list">{"".join(items)}</ul>' if items else ""


PINNED_BOTTOM = {"中國大陸": 1, "其他": 2}  # 這兩組固定在「各縣市災情」最底部
_CN_HOURS = (("凌晨", 4), ("清晨", 6), ("上午", 8), ("中午", 12), ("下午", 14),
             ("傍晚", 17), ("晚間", 20), ("夜間", 22))


def parse_row_time(s, fallback_mtime, year_hint=None, month_hint=None):
    """解析災情行的「日期時間」欄位 → datetime（只用於排序，不顯示）。
    常見格式：2026/7/10 05:30、2026/7/11、2026/7/11 下午、2026/7/12 凌晨4時、2026/7/24～25（取首日）。
    不帶年份的「M/D」依檔案路徑的 {YYYY}/{MM}/ 目錄推定年份（repo 慣例），
    跨年情境用月份差距修正：檔案在 12 月而日期在 1 月 → 下年度；反之 → 上年度。
    解析失敗時回退到事件檔 mtime（回傳值为 mtime 時由呼叫端計入 warning）。"""
    fallback = datetime.datetime.fromtimestamp(fallback_mtime)
    m = re.search(r"(20\d{2})/(\d{1,2})/(\d{1,2})", s or "")
    if not m:
        m = re.search(r"(?<!\d)(\d{1,2})/(\d{1,2})(?!\d)", s or "")  # 不帶年份：M/D（取首日）
        if not m or not year_hint:
            return fallback
        year, month, day = year_hint, int(m.group(1)), int(m.group(2))
        if month_hint:
            if month - month_hint > 2:
                year -= 1      # 檔案在 02 月、日期為 12/30 → 上年度
            elif month_hint - month > 2:
                year += 1      # 檔案在 12 月、日期為 1/3 → 下年度
    else:
        year, month, day = (int(g) for g in m.groups())
    try:
        base = datetime.datetime(year, month, day)
    except ValueError:
        return fallback
    tm = re.search(r"(\d{1,2}):(\d{2})", s)
    if tm:
        try:
            return base + datetime.timedelta(hours=int(tm.group(1)), minutes=int(tm.group(2)))
        except ValueError:
            pass
    h = re.search(r"(\d{1,2})\s*時", s)  # 例：凌晨4時、下午3時
    if h:
        try:
            return base + datetime.timedelta(hours=int(h.group(1)))
        except ValueError:
            pass
    for word, hour in _CN_HOURS:
        if word in (s or ""):
            return base + datetime.timedelta(hours=hour)
    return base


def compute_groups(events):
    """跨事件依縣分組（最新 8 筆/縣）。回傳 {縣名: [(idx, ev, row), ...]}。

    排序規則：
    - 縣內：依該筆災情行的日期時間（parse_row_time；不帶年份者依檔案 {YYYY}/{MM}/ 路徑推定）倒序，最新在上；
    - 縣間：依該縣「最新一筆災情」的時間倒序——哪縣剛有新災情，哪縣就浮到最上；
    - 「中國大陸」「其他」固定在最底部（本站以台灣縣市與周圍島嶼為優先）。
    """
    by_county = {}
    no_year = []  # 不帶年份靠路徑推定的行（供 warning，確認推定無誤）
    for e in events:
        year_hint = month_hint = None
        for part in e["path"].parts:  # 目錄慣例：…/{YYYY}/{MM}/…
            if re.fullmatch(r"20\d{2}", part):
                year_hint = int(part)
            elif re.fullmatch(r"\d{1,2}", part) and 1 <= int(part) <= 12:
                month_hint = int(part)
        for idx, r in enumerate(e["rows"]):
            c = find_county(r) or "其他"
            rt = parse_row_time(r["time"], e["mtime"], year_hint, month_hint)
            if rt == datetime.datetime.fromtimestamp(e["mtime"]) and not re.search(r"20\d{2}", r["time"]):
                no_year.append((e["name"], r["time"]))
            r["rowtime"] = rt
            by_county.setdefault(c, []).append((idx, e, r))
    if no_year:
        print(f"warning: {len(no_year)} 筆災情行無法解析日期，排序回退到檔案修改時間（建議補上完整年份，如 2026/7/10 05:30）：")
        for name, tm in no_year[:10]:
            print(f"  - {name}｜{tm!r}")
    items = {c: sorted(lst, key=lambda x: (x[2]["rowtime"], x[1]["mtime"], x[0]), reverse=True)[:8]
             for c, lst in by_county.items()}

    def order_key(kv):
        c, lst = kv
        latest = max(r["rowtime"] for _, _, r in by_county[c])
        return (PINNED_BOTTOM.get(c, 0), -latest.timestamp(), c)

    return dict(sorted(items.items(), key=order_key))


def chip_html(lang, county, groups):
    """hero 縣市 chip：有對應區塊 → 錨點連結；無 → 純文字。"""
    if county in groups:
        return f'<a class="chip chip-link" href="#{quote(county, safe="")}" title="{t(lang, "chip_jump", county=county)}">{county}</a>'
    return f'<span class="chip" title="{t(lang, "nav_no_county")}">{county}</span>'


def risk_bar_html(lang, level, items, ts, stale):
    """首頁頂部「目前風險狀態列」：level/items 由 cwa.current_risk_level() 推導。"""
    cls = {"red": "risk-red", "yellow": "risk-yellow", "green": "risk-green",
           "unknown": "risk-unknown"}[level]
    if level in ("red", "yellow"):
        body = "<ul>" + "".join(f"<li>{t(lang, key, **params)}</li>" for _, key, params in items) + "</ul>"
    elif level == "green":
        body = f'<p style="margin:4px 0 0">{t(lang, "risk_none")}</p>'
    else:
        body = ""
    stale_note = f"　{t(lang, 'stale_tag', ts='、'.join(stale.values()))}" if stale else ""
    return f"""
<section class="risk-bar {cls}">
<div class="risk-label">{t(lang, f"risk_label_{level}")}</div>
{body}
<p class="meta">{t(lang, "risk_asof", ts=ts)}{stale_note}</p>
</section>"""


def build_home(lang, events, ts, groups, cwa_ctx):
    active = [e for e in events if e["status"] == "active"]
    ended = [e for e in events if e["status"] != "active"]
    parts = []
    data, errors, stale, mode = cwa_ctx

    # 1. 目前風險狀態列：由 CWA 現況警報/特報推導（與事件歷史 severity 獨立，
    #    危險結束後不再顯示事件歷史紅）
    level, items = cwa.current_risk_level(lang, data, stale, mode)
    parts.append(risk_bar_html(lang, level, items, ts, stale))

    # 2. CWA 氣象總覽（現況資料來源，移至事件 hero 上方；build 時本機抓取，金鑰不出現在輸出）
    parts.append(cwa.cwa_section_html(lang, *cwa_ctx, has_active_event=bool(active)))

    # 3. Hero：active 事件入口卡（中性卡；severity 徽章只在事件頁與封存清單顯示）
    if active:
        main_ev = active[0]
        latest = main_ev["rows"][-6:][::-1]
        chips = "".join(chip_html(lang, c, groups) for c in main_ev["counties"])
        src = "、".join(main_ev["sources"])
        parts.append(f"""
<section class="card hero">
<h2 style="border:none"><span class="chip">{t(lang, "status_active")}</span>　<a href="{'/'.join(main_ev['url'])}">{main_ev["name"]}</a></h2>
<p class="meta">{(t(lang, "hero_period", p=main_ev["period"]) + "　") if main_ev["period"] else ""}{t(lang, "hero_source", src=src)}</p>
<p>{main_ev["summary"]}</p>
<div class="chips">{chips}</div>
<h3 style="font-size:1rem;margin:14px 0 4px">{t(lang, "hero_latest")}</h3>
<ul class="timeline">{''.join(row_html(r) for r in latest) or f'<li class="muted">{t(lang, "hero_no_rows")}</li>'}</ul>
<a class="hero-cta" href="{'/'.join(main_ev['url'])}">{t(lang, "hero_cta")}</a>
</section>""")
        # 其他 active 事件
        for e in active[1:]:
            parts.append(f"""
<section class="card hero">
<h2 style="border:none"><span class="chip">{t(lang, "status_active")}</span>　<a href="{'/'.join(e['url'])}">{e["name"]}</a></h2>
<p>{e["summary"]}</p>
</section>""")
    else:
        parts.append(f'<section class="card hero"><h2 style="border:none;margin-top:0">{t(lang, "no_event_title")}</h2><p>{t(lang, "no_event_body")}</p></section>')

    # 4. 各縣市災情（跨事件，依縣分組，最新在最上；卡片帶 id 供錨點跳轉）
    if groups:
        blocks = []
        for county, lst in groups.items():
            rows_html = "".join(row_html(r) for _, _, r in lst)
            news_html = news_list_html([r for _, _, r in lst])
            blocks.append(f"""
<div class="card county-card" id="{quote(county, safe='')}" style="padding:12px 16px">
<h3 style="margin:4px 0;font-size:1rem">{county}　<span class="muted">（{t(lang, "county_latest", n=len(lst))}）</span>　<a href="#top" class="muted" style="float:right">{t(lang, "back_to_top")}</a></h3>
{news_html}
<ul class="timeline">{rows_html}</ul>
</div>""")
        parts.append(f'<section><h2>{t(lang, "county_section")}</h2>' + "".join(blocks) + "</section>")

    # 5. 過去事件封存（active / ended 均可瀏覽；保留 severity 徽章：歷史事件索引）
    if ended:
        lis = []
        for e in ended:
            lis.append(f"""<li>{badge(lang, e['severity'])}　<a href="{'/'.join(e['url'])}">{e["name"]}</a>
<span class="meta">{("（" + e["period"] + "）") if e["period"] else ""}</span><br><span class="meta">{e["summary"]}</span></li>""")
        parts.append(f'<section><h2>{t(lang, "archive_title")}</h2><ul class="archive-list">' + "".join(lis) + "</ul></section>")

    return "".join(parts)


def build_event_page(lang, ev, ts, depth):
    home_link = "../" * depth + "index.html"
    body_html = markdown.markdown(ev["body"], extensions=["tables", "sane_lists"])
    chips = "".join(f'<span class="chip">{c}</span>' for c in ev["counties"])
    status = t(lang, "status_active" if ev["status"] == "active" else "status_ended")
    note = f'<p class="meta">{t(lang, "content_note")}</p>' if not i18n.is_default(lang) else ""
    content = f"""
<a class="backlink" href="{home_link}">{t(lang, "back_home")}</a>
<section class="card hero sev-{ev['severity']}" style="padding:12px 18px">
{badge(lang, ev['severity'])}　<span class="meta">{status}</span>
{note}
{"<div class='chips'>" + chips + '</div>' if chips else ''}
</section>
<div class="event-content">
{body_html}
</div>"""
    return content


SITE_BASE = "https://weather.avpclub.eu.org"


def build_llms_files(events, ts, cwa_ctx):
    """產生 llms.txt（簡明索引＋目前風險狀態）與 llms-full.txt（事件全文），供 LLM 讀取本站內容。

    固定用繁中（default 語言路徑，即 public/ 根），因為事件正文皆為繁中原文。
    """
    base = SITE_BASE
    active = [e for e in events if e["status"] == "active"]
    ended = [e for e in events if e["status"] != "active"]
    sev = {"red": "🔴 重大", "yellow": "🟡 警戒", "green": "🟢 一般"}
    data, errors, stale, mode = cwa_ctx
    level, items = cwa.current_risk_level("zh-Hant", data, stale, mode)
    risk_label = t("zh-Hant", f"risk_label_{level}")
    risk_detail = "；".join(t("zh-Hant", k, **p) for _, k, p in items) or t("zh-Hant", "risk_none").rstrip("。")
    risk_line = (f"> 目前風險狀態（依 CWA 目前之警報與特報判斷，產生於 {ts}）："
                 f"{risk_label}——{risk_detail}。")

    def link(e):
        return f"{base}/{'/'.join(e['url'])}"

    def heading(e):
        status = "進行中" if e["status"] == "active" else "已結束"
        return f"### {e['name']}（{status}・{sev.get(e['severity'], e['severity'])}）\n"

    # --- llms.txt：索引 ---
    lines = ["# 台灣天氣與災情總覽",
             "",
             f"> 記錄台灣目前與歷史上發生的颱風、低壓帶、豪雨等天氣事件與各縣市災情的純靜態網站。"
             f"氣象資料來源為中央氣象署（CWA）Open Data API，災情來源為各縣市政府公告與新聞媒體。"
             f"產生時間：{ts}。繁中為預設語言；`/ja/` 為日文介面（事件正文仍為繁中原文）。",
             "",
             risk_line,
             "",
             "## 網站結構",
             "",
             f"- [首頁（氣象彙整＋各縣市災情總覽）]({base}/index.html)",
             f"- [日文介面（UI 為日文，事件正文為繁中原文）]({base}/ja/index.html)",
             "",
             "- 所有事件列表（含已結束）見首頁側邊欄，本檔下方亦分列進行中／已結束。",
             "",
             "## 進行中的事件", ""]
    if active:
        for e in active:
            lines += [f"- [{e['name']}]({link(e)})（{sev.get(e['severity'], e['severity'])}）"]
    else:
        lines.append("- （目前無進行中的事件）")
    lines += ["", "## 已結束的事件", ""]
    if ended:
        for e in ended:
            lines.append(f"- [{e['name']}]({link(e)})（{sev.get(e['severity'], e['severity'])}）")
    else:
        lines.append("- （尚無）")
    lines += ["",
              "## 資料說明",
              "",
              "- 每筆災情均附新聞來源與連結，並標注時間戳（格式：`YYYY/M/D HH:MM`）。",
              "- 災害分級：🔴 重大／🟡 警戒／🟢 一般。",
              "- 首頁的颱風軌跡、警報特報、雨量 TOP-10 等氣象資料由 build 時自 CWA API 抓取，非即時。",
              "- 完整事件全文另見 `llms-full.txt`（同一網址下）。",
              "",
              "## 授權",
              "",
              "- 本內容（災情紀錄與彙整，含本檔）：CC BY-NC-SA 4.0（創用 CC 姓名標示-非商業性-相同方式分享 4.0 國際）——"
              "可自由分享與調修，但須註明出處、不得商用、衍生作品須以相同授權釋出。",
              "- 程式碼：GNU AGPLv3。",
              "- 源自中央氣象署（CWA）Open Data API 的氣象資料以 CWA 官方條款為準。",
              ""]
    (OUT / "llms.txt").write_text("\n".join(lines), encoding="utf-8")

    # --- llms-full.txt：全文 ---
    full = ["# 台灣天氣與災情總覽（llms-full.txt）",
            "",
            f"產生時間：{ts}。本檔含全部事件的完整內容（繁中原文）。",
            "",
            "---", ""]
    for e in events:
        full += [heading(e),
                 f"- 網頁：{link(e)}", "- 範圍：" + ("、".join(e["counties"]) or "未指定"),
                 f"- 期間：{e['period']}", "- 摘要：" + e["summary"], ""]
        full += ["### 內容", "", e["body"].rstrip(), "", "---", ""]
    (OUT / "llms-full.txt").write_text("\n".join(full), encoding="utf-8")


def main():
    if OUT.exists():
        for p in OUT.rglob("*"):
            if p.is_file():
                p.unlink()
    OUT.mkdir(parents=True, exist_ok=True)
    # 固定使用台灣時間（UTC+8），不依賴執行 build 機器的本地時區
    # （GitHub Actions runner 跑在 UTC，用 datetime.now() 會慢 8 小時）。
    ts = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y/%-m/%-d %H:%M")
    events = load_events()
    if not events:
        sys.exit("找不到任何含 front matter 的事件檔案")
    groups = compute_groups(events)
    cwa_ctx = cwa.load_snapshot()

    for lang in LANGS:
        outdir = OUT if i18n.is_default(lang) else OUT / lang
        outdir.mkdir(parents=True, exist_ok=True)
        home = render_page(lang, t(lang, "site_title"), ts, "index.html",
                           build_nav(lang, events, "index.html", "", "__home__", groups),
                           build_home(lang, events, ts, groups, cwa_ctx))
        (outdir / "index.html").write_text(home, encoding="utf-8")

        for e in events:
            depth = len(e["rel"]) - 1  # 檔案所在目錄層數
            base = "../" * depth
            page = render_page(lang, e["name"], ts, base + "index.html",
                               build_nav(lang, events, base + "index.html", base, "/".join(e["url"]), groups),
                               build_event_page(lang, e, ts, depth))
            out_path = outdir.joinpath(*e["rel"])
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(page, encoding="utf-8")

    build_llms_files(events, ts, cwa_ctx)

    mode = cwa_ctx[3]
    src_note = {"live": "CWA live", "partial": "CWA partial（含舊資料）", "cache": "CWA 快取", "none": "CWA 無法取得"}[mode]
    risk, _ = cwa.current_risk_level("zh-Hant", cwa_ctx[0], cwa_ctx[2], mode)
    print(f"build 完成：{len(events)} 個事件（active {sum(1 for e in events if e['status']=='active')} / ended {sum(1 for e in events if e['status']!='active')}）｜{src_note}｜目前風險：{risk}｜llms.txt + llms-full.txt 已產生")
    print(f"輸出：{OUT}")
    print(f"預覽：cd {OUT} && python3 -m http.server 8080")


if __name__ == "__main__":
    main()

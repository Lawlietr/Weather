#!/usr/bin/env python3
"""檢查 public/ 內部連結是否有對應檔案（§12 斷鏈的驗證工具；build 後跑）。

用法：build/.venv/bin/python build/check_links.py [--public public] [--show 20]

只查「本地」href/src（跳過 http(s)://、mailto:、data:、#anchor）：
以檔案所在目錄解析相對路徑，目錄則補 index.html；`?query` 先丟掉。

⚠️ 已知限制（不算斷鏈、但如實標出）：`404.html` 的相對連結。Cloudflare Pages 對
「任何深度」的未匹配路徑都送同一份 top-level 404.html，瀏覽器會以**被請求的 URL**
為基準解析相對連結 → 深路徑的 404 頁側欄連結可能再次 404。改成絕對 URL 會讓
GitHub Pages mirror（/Weather/ 前綴）跳回 CF 域名，故刻意保留相對寫法（見 TODO §12）。
"""
import argparse
import sys
from pathlib import Path
from urllib.parse import unquote

SKIP_PREFIXES = ("http://", "https://", "mailto:", "data:", "//", "#")


def check(public: Path, show: int):
    broken, by_pattern, soft = [], {}, []
    for html in sorted(public.rglob("*.html")):
        rel_dir = html.parent.relative_to(public)
        is_404 = html.name == "404.html"
        text = html.read_text(encoding="utf-8", errors="replace")
        # href="..." 與 src="..."（含 CSS url() 少用；此站前端零外部請求）
        for attr in ('href="', 'src="'):
            i = 0
            while True:
                i = text.find(attr, i)
                if i < 0:
                    break
                j = text.find('"', i + len(attr))
                if j < 0:
                    break
                url = text[i + len(attr):j]
                i = j
                raw = url
                url = url.split("#", 1)[0].split("?", 1)[0]
                if not url or url.startswith(SKIP_PREFIXES):
                    continue
                target = (public / rel_dir / unquote(url)).resolve()
                if not (target.exists() or (target / "index.html").exists()):
                    rec = (str(html.relative_to(public)), raw)
                    if is_404:
                        soft.append(rec)
                    else:
                        broken.append(rec)
                        key = raw.split("/")[-1] if ".md" not in raw else "<*.md>"
                        if "map/index.html" in raw or "index.html" in raw:
                            key = raw[-40:]
                        by_pattern[key] = by_pattern.get(key, 0) + 1
    print(f"public: {public}  斷鏈 {len(broken)} 條（另有 404 頁相對連結 {len(soft)} 條，見檔首限制說明）")
    for k, v in sorted(by_pattern.items(), key=lambda x: -x[1])[:15]:
        print(f"  {v:4d} × {k}")
    for rec in broken[:show]:
        print(f"  ✗ {rec[0]} → {rec[1]}")
    if len(broken) > show:
        print(f"  …（還有 {len(broken) - show} 條，加 --show N 看更多）")
    return len(broken)


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    ap.add_argument("--public", default=str(here.parent / "public"))
    ap.add_argument("--show", type=int, default=20)
    a = ap.parse_args()
    public = Path(a.public)
    if not public.is_dir():
        sys.exit(f"找不到 {public}（先跑 ./build/build.sh）")
    sys.exit(1 if check(public, a.show) else 0)


if __name__ == "__main__":
    main()

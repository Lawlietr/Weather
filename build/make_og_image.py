#!/usr/bin/env python3
"""產出 build/static/og.png（1200×630 Open Graph 卡片圖；純 stdlib、無相依）。

設計：深藍漸層底＋琥珀日輪＋雲＋雨線（抽象天氣符號，無文字——純 Python 無字型渲染）。
重跑即覆寫 build/static/og.png（檔案 commit 進 git；build/site.py 每次 build 時
複製到 public/assets/og.png 供 og:image 使用）。

用法：python3 build/make_og_image.py
"""
import struct
import zlib
from pathlib import Path

W, H = 1200, 630
OUT = Path(__file__).resolve().parent / "static" / "og.png"

TOP = (11, 18, 32)      # 上：深藏青
BOT = (30, 41, 59)      # 下：石板藍
SUN = (251, 191, 36)    # 琥珀
CLOUD = (226, 232, 240) # 淺灰藍
RAIN = (96, 165, 250)   # 藍


def lerp(a, b, t):
    return a + (b - a) * t


def draw(x, y):
    # 垂直漸層底
    tt = y / H
    px = (int(lerp(TOP[0], BOT[0], tt)), int(lerp(TOP[1], BOT[1], tt)), int(lerp(TOP[2], BOT[2], tt)))
    # 日輪（左中）
    if (x - 400) ** 2 + (y - 300) ** 2 <= 150 ** 2:
        px = SUN
    # 雲（三個重疊圓，蓋住日輪右緣）
    for cx, cy, r in ((520, 290, 90), (630, 260, 115), (740, 295, 85)):
        if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
            px = CLOUD
            break
    # 雨線（雲下三條斜線）
    for rx in (560, 650, 740):
        if 420 <= y <= 530 and 0 <= x - (rx + (y - 420) * 0.25) <= 16:
            px = RAIN
            break
    return px


def main():
    raw = b"".join(b"\x00" + b"".join(bytes(draw(x, y)) for x in range(W)) for y in range(H))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)  # 8-bit RGB
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(png)
    print(f"written {OUT}（{len(png):,} bytes, {W}x{H}）")


if __name__ == "__main__":
    main()

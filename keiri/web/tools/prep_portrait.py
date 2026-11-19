"""立ち絵の下ごしらえ：明るい無地の背景を透明にして、余白を詰め、ゲーム用のサイズで保存する。

使い方:
  python keiri/web/tools/prep_portrait.py 入力画像 出力.webp [--box 左,上,右,下]

--box を付けると、先にその範囲を切り抜く（コラージュ画像から1枚ずつ取り出すとき用）。
背景は「上・左・右の端から続く、明るく彩度の低い色」とみなして抜く。下端は服が続くので抜かない。
"""
import argparse

import numpy as np
from PIL import Image, ImageFilter


def cutout(im: Image.Image) -> Image.Image:
    a = np.asarray(im.convert("RGB")).astype(np.int16)
    bright = a.mean(axis=2) > 150
    flat = (a.max(axis=2) - a.min(axis=2)) < 22
    cand = bright & flat
    region = np.zeros_like(cand)
    region[0, :] = cand[0, :]
    region[:, 0] = cand[:, 0]
    region[:, -1] = cand[:, -1]
    while True:  # 端から背景の候補をたどって広げる
        grow = region.copy()
        grow[1:, :] |= region[:-1, :]
        grow[:-1, :] |= region[1:, :]
        grow[:, 1:] |= region[:, :-1]
        grow[:, :-1] |= region[:, 1:]
        grow &= cand
        if (grow == region).all():
            break
        region = grow
    alpha = Image.fromarray(np.where(region, 0, 255).astype(np.uint8))
    alpha = alpha.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.GaussianBlur(1.6))
    out = im.convert("RGBA")
    out.putalpha(alpha)
    return out.crop(out.getbbox())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--box", help="左,上,右,下")
    ap.add_argument("--height", type=int, default=900)
    o = ap.parse_args()
    im = Image.open(o.src)
    if o.box:
        im = im.crop(tuple(int(v) for v in o.box.split(",")))
    out = cutout(im)
    if out.height > o.height:
        out = out.resize((round(out.width * o.height / out.height), o.height), Image.LANCZOS)
    out.save(o.dst, "WEBP", quality=86, method=6)
    print(f"{o.dst}: {out.size}")


if __name__ == "__main__":
    main()

"""立ち絵の下ごしらえ：背景を透明にして、余白を詰め、ゲーム用のサイズで保存する。

背景抜きには切り抜きモデル（rembg の isnet-general-use）を使う。
  pip install "rembg[cpu]"   （初回はモデルを自動でダウンロードする）
rembg が無い場合は、明るい無地の背景を色で判定して抜く簡易版で処理する（白いシャツは苦手）。

使い方:
  python keiri/web/tools/prep_portrait.py 入力画像 出力.webp [--box 左,上,右,下]

--box を付けると、先にその範囲を切り抜く（コラージュ画像から1枚ずつ取り出すとき用）。
背景は「上と横の端から、隣とほぼ同じ色でなめらかに続く、明るく彩度の低い部分」とみなして抜く。
"""
import argparse

import numpy as np
from PIL import Image, ImageFilter


MODEL = "isnet-general-use"  # 持ち物（スマホなど）も残す汎用モデル。--model で変更できる
ERODE = 0                     # 輪郭を何ピクセル内側に削るか（--erode）


def cutout(im: Image.Image) -> Image.Image:
    try:
        from rembg import new_session, remove
    except ImportError:
        return cutout_simple(im)
    global _SESSION
    if "_SESSION" not in globals():
        _SESSION = new_session(MODEL)
    out = remove(im.convert("RGB"), session=_SESSION, post_process_mask=True)
    if ERODE:  # 髪の毛先などに残る背景のふちを削る
        a = out.getchannel("A").filter(ImageFilter.MinFilter(2 * ERODE + 1)).filter(ImageFilter.GaussianBlur(1))
        out.putalpha(a)
    return out.crop(out.getbbox())


def cutout_simple(im: Image.Image) -> Image.Image:
    a = np.asarray(im.convert("RGB")).astype(np.int16)
    h, w, _ = a.shape
    flat = (a.max(axis=2) - a.min(axis=2)) < 22
    bright = a.mean(axis=2) > 120
    ok = flat & bright
    # 背景はゆるやかなグラデーション。隣の背景とほぼ同じ色なら背景とみなして広げる。
    # 髪や服の輪郭のような、はっきりした境目は越えない。
    T = 6
    dv = np.abs(a[1:] - a[:-1]).max(axis=2) < T       # 上下の隣と近いか
    dh = np.abs(a[:, 1:] - a[:, :-1]).max(axis=2) < T  # 左右の隣と近いか
    region = np.zeros((h, w), bool)
    region[0] = ok[0]
    side = int(h * 0.5)                                 # 横の端は上半分だけを起点にする
    region[:side, 0] |= ok[:side, 0]
    region[:side, -1] |= ok[:side, -1]
    while True:
        g = region.copy()
        g[1:] |= region[:-1] & dv
        g[:-1] |= region[1:] & dv
        g[:, 1:] |= region[:, :-1] & dh
        g[:, :-1] |= region[:, 1:] & dh
        g &= ok
        if (g == region).all():
            break
        region = g
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
    ap.add_argument("--model", default=MODEL, help="rembg のモデル名（例：u2net_human_seg）")
    ap.add_argument("--erode", type=int, default=0, help="輪郭を内側に削るピクセル数（髪のふちの背景残り対策）")
    o = ap.parse_args()
    globals()["MODEL"] = o.model
    globals()["ERODE"] = o.erode
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

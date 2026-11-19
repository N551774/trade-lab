"""keiri/content*.py の学習データと chars.js を埋め込み、index.html（ゲーム）と characters.html（キャラクター図鑑）を作る。

使い方:  python keiri/web/build.py
"""
import base64
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))

from content import ACCOUNTS, DRILL, LESSONS, TERMS  # noqa: E402
from content_jitsumu import CAREER, DOCS, PRACTICE_LESSONS, PROMOTE_RATIO  # noqa: E402

data = {
    "accounts": {k: {"cat": v["cat"], "desc": v["desc"]} for k, v in ACCOUNTS.items()},
    "drill": DRILL,
    "checks": {l["id"]: l["check"] for l in LESSONS + PRACTICE_LESSONS},
    "terms": TERMS,
    "docs": [{**d, "answer": sorted(d["answer"])} for d in DOCS],
    "career": [{k: v for k, v in s.items()} for s in CAREER],
    "promote": PROMOTE_RATIO,
}
chars = (HERE / "chars.js").read_text(encoding="utf-8")
# 立ち絵：img/人物_表情.webp を data URI にして埋め込む（Streamlit でも表示できるように）
imgs = {p.stem.replace("_", ":", 1): "data:image/webp;base64," + base64.b64encode(p.read_bytes()).decode()
        for p in sorted((HERE / "img").glob("*.webp"))}


def build(src_name: str, out_name: str) -> None:
    src = (HERE / src_name).read_text(encoding="utf-8")
    out = (src.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
              .replace("/*__CHARS__*/", chars)
              .replace("/*__IMG__*/{}", json.dumps(imgs)))
    (HERE / out_name).write_text(out, encoding="utf-8")
    print(f"wrote {out_name} ({len(out) // 1024} KB)")


build("app.src.html", "index.html")            # ゲーム本体
build("characters.src.html", "characters.html")  # キャラクター図鑑
build("balance.src.html", "balance.html")        # ストーリーモード「バランスシート」

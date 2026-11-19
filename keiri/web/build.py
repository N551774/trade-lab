"""keiri/content*.py の学習データを JSON にして app.src.html に埋め込み、index.html を作る。

使い方:  python keiri/web/build.py
"""
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
src = (HERE / "app.src.html").read_text(encoding="utf-8")
out = src.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
(HERE / "index.html").write_text(out, encoding="utf-8")
print(f"wrote index.html ({len(out) // 1024} KB)")

"""経理ラボ — 経理の仕事を学ぶアプリ（Streamlit）

起動:  streamlit run keiri/app.py
"""
from __future__ import annotations

import json
import random
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))  # リポジトリ直下から起動しても import できるように

import ledger as lg  # noqa: E402
from content import (ACCOUNTS, ANNUAL, CAT_INFO, DRILL, DRILL_TAGS, LESSONS,  # noqa: E402
                     ROUTINE, TERMS)
from content_jitsumu import (CAREER, DOCS, MATCH_ACTIONS, MATCH_SETS,  # noqa: E402
                             PRACTICE_LESSONS, PROMOTE_RATIO, STORY_RANKS)

LESSONS = LESSONS + PRACTICE_LESSONS

st.set_page_config(page_title="経理ラボ", page_icon="📒", layout="centered")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Noto+Sans+JP:wght@400;500;700;900&display=swap');
:root {--bg:#0b0b0c; --surface:#161615; --surface2:#1f1f1d; --line:#2a2a28; --text:#f2f2ef; --muted:#9a9a95;
  --lime:#c6f432; --ok:#c6f432; --ng:#ff5a6a; --num:"Space Grotesk","Noto Sans JP",sans-serif;}
html, body, .stApp, .stMarkdown, button, input, textarea, select {
  font-family:"Noto Sans JP",-apple-system,"Hiragino Sans",sans-serif !important;}
.stApp {background:var(--bg) !important;}
.block-container {padding-top:2.4rem; padding-bottom:4rem;}
header[data-testid="stHeader"] {background:transparent; height:2.4rem;}
.num, [data-testid="stMetricValue"] {font-family:var(--num) !important; font-variant-numeric:tabular-nums;}
.brand {display:flex; align-items:baseline; gap:10px; margin-bottom:6px;}
.brand b {font-family:var(--num); font-size:1.35rem; letter-spacing:-.02em;}
.brand b i {font-style:normal; color:var(--lime);}
.brand small {color:var(--muted); font-size:.75rem;}
.st-key-topnav {position:sticky; top:2.4rem; z-index:50; padding:6px 0 10px; background:rgba(11,11,12,.9);
  backdrop-filter:blur(12px); -webkit-backdrop-filter:blur(12px);}
.st-key-topnav [data-testid="stButtonGroup"] > div {gap:6px; flex-wrap:wrap;}
.card {background:var(--surface); border:1px solid var(--line); border-radius:14px; padding:16px 18px; margin:6px 0 12px;}
.card h4 {margin:0 0 6px; font-size:1rem;}
.q {font-size:1.08rem; font-weight:700; line-height:1.7;}
.tag {display:inline-block; font-size:.7rem; padding:2px 9px; border-radius:999px; background:var(--surface2);
  color:var(--muted); margin-right:6px; border:1px solid var(--line);}
.ok {color:var(--ok); font-weight:800;}
.ng {color:var(--ng); font-weight:800;}
.je {font-family:var(--num), "Noto Sans JP"; width:100%; border-collapse:collapse; font-size:.92rem;}
.je th {color:var(--muted); font-weight:500; text-align:left; padding:4px 6px; border-bottom:1px solid var(--line);}
.je td {padding:6px; border-bottom:1px dashed var(--line);}
.je td.amt {text-align:right; font-variant-numeric:tabular-nums;}
.cat {display:inline-block; width:9px; height:9px; border-radius:3px; margin-right:6px;}
.muted {color:var(--muted); font-size:.85rem;}
.bar {height:8px; border-radius:99px; background:var(--surface2); overflow:hidden;}
.bar > div {height:100%; background:var(--lime);}
.ladder {display:flex; gap:4px; flex-wrap:wrap; margin:4px 0 10px;}
.ladder span {font-size:.72rem; padding:4px 9px; border-radius:999px; border:1px solid var(--line); color:var(--muted);}
.ladder span.done {color:var(--bg); background:#6f8a1c; border-color:#6f8a1c;}
.ladder span.now {color:var(--bg); background:var(--lime); border-color:var(--lime); font-weight:800;}
.who {display:flex; gap:12px; align-items:flex-start;}
.who .ic {font-size:2rem; line-height:1;}
.who .nm {font-size:.75rem; color:var(--muted);}
.pts {font-family:var(--num); font-weight:800; font-size:1.2rem;}
.point {border-left:3px solid var(--lime); padding:10px 14px; background:var(--surface2); border-radius:6px; margin:8px 0;}
.paper {background:#f6f4ec; color:#1d1d1b; border-radius:6px; padding:18px 20px; margin:8px 0 14px;
  box-shadow:0 6px 24px rgba(0,0,0,.45); font-family:"Noto Sans JP",sans-serif;}
.paper .kind {font-size:1.25rem; font-weight:900; letter-spacing:.3em; text-align:center; border-bottom:2px solid #1d1d1b;
  padding-bottom:6px; margin-bottom:4px;}
.paper .sub {text-align:center; font-size:.8rem; color:#555; margin-bottom:10px;}
.paper table {width:100%; border-collapse:collapse; font-size:.9rem;}
.paper td {padding:6px 4px; border-bottom:1px solid #d8d4c6; vertical-align:top;}
.paper td:first-child {color:#666; width:38%; white-space:nowrap;}
.dep {font-family:var(--num); font-size:1.05rem;}
</style>""", unsafe_allow_html=True)

ACCT_NAMES = list(ACCOUNTS)
NONE = "（なし）"


# ─────────────────────────────────────────────
# 学習記録（セッション内に保持。JSONで書き出し／読み込み可能）
# ─────────────────────────────────────────────
def new_progress() -> dict:
    return {"lessons": [], "drill": {}, "acct": {}, "terms": {}, "routine": {}, "journal": [],
            "story": {}, "docs": {}, "match": {}, "career": new_career()}


def new_career() -> dict:
    # stage: 今のステージ / i: -1=導入, 0..n-1=イベント, n=評価 / picked: 選んだ選択肢
    return {"stage": 0, "i": -1, "pts": 0, "total": 0, "picked": None, "done": False, "retries": 0, "best": None}


if "prog" not in st.session_state:
    st.session_state.prog = new_progress()
P: dict = st.session_state.prog


def record(kind: str, key: str, ok: bool) -> None:
    s = P[kind].setdefault(key, {"ok": 0, "ng": 0, "last": None})
    s["ok" if ok else "ng"] += 1
    s["last"] = ok


def accuracy(kind: str) -> tuple[int, int]:
    ok = sum(v["ok"] for v in P[kind].values())
    ng = sum(v["ng"] for v in P[kind].values())
    return ok, ok + ng


def yen(v: int) -> str:
    return f"{v:,}"


def bar(ratio: float) -> str:
    return f'<div class="bar"><div style="width:{max(0, min(1, ratio)) * 100:.0f}%"></div></div>'


def cat_dot(acct: str) -> str:
    return f'<span class="cat" style="background:{CAT_INFO[ACCOUNTS[acct]["cat"]]["color"]}"></span>'


def entry_html(dr: list, cr: list) -> str:
    """仕訳を左右2列の表で表示。dr/cr は [(科目, 金額)]。"""
    n = max(len(dr), len(cr))
    rows = []
    for i in range(n):
        d = dr[i] if i < len(dr) else ("", "")
        c = cr[i] if i < len(cr) else ("", "")
        rows.append(
            f"<tr><td>{cat_dot(d[0]) if d[0] else ''}{d[0]}</td><td class='amt'>{yen(d[1]) if d[1] != '' else ''}</td>"
            f"<td>{cat_dot(c[0]) if c[0] else ''}{c[0]}</td><td class='amt'>{yen(c[1]) if c[1] != '' else ''}</td></tr>")
    return ("<table class='je'><tr><th>借方科目</th><th style='text-align:right'>金額</th>"
            "<th>貸方科目</th><th style='text-align:right'>金額</th></tr>" + "".join(rows) + "</table>")


def entry_input(key: str, options: list[str], rows: int = 2) -> list[dict]:
    """仕訳の入力欄（借方・貸方とも rows 行）。入力された行だけ返す。"""
    lines: list[dict] = []
    opts = [NONE] + options
    cols = st.columns(2)
    for side, col in zip(["借方", "貸方"], cols):
        with col:
            st.markdown(f"**{side}**{'（左）' if side == '借方' else '（右）'}")
            for i in range(rows):
                a = st.selectbox(f"{side}科目{i + 1}", opts, key=f"{key}_{side}_a{i}", label_visibility="collapsed")
                v = st.number_input(f"{side}金額{i + 1}", min_value=0, value=None, step=1000, key=f"{key}_{side}_v{i}",
                                    label_visibility="collapsed", placeholder="金額")
                if a != NONE and v:
                    lines.append({"side": side, "acct": a, "amount": int(v)})
    return lines


def to_lines(dr: list, cr: list) -> list[dict]:
    return ([{"side": "借方", "acct": a, "amount": v} for a, v in dr]
            + [{"side": "貸方", "acct": a, "amount": v} for a, v in cr])


# ─────────────────────────────────────────────
# ヘッダー・ナビ
# ─────────────────────────────────────────────
st.markdown('<div class="brand"><b>経理<i>ラボ</i></b><small>仕訳から決算まで、手を動かして覚える</small></div>',
            unsafe_allow_html=True)
PAGES = ["ホーム", "キャリア", "講座", "仕訳ドリル", "証憑チェック", "入金消込", "科目クイズ", "用語クイズ",
         "帳簿づくり", "経理カレンダー", "科目辞典"]
with st.container(key="topnav"):
    page = st.segmented_control("メニュー", PAGES, default="ホーム", key="page", label_visibility="collapsed") or "ホーム"


# ─────────────────────────────────────────────
# ホーム
# ─────────────────────────────────────────────
def page_home() -> None:
    d_ok, d_n = accuracy("drill")
    a_ok, a_n = accuracy("acct")
    t_ok, t_n = accuracy("terms")
    done_l = len(P["lessons"])
    mastered = sum(1 for v in P["drill"].values() if v["last"])
    c = st.columns(4)
    c[0].metric("講座", f"{done_l}/{len(LESSONS)}")
    c[1].metric("仕訳 正解済み", f"{mastered}/{len(DRILL)}")
    c[2].metric("仕訳 正答率", f"{d_ok / d_n:.0%}" if d_n else "—")
    c[3].metric("クイズ 正答率", f"{(a_ok + t_ok) / (a_n + t_n):.0%}" if a_n + t_n else "—")

    st.markdown("#### おすすめの進め方")
    steps = [
        ("キャリア", "新入社員から経理部長を目指すストーリーで、実務の判断を体験する", P["career"]["done"]),
        ("講座", "1〜3章で「5要素」と「借方・貸方」のルールを理解する", done_l >= 3),
        ("科目クイズ", "勘定科目が5要素のどれかを即答できるようにする", a_ok >= 20),
        ("仕訳ドリル", "「基本」タグの問題を全問正解する",
         all(P["drill"].get(p["id"], {}).get("last") for p in DRILL if p["tag"] == "基本")),
        ("仕訳ドリル", "給与・消費税・決算の仕訳に挑戦する", mastered >= len(DRILL) * 0.8),
        ("帳簿づくり", "自分で仕訳を入れて、試算表と決算書ができる流れを体験する", len(P["journal"]) >= 5),
        ("証憑チェック・入金消込", "請求書の不備を見抜き、入金を正しく消し込めるようになる",
         len([1 for v in P["docs"].values() if v["last"]]) >= 6),
        ("経理カレンダー", "毎月・毎年の締め切りを覚える", False),
    ]
    for i, (where, what, done) in enumerate(steps, 1):
        mark = "✅" if done else f"**{i}.**"
        st.markdown(f"{mark} **{where}** — {what}")

    weak = sorted(((k, v) for k, v in P["drill"].items() if v["ng"]), key=lambda kv: -kv[1]["ng"])[:5]
    if weak:
        st.markdown("#### 間違えが多い仕訳")
        by_id = {p["id"]: p for p in DRILL}
        for pid, v in weak:
            p = by_id.get(pid)
            if p:
                st.markdown(f"<div class='card'><span class='tag'>{p['tag']}</span>"
                            f"<span class='muted'>✕{v['ng']}　○{v['ok']}</span><br>{p['q']}</div>",
                            unsafe_allow_html=True)

    with st.expander("学習記録の保存・読み込み"):
        st.caption("記録はこの画面を開いている間だけ保持されます。続きから学習したいときは、ファイルに保存して次回読み込んでください。")
        st.download_button("学習記録をダウンロード", json.dumps(P, ensure_ascii=False, indent=1),
                           file_name=f"keiri-lab-{date.today():%Y%m%d}.json", mime="application/json")
        up = st.file_uploader("保存した記録を読み込む", type="json")
        if up is not None and st.button("この記録で上書きする"):
            try:
                data = json.load(up)
                base = new_progress()
                base.update({k: data[k] for k in base if k in data})
                st.session_state.prog = base
                st.success("読み込みました。")
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f"読み込めませんでした：{e}")
        if st.button("記録をリセット", type="secondary"):
            st.session_state.prog = new_progress()
            st.rerun()


# ─────────────────────────────────────────────
# 講座
# ─────────────────────────────────────────────
def page_lessons() -> None:
    titles = [f"{'✅ ' if l['id'] in P['lessons'] else ''}{i}. {l['title']}" for i, l in enumerate(LESSONS, 1)]
    idx = st.selectbox("章を選ぶ", range(len(LESSONS)), format_func=lambda i: titles[i], key="lesson_idx")
    L = LESSONS[idx]
    st.markdown(f"## {L['title']}")
    st.markdown(f"<p class='muted'>{L['lead']}</p>", unsafe_allow_html=True)
    st.markdown(L["body"])

    st.markdown("---\n#### 理解チェック")
    all_ok = True
    for j, c in enumerate(L["check"]):
        ans = st.radio(c["q"], c["choices"], index=None, key=f"lc_{L['id']}_{j}")
        if ans is None:
            all_ok = False
            continue
        if c["choices"].index(ans) == c["a"]:
            st.markdown(f"<span class='ok'>○ 正解</span>　{c['exp']}", unsafe_allow_html=True)
        else:
            all_ok = False
            st.markdown(f"<span class='ng'>✕ 不正解</span>　正解は「{c['choices'][c['a']]}」。{c['exp']}",
                        unsafe_allow_html=True)
    if all_ok and L["id"] not in P["lessons"]:
        P["lessons"].append(L["id"])
        st.success("この章は完了です！")
    c1, c2 = st.columns(2)
    def go(i: int) -> None:
        st.session_state.lesson_idx = i
    if idx > 0:
        c1.button("← 前の章", width="stretch", on_click=go, args=(idx - 1,))
    if idx < len(LESSONS) - 1:
        c2.button("次の章 →", width="stretch", on_click=go, args=(idx + 1,))


# ─────────────────────────────────────────────
# 仕訳ドリル
# ─────────────────────────────────────────────
def pick_problem(tags: list[str], only_wrong: bool, exclude: str | None = None) -> str | None:
    pool = [p for p in DRILL if p["tag"] in tags]
    if only_wrong:
        pool = [p for p in pool if P["drill"].get(p["id"], {}).get("last") is False]
    if not pool:
        return None
    # まだ正解していない問題を優先
    fresh = [p for p in pool if not P["drill"].get(p["id"], {}).get("last") and p["id"] != exclude]
    cand = fresh or [p for p in pool if p["id"] != exclude] or pool
    return random.choice(cand)["id"]


def candidates(p: dict) -> list[str]:
    """選択肢：正解の科目＋紛らわしい科目（同じ区分から）を混ぜる。問題ごとに固定。"""
    right = {a for a, _ in p["dr"] + p["cr"]}
    rnd = random.Random(p["id"])
    same = [a for a in ACCT_NAMES if a not in right and ACCOUNTS[a]["cat"] in {ACCOUNTS[r]["cat"] for r in right}]
    other = [a for a in ACCT_NAMES if a not in right and a not in same]
    picks = rnd.sample(same, min(5, len(same))) + rnd.sample(other, min(3, len(other)))
    return sorted(right | set(picks), key=ACCT_NAMES.index)


def page_drill() -> None:
    c1, c2 = st.columns([3, 1])
    tags = c1.multiselect("出題範囲", DRILL_TAGS, default=DRILL_TAGS, key="drill_tags")
    only_wrong = c2.toggle("間違えた問題だけ", key="drill_wrong")
    all_accts = st.toggle("科目を全リストから選ぶ（上級）", key="drill_all",
                          help="オフのときは、正解を含む10科目前後の候補から選びます。")
    if not tags:
        st.info("出題範囲を選んでください。")
        return
    by_id = {p["id"]: p for p in DRILL}
    cur = st.session_state.get("drill_cur")
    if cur not in by_id or by_id[cur]["tag"] not in tags:
        cur = pick_problem(tags, only_wrong)
        st.session_state.drill_cur = cur
        st.session_state.drill_n = st.session_state.get("drill_n", 0) + 1
    if cur is None:
        st.success("間違えた問題はありません 🎉")
        return
    p = by_id[cur]
    n_done = sum(1 for q in DRILL if q["tag"] in tags and P["drill"].get(q["id"], {}).get("last"))
    n_all = sum(1 for q in DRILL if q["tag"] in tags)
    st.markdown(f"<span class='muted'>範囲内の正解済み {n_done}/{n_all}</span>{bar(n_done / n_all)}",
                unsafe_allow_html=True)
    st.markdown(f"<div class='card'><span class='tag'>{p['tag']}</span><div class='q'>{p['q']}</div></div>",
                unsafe_allow_html=True)

    key = f"dr_{cur}_{st.session_state.drill_n}"
    rows = max(2, len(p["dr"]), len(p["cr"]))
    lines = entry_input(key, ACCT_NAMES if all_accts else candidates(p), rows)
    dr_sum, cr_sum = lg.side_totals(lines)
    st.markdown(f"<span class='muted'>借方合計 <b class='num'>{yen(dr_sum)}</b>　／　貸方合計 "
                f"<b class='num'>{yen(cr_sum)}</b></span>", unsafe_allow_html=True)

    checked = st.session_state.get("drill_checked") == key
    b1, b2, b3 = st.columns(3)
    if b1.button("答え合わせ", type="primary", width="stretch", disabled=checked):
        ok = lg.is_same_entry(lines, to_lines(p["dr"], p["cr"]))
        record("drill", cur, ok)
        st.session_state.drill_checked = key
        st.session_state.drill_result = ok
        st.rerun()
    if b2.button("答えを見る", width="stretch", disabled=checked):
        record("drill", cur, False)
        st.session_state.drill_checked = key
        st.session_state.drill_result = None
        st.rerun()
    if b3.button("次の問題 →", width="stretch"):
        st.session_state.drill_cur = pick_problem(tags, only_wrong, exclude=cur)
        st.session_state.drill_n += 1
        st.rerun()

    if checked:
        res = st.session_state.get("drill_result")
        if res:
            st.markdown("<p class='ok' style='font-size:1.3rem'>○ 正解！</p>", unsafe_allow_html=True)
        elif res is False:
            st.markdown("<p class='ng' style='font-size:1.3rem'>✕ 惜しい！</p>", unsafe_allow_html=True)
            if dr_sum != cr_sum:
                st.caption("借方と貸方の合計が一致していません。仕訳は必ず左右の合計が同じになります。")
        st.markdown("**正しい仕訳**")
        st.markdown(entry_html(p["dr"], p["cr"]), unsafe_allow_html=True)
        st.markdown(f"<div class='card'>💡 {p['exp']}</div>", unsafe_allow_html=True)
        for a in dict.fromkeys(a for a, _ in p["dr"] + p["cr"]):
            info = ACCOUNTS[a]
            st.markdown(f"<span class='muted'>{cat_dot(a)}<b>{a}</b>（{info['cat']}）… {info['desc']}</span>",
                        unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 科目クイズ（どの区分？）
# ─────────────────────────────────────────────
def page_acct_quiz() -> None:
    st.markdown("<p class='muted'>表示された勘定科目は、5つの要素のどれ？</p>", unsafe_allow_html=True)
    if "aq" not in st.session_state:
        st.session_state.aq = random.choice(ACCT_NAMES)
        st.session_state.aq_ans = None
    a = st.session_state.aq
    ok, n = accuracy("acct")
    st.markdown(f"<span class='muted'>正答 {ok}/{n}</span>", unsafe_allow_html=True)
    st.markdown(f"<div class='card' style='text-align:center'><div class='q' style='font-size:1.8rem'>{a}</div></div>",
                unsafe_allow_html=True)
    cols = st.columns(5)
    answered = st.session_state.aq_ans is not None
    for c, cat in zip(cols, lg.CATS):
        if c.button(cat, key=f"aq_{cat}", width="stretch", disabled=answered):
            st.session_state.aq_ans = cat
            record("acct", a, cat == ACCOUNTS[a]["cat"])
            st.rerun()
    if answered:
        right = ACCOUNTS[a]["cat"]
        if st.session_state.aq_ans == right:
            st.markdown(f"<span class='ok'>○ 正解：{right}</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"<span class='ng'>✕ 正解は「{right}」</span>", unsafe_allow_html=True)
        info = ACCOUNTS[a]
        st.markdown(f"<div class='card'>{info['desc']}<br><span class='muted'>例：{info['ex']}　／　"
                    f"増えたら{CAT_INFO[right]['side']}</span></div>", unsafe_allow_html=True)
        if st.button("次へ →", type="primary", width="stretch"):
            # 間違えた科目は出やすくする
            weights = [1 + 3 * P["acct"].get(x, {}).get("ng", 0) - (2 if P["acct"].get(x, {}).get("last") else 0)
                       for x in ACCT_NAMES]
            nxt = random.choices(ACCT_NAMES, weights=[max(1, w) for w in weights])[0]
            st.session_state.aq = nxt if nxt != a else random.choice(ACCT_NAMES)
            st.session_state.aq_ans = None
            st.rerun()


# ─────────────────────────────────────────────
# 用語クイズ
# ─────────────────────────────────────────────
def page_terms() -> None:
    if "tq" not in st.session_state:
        st.session_state.tq_order = random.sample(range(len(TERMS)), len(TERMS))
        st.session_state.tq = 0
    i = st.session_state.tq
    if i >= len(TERMS):
        ok = sum(1 for k in st.session_state.tq_order if P["terms"].get(str(k), {}).get("last"))
        st.markdown(f"### 1周終了！ 直近の結果 {ok}/{len(TERMS)}")
        if st.button("もう一度（シャッフル）", type="primary"):
            del st.session_state["tq"]
            st.rerun()
        return
    k = st.session_state.tq_order[i]
    t = TERMS[k]
    st.markdown(f"<span class='muted'>{i + 1} / {len(TERMS)}</span>{bar(i / len(TERMS))}", unsafe_allow_html=True)
    st.markdown(f"<div class='card'><div class='q'>{t['q']}</div></div>", unsafe_allow_html=True)
    ans = st.radio("選択肢", t["choices"], index=None, key=f"tq_{k}_{i}", label_visibility="collapsed")
    done_key = f"tq_done_{k}_{i}"
    if ans is not None:
        ok = t["choices"].index(ans) == t["a"]
        if done_key not in st.session_state:
            st.session_state[done_key] = True
            record("terms", str(k), ok)
        if ok:
            st.markdown(f"<span class='ok'>○ 正解</span>　{t['exp']}", unsafe_allow_html=True)
        else:
            st.markdown(f"<span class='ng'>✕ 不正解</span>　正解は「{t['choices'][t['a']]}」。{t['exp']}",
                        unsafe_allow_html=True)
        if st.button("次へ →", type="primary", width="stretch"):
            st.session_state.tq += 1
            st.rerun()


# ─────────────────────────────────────────────
# 帳簿づくり（仕訳 → 元帳 → 試算表 → 決算書）
# ─────────────────────────────────────────────
SAMPLE = [
    ("04-01", "会社設立・出資", [("普通預金", 1000000)], [("資本金", 1000000)]),
    ("04-03", "銀行から借入", [("普通預金", 500000)], [("借入金", 500000)]),
    ("04-05", "PC購入（翌月払い）", [("備品", 240000)], [("未払金", 240000)]),
    ("04-10", "商品仕入（掛）", [("仕入", 300000)], [("買掛金", 300000)]),
    ("04-15", "商品売上（掛）", [("売掛金", 700000)], [("売上", 700000)]),
    ("04-25", "給料支給", [("給料", 200000)], [("預り金", 30000), ("普通預金", 170000)]),
    ("04-28", "家賃支払い", [("支払家賃", 80000)], [("普通預金", 80000)]),
    ("04-30", "売掛金入金", [("普通預金", 500000)], [("売掛金", 500000)]),
    ("04-30", "買掛金支払い", [("買掛金", 300000)], [("普通預金", 300000)]),
    ("04-30", "減価償却（月割）", [("減価償却費", 5000)], [("備品", 5000)]),
]


def page_books() -> None:
    st.markdown("<p class='muted'>自分で取引を仕訳すると、総勘定元帳・試算表・損益計算書・貸借対照表が自動でできあがります。"
                "1つの仕訳が帳簿全体にどう流れるかを体験しましょう。</p>", unsafe_allow_html=True)
    J: list = P["journal"]

    with st.expander("➕ 仕訳を追加する", expanded=not J):
        c1, c2 = st.columns([1, 2])
        d = c1.text_input("日付", value=date.today().strftime("%m-%d"), key="bk_date")
        memo = c2.text_input("摘要（取引の内容）", key="bk_memo", placeholder="例：文房具を購入")
        n = st.session_state.get("bk_n", 0)
        lines = entry_input(f"bk_{n}", ACCT_NAMES, rows=2)
        dr, cr = lg.side_totals(lines)
        st.markdown(f"<span class='muted'>借方 <b class='num'>{yen(dr)}</b>　貸方 <b class='num'>{yen(cr)}</b></span>",
                    unsafe_allow_html=True)
        if st.button("仕訳帳に記入", type="primary"):
            if not lines:
                st.error("科目と金額を入力してください。")
            elif dr != cr:
                st.error("借方と貸方の合計が一致していません。")
            elif not any(l["side"] == "借方" for l in lines) or not any(l["side"] == "貸方" for l in lines):
                st.error("借方・貸方の両方に入力してください。")
            else:
                J.append({"date": d, "memo": memo, "lines": lines})
                st.session_state.bk_n = n + 1
                st.rerun()
    c1, c2 = st.columns(2)
    if c1.button("サンプル取引（4月の1か月分）を読み込む", width="stretch"):
        P["journal"] = [{"date": d, "memo": m, "lines": to_lines(dr, cr)} for d, m, dr, cr in SAMPLE]
        st.rerun()
    if J and c2.button("すべて消す", width="stretch"):
        P["journal"] = []
        st.rerun()
    if not J:
        st.info("まだ仕訳がありません。上で入力するか、サンプルを読み込んでください。")
        return

    tabs = st.tabs(["仕訳帳", "総勘定元帳", "試算表", "損益計算書", "貸借対照表"])
    with tabs[0]:
        for i, e in enumerate(J):
            dr_l = [(l["acct"], l["amount"]) for l in e["lines"] if l["side"] == "借方"]
            cr_l = [(l["acct"], l["amount"]) for l in e["lines"] if l["side"] == "貸方"]
            c1, c2 = st.columns([6, 1])
            c1.markdown(f"<span class='muted'>{e['date']}　{e['memo']}</span>{entry_html(dr_l, cr_l)}",
                        unsafe_allow_html=True)
            if c2.button("削除", key=f"del_{i}"):
                J.pop(i)
                st.rerun()
    with tabs[1]:
        used = [a for a in ACCT_NAMES if any(l["acct"] == a for e in J for l in e["lines"])]
        a = st.selectbox("勘定科目", used, key="bk_ledger")
        rows = lg.ledger(J, a)
        st.caption(f"{a}（{ACCOUNTS[a]['cat']}）— 増えたら{CAT_INFO[ACCOUNTS[a]['cat']]['side']}に記入")
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                     column_config={k: st.column_config.NumberColumn(format="localized") for k in ["借方", "貸方", "残高"]})
    with tabs[2]:
        tb = lg.trial_balance(J)
        df = pd.DataFrame(tb)
        tot_dr, tot_cr = int(df["借方残高"].sum()), int(df["貸方残高"].sum())
        st.dataframe(df, hide_index=True, width="stretch",
                     column_config={k: st.column_config.NumberColumn(format="localized") for k in ["借方残高", "貸方残高"]})
        mark = "<span class='ok'>一致 ✓</span>" if tot_dr == tot_cr else "<span class='ng'>不一致</span>"
        st.markdown(f"借方合計 <b class='num'>{yen(tot_dr)}</b> ／ 貸方合計 <b class='num'>{yen(tot_cr)}</b>　{mark}",
                    unsafe_allow_html=True)
        st.caption("試算表の借方合計と貸方合計は必ず一致します（仕訳ごとに左右が一致しているため）。")
    S = lg.statements(J)
    with tabs[3]:
        rows = [f"<tr><td>{cat_dot(a)}{a}</td><td class='amt'>{yen(v)}</td></tr>" for a, v in S["by"]["収益"].items()]
        rows.append(f"<tr><td><b>収益合計</b></td><td class='amt'><b>{yen(S['revenue'])}</b></td></tr>")
        rows += [f"<tr><td>{cat_dot(a)}{a}</td><td class='amt'>△{yen(v)}</td></tr>" for a, v in S["by"]["費用"].items()]
        rows.append(f"<tr><td><b>費用合計</b></td><td class='amt'><b>△{yen(S['expense'])}</b></td></tr>")
        cls = "ok" if S["net_income"] >= 0 else "ng"
        rows.append(f"<tr><td><b>当期純利益</b></td><td class='amt {cls}'>{yen(S['net_income'])}</td></tr>")
        st.markdown("<table class='je'>" + "".join(rows) + "</table>", unsafe_allow_html=True)
        st.caption("収益 − 費用 ＝ 当期純利益（マイナスなら当期純損失）")
    with tabs[4]:
        left = [f"<tr><td>{cat_dot(a)}{a}</td><td class='amt'>{yen(v)}</td></tr>" for a, v in S["by"]["資産"].items()]
        left.append(f"<tr><td><b>資産合計</b></td><td class='amt'><b>{yen(S['assets'])}</b></td></tr>")
        right = [f"<tr><td>{cat_dot(a)}{a}</td><td class='amt'>{yen(v)}</td></tr>" for a, v in S["by"]["負債"].items()]
        right.append(f"<tr><td>負債合計</td><td class='amt'>{yen(S['liabilities'])}</td></tr>")
        right += [f"<tr><td>{cat_dot(a)}{a}</td><td class='amt'>{yen(v)}</td></tr>" for a, v in S["by"]["純資産"].items()]
        right.append(f"<tr><td>当期純利益</td><td class='amt'>{yen(S['net_income'])}</td></tr>")
        right.append(f"<tr><td><b>負債・純資産合計</b></td><td class='amt'><b>"
                     f"{yen(S['liabilities'] + S['equity'] + S['net_income'])}</b></td></tr>")
        c1, c2 = st.columns(2)
        c1.markdown("**資産の部**<table class='je'>" + "".join(left) + "</table>", unsafe_allow_html=True)
        c2.markdown("**負債・純資産の部**<table class='je'>" + "".join(right) + "</table>", unsafe_allow_html=True)
        st.caption("損益計算書の当期純利益が純資産に加わることで、資産 ＝ 負債 ＋ 純資産 が成り立ちます。"
                   + ("（一致 ✓）" if S["balanced"] else ""))


# ─────────────────────────────────────────────
# 経理カレンダー
# ─────────────────────────────────────────────
def page_calendar() -> None:
    st.markdown("<p class='muted'>経理の仕事は「いつまでに何をするか」が決まっています。チェックしながら流れを覚えましょう。</p>",
                unsafe_allow_html=True)
    for cycle, items in ROUTINE.items():
        st.markdown(f"#### {cycle}の仕事")
        done = 0
        for j, it in enumerate(items):
            k = f"{cycle}{j}"
            v = st.checkbox(it, value=P["routine"].get(k, False), key=f"rt_{k}")
            P["routine"][k] = v
            done += v
        st.markdown(bar(done / len(items)), unsafe_allow_html=True)
    st.markdown("#### 年間スケジュール（3月決算の会社の例）")
    this_month = date.today().month
    for m, text in ANNUAL:
        hl = " style='border-color:var(--lime)'" if m == this_month else ""
        st.markdown(f"<div class='card'{hl}><b class='num'>{m}月</b>　{text}</div>", unsafe_allow_html=True)
    st.caption("※ 期限は原則的なもの。土日祝の場合は翌営業日。会社の決算月・規模・特例の有無で変わります。")


# ─────────────────────────────────────────────
# 科目辞典
# ─────────────────────────────────────────────
def page_dict() -> None:
    q = st.text_input("検索", placeholder="科目名や内容で検索（例：家賃、税）", key="dict_q")
    cats = st.segmented_control("区分", lg.CATS, selection_mode="multi", default=lg.CATS, key="dict_cats")
    for cat in lg.CATS:
        if cat not in (cats or []):
            continue
        hits = [a for a in ACCT_NAMES if ACCOUNTS[a]["cat"] == cat
                and (not q or q in a or q in ACCOUNTS[a]["desc"] or q in ACCOUNTS[a]["ex"])]
        if not hits:
            continue
        info = CAT_INFO[cat]
        st.markdown(f"#### <span class='cat' style='background:{info['color']}'></span>{cat}"
                    f"<span class='muted'>　増えたら{info['side']}・{info['desc']}</span>", unsafe_allow_html=True)
        for a in hits:
            x = ACCOUNTS[a]
            st.markdown(f"<div class='card'><h4>{a}</h4>{x['desc']}<br><span class='muted'>例：{x['ex']}</span></div>",
                        unsafe_allow_html=True)


# ─────────────────────────────────────────────
# キャリアモード（新入社員 → 経理部長）
# ─────────────────────────────────────────────
def stage_max(stage: dict) -> int:
    return sum(max(p for _, p, _ in e["choices"]) for e in stage["events"])


CAREER_MAX = sum(stage_max(s) for s in CAREER)


def page_career() -> None:
    C = P["career"]
    ranks = "".join(
        f"<span class='{'done' if i < C['stage'] or C['done'] else 'now' if i == C['stage'] else ''}'>{s['icon']} {s['rank']}</span>"
        for i, s in enumerate(CAREER))
    st.markdown(f"<div class='ladder'>{ranks}</div>", unsafe_allow_html=True)

    def restart() -> None:
        P["career"] = new_career()

    if C["done"]:
        pct = C["total"] / CAREER_MAX * 100
        title, msg = next((t, m) for th, t, m in STORY_RANKS if pct >= th)
        st.markdown(f"<div class='card' style='text-align:center'><div class='muted'>キャリア達成！ 最終評価</div>"
                    f"<div style='font-size:2rem;font-weight:900;margin:6px 0'>{title}</div>"
                    f"<div class='pts'>信頼度 {C['total']} / {CAREER_MAX}</div><p>{msg}</p>"
                    f"<span class='muted'>昇進見送り {C['retries']} 回</span></div>", unsafe_allow_html=True)
        miss = [(k, v) for k, v in P["story"].items() if v["last"] is False]
        if miss:
            st.markdown("#### 判断を誤った論点（講座・証憑チェックで復習しよう）")
            st.markdown("　".join(f"<span class='tag'>{k}</span>" for k, _ in miss), unsafe_allow_html=True)
        st.button("もう一度、新入社員からやり直す", type="primary", width="stretch", on_click=restart)
        return

    stage = CAREER[C["stage"]]
    evs = stage["events"]
    need = int(stage_max(stage) * PROMOTE_RATIO)

    # 導入
    if C["i"] == -1:
        st.markdown(f"<div class='card'><div class='muted'>{stage['years']}</div>"
                    f"<div style='font-size:1.6rem;font-weight:900'>{stage['icon']} {stage['rank']}編</div>"
                    f"<p>{stage['intro']}</p><span class='muted'>{len(evs)}つの場面で判断を下そう。"
                    f"信頼度 {need} 以上で昇進！</span></div>", unsafe_allow_html=True)

        def begin() -> None:
            C.update(i=0, pts=0, picked=None)
        st.button("業務を始める →", type="primary", width="stretch", on_click=begin)
        if C["stage"] > 0 or C["total"]:
            st.button("最初からやり直す", on_click=restart)
        return

    # 評価（昇進判定）
    if C["i"] >= len(evs):
        ok = C["pts"] >= need
        st.markdown(f"<span class='muted'>{stage['rank']}編の評価</span>", unsafe_allow_html=True)
        st.markdown(f"<div class='pts'>信頼度 {C['pts']} / {stage_max(stage)}（昇進ライン {need}）</div>"
                    f"{bar(C['pts'] / stage_max(stage))}", unsafe_allow_html=True)
        if ok:
            last = C["stage"] == len(CAREER) - 1
            if last:
                st.markdown("<div class='card'><h4>🎉 経理部長として、数々の試練を乗り越えた！</h4></div>",
                            unsafe_allow_html=True)
            else:
                nxt = CAREER[C["stage"] + 1]
                st.markdown(f"<div class='card' style='text-align:center'><div class='muted'>辞令</div>"
                            f"<div style='font-size:1.5rem;font-weight:900'>{stage['rank']} → {nxt['icon']} {nxt['rank']}</div>"
                            f"<p>あなたの仕事ぶりが評価され、昇進が決まりました！</p></div>", unsafe_allow_html=True)
            if st.session_state.get("_balloon") != (C["stage"], C["retries"]):
                st.session_state._balloon = (C["stage"], C["retries"])
                st.balloons()

            def promote() -> None:
                C["total"] += C["pts"]
                if C["stage"] == len(CAREER) - 1:
                    C["done"] = True
                else:
                    C.update(stage=C["stage"] + 1, i=-1, pts=0, picked=None)
            st.button("結果を見る →" if last else "次のステージへ →", type="primary", width="stretch", on_click=promote)
        else:
            st.markdown("<div class='card'><h4>😣 今回は昇進見送り…</h4>"
                        "<span class='muted'>上司からのひとこと：「判断の根拠をもう一度見直してみよう」"
                        "解説の「実務ポイント」を思い出して再挑戦！</span></div>", unsafe_allow_html=True)

            def retry() -> None:
                C.update(i=-1, pts=0, picked=None, retries=C["retries"] + 1)
            st.button("このステージに再挑戦", type="primary", width="stretch", on_click=retry)
        return

    # イベント
    e = evs[C["i"]]
    st.markdown(f"<span class='muted'>{stage['icon']} {stage['rank']}編　{C['i'] + 1}/{len(evs)}</span>"
                f"{bar(C['pts'] / max(1, need))}<span class='muted'>信頼度 <b class='num'>{C['pts']}</b>"
                f"（昇進ライン {need}）</span>", unsafe_allow_html=True)
    st.markdown(f"<div class='card'><div class='who'><div class='ic'>{e['icon']}</div><div>"
                f"<div class='nm'>{e['who']}　<span class='tag'>{e['tag']}</span></div>"
                f"<div class='q'>{e['text']}</div></div></div></div>", unsafe_allow_html=True)
    order = list(range(len(e["choices"])))
    random.Random(e["tag"] + str(C["retries"])).shuffle(order)

    if C["picked"] is None:
        for k in order:
            def pick(k: int = k) -> None:
                pts = e["choices"][k][1]
                C["picked"] = k
                C["pts"] += pts
                record("story", e["tag"], pts > 0 and pts == max(p for _, p, _ in e["choices"]))
            st.button(e["choices"][k][0], key=f"cv_{C['stage']}_{C['i']}_{k}", width="stretch", on_click=pick)
        return

    text, pts, fb = e["choices"][C["picked"]]
    best = max(p for _, p, _ in e["choices"])
    color = "var(--ok)" if pts == best else "var(--ng)" if pts < 0 else "#f5b83d"
    st.markdown(f"<div class='muted'>あなたの判断：{text}</div>"
                f"<div class='pts' style='color:{color}'>信頼度 {pts:+d}</div><p>{fb}</p>", unsafe_allow_html=True)
    if pts != best:
        right = next(t for t, p, _ in e["choices"] if p == best)
        st.markdown(f"<span class='muted'>ベストな判断：</span>{right}", unsafe_allow_html=True)
    st.markdown(f"<div class='point'>📌 <b>実務ポイント</b><br>{e['point']}</div>", unsafe_allow_html=True)

    def nxt() -> None:
        C.update(i=C["i"] + 1, picked=None)
    st.button("次へ →", type="primary", width="stretch", on_click=nxt)


# ─────────────────────────────────────────────
# 証憑チェック
# ─────────────────────────────────────────────
def page_docs() -> None:
    st.markdown("<p class='muted'>回ってきた書類をチェックしよう。問題があるものをすべて選んでください（問題がない場合もあります）。</p>",
                unsafe_allow_html=True)
    done = sum(1 for d in DOCS if P["docs"].get(d["id"], {}).get("last"))
    st.markdown(f"<span class='muted'>正解済み {done}/{len(DOCS)}</span>{bar(done / len(DOCS))}", unsafe_allow_html=True)
    i = st.session_state.setdefault("doc_i", 0) % len(DOCS)
    d = DOCS[i]
    rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in d["fields"])
    st.markdown(f"<div class='paper'><div class='kind'>{d['kind']}</div><div class='sub'>{d['title']}</div>"
                f"<table>{rows}</table></div>", unsafe_allow_html=True)
    n = st.session_state.get("doc_n", 0)
    picked = {j for j, iss in enumerate(d["issues"]) if st.checkbox(iss, key=f"doc_{d['id']}_{n}_{j}")}
    shown = st.session_state.get("doc_shown") == (d["id"], n)
    c1, c2 = st.columns(2)
    if c1.button("判定する", type="primary", width="stretch", disabled=shown):
        record("docs", d["id"], picked == d["answer"])
        st.session_state.doc_shown = (d["id"], n)
        st.rerun()

    def go_next() -> None:
        st.session_state.doc_i = i + 1
        st.session_state.doc_n = n + 1
    c2.button("次の書類 →", width="stretch", on_click=go_next)
    if shown:
        if picked == d["answer"]:
            st.markdown("<p class='ok' style='font-size:1.2rem'>○ 見抜けました！</p>", unsafe_allow_html=True)
        else:
            st.markdown("<p class='ng' style='font-size:1.2rem'>✕ おしい！</p>", unsafe_allow_html=True)
        st.markdown("**正解：** " + " ／ ".join(d["issues"][j] for j in sorted(d["answer"])))
        st.markdown(f"<div class='point'>📌 {d['exp']}</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 入金消込パズル
# ─────────────────────────────────────────────
def page_match() -> None:
    st.markdown("<p class='muted'>通帳に入金がありました。どの請求書の入金かを特定し、処理方法を選ぼう。</p>",
                unsafe_allow_html=True)
    lv = st.selectbox("レベル", range(len(MATCH_SETS)), key="match_lv",
                      format_func=lambda k: MATCH_SETS[k]["title"]
                      + (f"（ベスト {P['match'][MATCH_SETS[k]['title']]}/{len(MATCH_SETS[k]['deposits'])}）"
                         if MATCH_SETS[k]["title"] in P["match"] else ""))
    S = MATCH_SETS[lv]
    st.markdown("**未入金の請求（売掛金）**")
    st.dataframe(pd.DataFrame([{"請求番号": a, "取引先": b, "請求額": c} for a, b, c in S["invoices"]]),
                 hide_index=True, width="stretch", column_config={"請求額": st.column_config.NumberColumn(format="localized")})
    inv_ids = [a for a, _, _ in S["invoices"]]
    n = st.session_state.get("match_n", 0)
    answers = []
    st.markdown("**通帳の入金明細**")
    for j, (name, amt, _, _, _) in enumerate(S["deposits"]):
        st.markdown(f"<div class='card' style='margin-bottom:4px'>🏦 振込 <b class='dep'>{name}</b>　"
                    f"<b class='dep'>¥{yen(amt)}</b></div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        sel = c1.multiselect("対応する請求", inv_ids, key=f"m_{lv}_{n}_{j}_i", placeholder="請求番号を選ぶ（不明なら空欄）")
        act = c2.selectbox("処理", MATCH_ACTIONS, key=f"m_{lv}_{n}_{j}_a", index=None, placeholder="処理を選ぶ")
        if sel:
            tot = sum(c for a, _, c in S["invoices"] if a in sel)
            diff = amt - tot
            st.caption(f"選んだ請求の合計 ¥{yen(tot)}　差額 {diff:+,}円")
        answers.append((set(sel), act))
    shown = st.session_state.get("match_shown") == (lv, n)
    c1, c2 = st.columns(2)
    if c1.button("答え合わせ", type="primary", width="stretch", disabled=shown):
        st.session_state.match_shown = (lv, n)
        st.rerun()

    def reset() -> None:
        st.session_state.match_n = n + 1
    c2.button("やり直す", width="stretch", on_click=reset)
    if shown:
        score = 0
        for (name, amt, right, act_i, exp), (sel, act) in zip(S["deposits"], answers):
            want = MATCH_ACTIONS[act_i]
            # 「確認」する入金は、候補の請求を選んでいても空欄でも可
            ok_inv = sel == right or (act_i == 2 and (not sel or sel == right))
            ok = ok_inv and act == want
            score += ok
            mark = "<span class='ok'>○</span>" if ok else "<span class='ng'>✕</span>"
            right_txt = "・".join(sorted(right)) or "該当なし"
            st.markdown(f"{mark} <b>{name}</b> ¥{yen(amt)} → 正解：{right_txt}／{want}<br>"
                        f"<span class='muted'>{exp}</span>", unsafe_allow_html=True)
        st.markdown(f"<div class='pts'>{score} / {len(S['deposits'])}</div>", unsafe_allow_html=True)
        if score > P["match"].get(S["title"], -1):
            P["match"][S["title"]] = score
        if score == len(S["deposits"]):
            st.balloons()


{
    "ホーム": page_home, "キャリア": page_career, "証憑チェック": page_docs, "入金消込": page_match, "講座": page_lessons, "仕訳ドリル": page_drill, "科目クイズ": page_acct_quiz,
    "用語クイズ": page_terms, "帳簿づくり": page_books, "経理カレンダー": page_calendar, "科目辞典": page_dict,
}[page]()

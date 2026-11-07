"""短期トレード・ラボ（Streamlit）

起動:  streamlit run app.py
"""
from __future__ import annotations

import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import backtest as bt
import charts
import data
import events as ev
import indicators as ind
import journal
import storage
import papertrade as pt
import forward as fw
import market as mk
import setups as su
import strategies as strat

UP, DOWN = charts.UP, charts.DOWN
# Streamlitのバージョン差を吸収（古い版は plotly_chart に width 指定ができない）
import inspect as _inspect
PKW = {"width": "stretch"} if "width" in _inspect.signature(st.plotly_chart).parameters else {"use_container_width": True}
JST = ZoneInfo("Asia/Tokyo")
LOGO_B64 = "iVBORw0KGgoAAAANSUhEUgAAAEgAAABICAMAAABiM0N1AAABgFBMVEU3MppkV5OhnNRJK6JxaufKrnA0N3cpKnA/P785L8E/QJBCP7VgN9NiPeFRQHhGRKlIRKiAboy8tbnx0GLh3s5WQ+U2NZE7N6xKQtJBPLRHQq9iQOhDPMX81UwAAAEyNHtmPuhLQ5YuLoj29ftFPpjwylI7NMXo5/GMiNKPd3LYtVhsZ86liWtoV4m0mGl3ZorHqGXDu63Kw7XPzMza2ewPBiURCyswKrN7ZXjZ19QAAH9hXMx6dtXjx24tLnw7O35SOctcVsaKepDJqVwCAQUXFzZHRK+BfNa8uujIt5DKye7/4kdLQNJpV31jW7CFfKqWhYuLhLabl+Wpoq8AAP8cHFIwNHQ1OHlCOrZFO+JVVVVkO96EbHSWktvhvVfg3u4gE0wjI1goKGosLXYzNHMwM3M7NKtPL61WM8FFPspERKVFQq5VVapaVbl9d7CYgnaYk7ezlV+ol46zpZm3tNLcwnTSwIwTDzkAAFUVET0AKionEzohEkIjI14qKmcpK2zlT0Q4AAAAgHRSTlNo//9v//9vlQT//qC81/90jf/////+/v7+/v7+/v8E/v3+/v///////////////////////xEx////Av////kJsv///ygNzP//////0/////////8BD5XOkv8D1/////86DhPPTb2GhJfVUqQD/////////////0IDOgYNRU5bdrdcRvIAAAThSURBVHjardhnW9tIEADgheR6L9KqLpaRLbnhigtgMDa9l0AggUvvl16uX/76za4kq2Bbsrn5hAG9z8zs7kgWIlbcIOTP+8fXJ6zgg/GlFghJkla+f3pEyIINIMe586mj9HBo6H6Gxcp3C+TXay40Q8j96/xgByQ9wLB4yi63oBmyfDwxEeZ0Kckfz+4yCaCZa0cPIjlU0nUpGCsLVALoxvKDaAx1RPECJKzcgT4haPsxH80BSRR7Sc8AQQvk34moDo9FsRclIPI5+n05soMhekvS3RlEPvLRGQcKUsIJQcv3hnFcSfT3+wj9M5zTG4Iuoc/4+fnojOt4LUEQvkL3+GGcgIQdR9hC83z4oveBsPhyCluOIKD5+fgQjAfi+VR60wPFIaIzXQjjXEFV1RS2HQuKD+9oUyqNfDSoHyPhvLrJoDEs+qB4JMaB4Ac7oYQmhkIY94NwxoS5m6ZQAYtKCIT7QzXzHa9lqQOLJgh+KB7JsTMyD/k6MJ2UupcMQNHToRm9OPz2F+jPNp/bUXxQtGycfKSdV4ev6RbSJew6AA1EAkcULsDmz8UP4EzB7UQQvFC8H3PhmNP/l/Cr0npCVdMBJywjn6soCpS2X2pCQnW4Dyg+KHJzFIVB/B51CprkdzhPRmHZMEfU98D56Y0Ov/EwHIcGMLUAQyGNbunEh0Ovw3Eu1DOPjGTX5Tq6Trf0J6VxtzCOc6E+BVXmat3mJG2Ibulmsfwu6FCoX1/wxly3quTsolUY3dLrpcaa4mco1LfDNcgI20Ul5zJJBRw6PdaLZWND8TMA9XXGK0ZlYzHpQlBYCpz3xXJjkkIc1xeChjyXrK0sCsYkhOkc77mMJGnbdEu3fyxXjIMAE4SwdGvRPhpeSJk7ME1zR+vQLa2JJnSIGwhhBllkF6KVrQK0n0+pCTWrSV+MryW5EKiGK0LNWnEPJCir5+b+bhsK68ATZPJg4zQMOl8z1s6t9gJkGE5pq6a526Yrn4MZoFy9yg2ERLxIk5jMsDUXKoZRMWhGDNpts/shnR3c6WkYNGtBdMmxVG6Uy41VigpKZn/3DT0abAZxPaM3RCdqsVQsll7ARhDplv4hYRfWx/FAYheiG0DX3jYTzeaeptEHa02jhZ0NcLoQXSoGGQzStVSC3UrT2To87I+l2JQe4NiQteJJgAzD2MGavt1Ru5HOnqXYlJaUEKg7KjLgVBpjei5L00k0C2mLStCP+UGFUcgdXMlZ41ajXMqfses79bd5rZ61LLalBzkccuefgheBKa4X2JUp62uQpuWptVkYsPI21HVE/LxRKr5nGUzlgIE/OVY2zOGQ68Buaa+ztUrXGWNPELBgroQ4MvIO9u3XrMkvNeeuxfluXYMcL2RvHVaVd5KGO7LsQqKY63SbzNLhooYs+yBc2EyoiayTzpCMDcGgUHDOU9XQDIWsDkBK7TycT1EYwpE9gZ7YvYScxJGaY8U36ETwx0hMTG4h9D8wsZh8BVWfcJdmYnKsishDbjjkIgPQY3iBUKUHYUTGcWK34Vs2QZxwKQagR+QvRKZJ6zJVUae1NM1e+1S3LsPE5JtV50XUH1ujM+DchqoYNE2qrVGZmPx1lTrOO7alhyP0GBQ59miJOQ5EyG8nQ/cGPjz+m/jf+lF1CbW2hsgmdrN1pWqnQwj5D/i9NMVu20JSAAAAAElFTkSuQmCC"
try:
    import base64 as _b64, io as _io
    from PIL import Image as _Image
    _icon = _Image.open(_io.BytesIO(_b64.b64decode(LOGO_B64)))
except Exception:
    _icon = "📈"
st.set_page_config(page_title="短期トレード・ラボ", page_icon=_icon, layout="wide")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap');
html, body, [class*="css"], .stMarkdown, button, input, textarea, select {font-family: "Noto Sans JP", -apple-system, "Hiragino Sans", sans-serif;}
/* 上の余白：Streamlitのヘッダー（透明）の下に隠れないように */
header[data-testid="stHeader"] {background: transparent; height: 2.6rem;}
.block-container {padding-top: 3.0rem; padding-bottom: 3rem; max-width: 1320px;}
/* 上部のブランドバー */
.tl-brand {display:flex; align-items:center; justify-content:space-between; gap:12px; margin: 0 0 10px 0;}
.tl-brand .logo {display:flex; align-items:center; gap:10px; font-weight:700; font-size:1.15rem; color:#1f2430;}
.tl-brand .logo img {width:30px; height:30px; border-radius:8px;}
.tl-brand .meta {font-size:.82rem; color:#6b7280; text-align:right;}
.tl-brand .meta b {color:#1f2430; font-variant-numeric: tabular-nums;}
/* ページ切り替え：スクロールしても上に残る */
.st-key-topnav {position: sticky; top: 2.6rem; z-index: 50; background: var(--tl-bg, #f6f7fb); padding: 6px 0 8px 0;
  border-bottom: 1px solid rgba(31,36,48,.08); margin-bottom: 6px;}
.st-key-topnav [data-testid="stButtonGroup"] {flex-wrap: wrap;}
.st-key-topnav button {border-radius: 999px !important; padding: 4px 14px !important;}
/* カード（枠つきコンテナ）を白いカードに */
[data-testid="stVerticalBlockBorderWrapper"] {background:#ffffff; border-radius:14px !important; border-color: rgba(31,36,48,.08) !important;
  box-shadow: 0 1px 2px rgba(16,24,40,.04), 0 2px 8px rgba(16,24,40,.04);}
[data-testid="stExpander"] details {background:#ffffff; border-radius:12px; border-color: rgba(31,36,48,.08);}
[data-testid="stMetric"] {background:#ffffff; border:1px solid rgba(31,36,48,.08); border-radius:12px; padding:8px 14px;}
[data-testid="stMetricValue"] {font-size: 1.3rem; font-weight:700;}
[data-testid="stMetricLabel"] {color:#6b7280;}
h1, h2 {letter-spacing: .01em; font-weight: 700 !important;}
h2 {font-size: 1.75rem !important;}
.st-key-topnav [data-testid="stButtonGroup"] > div {gap: 6px;}
[data-testid="stSidebar"] {background:#ffffff; border-right:1px solid rgba(31,36,48,.06);}
[data-testid="stSidebar"] h1 {font-size: 1.15rem !important;}
.stButton > button, .stDownloadButton > button {border-radius: 10px;}
.plan-row {display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid rgba(128,128,128,.18); font-size:0.98rem;}
.plan-row b {font-variant-numeric: tabular-nums;}
.tag {display:inline-block; padding:1px 9px; border-radius:10px; font-size:0.8rem; margin-right:6px; background:rgba(128,128,128,.16);}
.tag-setup {background:#fde7e8; color:#b4232a;}
.stars {color:#f5a524; letter-spacing:1px;}
.tag-warn {background:#fff4d6; color:#8a5a00;}
.tag-fx {background:#e3f0ff; color:#1d5fbf;}
/* Streamlit標準の英語メニュー（Deploy・⋮・Running表示）は使わないので隠す */
[data-testid="stToolbar"], [data-testid="stAppDeployButton"], [data-testid="stMainMenu"],
[data-testid="stStatusWidget"], [data-testid="stDecoration"] {display:none !important;}
/* スマホ向け：余白と文字を小さく */
@media (max-width: 640px) {
  .block-container {padding: 3.0rem 0.6rem 2rem 0.6rem;}
  .tl-brand .meta {display:none;}
  .st-key-topnav button {padding: 2px 10px !important; font-size: .85rem;}
  h1 {font-size: 1.6rem !important;} h2 {font-size: 1.35rem !important;} h3 {font-size: 1.15rem !important;}
  h4 {font-size: 1.05rem !important;}
  [data-testid="stMetricValue"] {font-size: 1.1rem;}
  .plan-row {font-size: 0.92rem;}
}
</style>""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# パスワード（クラウドで公開するとき用：Secrets に app_password を設定すると有効）
# ---------------------------------------------------------------------------
def _password_gate():
    """ログインの確認
    ・Secrets に [auth]（GoogleのOAuth設定）と allowed_emails があれば「Googleでログイン」
      （スマホではGoogleのパスキー＝Face ID・指紋でログインできる）
    ・なければ app_password によるパスワード
    """
    try:
        sec = st.secrets
        has_auth = "auth" in sec and "allowed_emails" in sec
        pw = sec.get("app_password")
    except Exception:
        has_auth, pw = False, None
    if has_auth:
        allowed = [e.strip().lower() for e in (sec["allowed_emails"] if isinstance(sec["allowed_emails"], (list, tuple))
                                               else str(sec["allowed_emails"]).split(","))]
        if not st.user.get("is_logged_in", False):
            st.markdown("## 📈 短期トレード・ラボ")
            st.caption("登録したGoogleアカウントでログインしてください。スマホではFace IDや指紋（パスキー）でログインできます。")
            if st.button("Googleでログイン", type="primary"):
                st.login()
            st.stop()
        if str(st.user.get("email", "")).lower() not in allowed:
            st.error("このGoogleアカウントでは使えません。")
            if st.button("ログアウト"):
                st.logout()
            st.stop()
        return
    if not pw or st.session_state.get("auth_ok"):
        return
    st.markdown("## 📈 短期トレード・ラボ")
    with st.form("login"):
        v = st.text_input("パスワード", type="password")
        if st.form_submit_button("ログイン", type="primary"):
            if v == pw:
                st.session_state["auth_ok"] = True
                st.rerun()
            else:
                st.error("パスワードが違います")
    st.stop()


_password_gate()

PAGES = ["🎯 今日の狙い目", "🌏 相場環境", "📈 銘柄分析", "🎮 仮想売買", "🧪 検証", "📒 トレード記録", "❓ 使い方"]
P_PICK, P_ENV, P_AN, P_PAPER, P_VAL, P_LOG, P_HELP = PAGES
ALL_CATS = ["日本株", "米国株", "ETF", "原油", "金・貴金属"]
st.session_state.setdefault("page", PAGES[0])
st.session_state.setdefault("sym", "7203.T")


# ---------------------------------------------------------------------------
# 共通
# ---------------------------------------------------------------------------
def fmtp(v, cur):
    if v is None or not np.isfinite(v):
        return "—"
    return f"{cur}{v:,.0f}" if cur == "¥" and abs(v) >= 1000 else f"{cur}{v:,.2f}"


def yen(v):
    return f"{v:,.0f}円"


@st.cache_data(ttl=60, show_spinner=False)
def fetch(ticker, period, interval, use_yahoo):
    if not use_yahoo:
        n = {"1d": 1300 if period in ("5y", "10y") else 500, "1wk": 400}.get(interval, 3000)
        return data.demo_data(ticker, interval, n)
    return data.fetch_yahoo(ticker, period, interval)


@st.cache_data(ttl=3600, show_spinner=False)
def usdjpy(use_yahoo):
    if use_yahoo:
        try:
            return float(data.fetch_yahoo("JPY=X", "5d", "1d")["Close"].iloc[-1]), True
        except Exception:
            pass
    return 150.0, False


@st.cache_data(ttl=900, show_spinner=False)
def macro(use_yahoo):
    out, frames = {}, {}
    for name, t, _ in mk.MACRO:
        try:
            df = fetch(t, "1y", "1d", use_yahoo)
            out[name] = mk.summarize(name, df)
            frames[name] = df["Close"]
        except Exception:
            pass
    return out, frames


@st.cache_data(ttl=1800, show_spinner=False)
def get_news(ticker, use_yahoo):
    return mk.news(ticker) if use_yahoo else []


@st.cache_data(ttl=43200, show_spinner=False)
def get_earnings(ticker, use_yahoo):
    if not use_yahoo or not ticker.endswith(".T") and not ticker.isalpha():
        return None
    return mk.earnings_date(ticker)


@st.cache_data(ttl=86400, show_spinner=False)
def get_earn_hist(ticker, use_yahoo):
    return mk.earnings_history(ticker) if use_yahoo else []


_OLD = storage.DATA_DIR  # 以前の保存ファイル（Mac版）。見つかれば新しい保存先へ引き継ぐ


def _migrate_once():
    if storage.get("migrated_v1"):
        return
    import json as _j
    for key, fname in (("day_rule", "adopted_rule.json"), ("swing_rule", "adopted_swing_rule.json")):
        f = _OLD / fname
        if storage.get(key) is None and f.exists():
            try:
                storage.put(key, _j.loads(f.read_text(encoding="utf-8")))
            except Exception:
                pass
    f = _OLD / "my_watchlist.txt"
    if storage.get("watchlist") is None and f.exists():
        try:
            storage.put("watchlist", [x.strip() for x in f.read_text(encoding="utf-8").split(",") if x.strip()])
        except Exception:
            pass
    storage.put("migrated_v1", True)


try:
    _migrate_once()
except Exception:
    pass


def load_watch():
    return storage.get("watchlist", []) or []


def save_watch(items):
    try:
        storage.put("watchlist", items)
    except Exception:
        pass


# 検証済みの既定ルール（Mac版での検証結果。採用ルールが未設定のクラウド版などで使う）
VALIDATED_SWING = {"avoid_earnings": False, "filter": True, "patterns": "すべて", "stop": "標準", "target_r": None}
VALIDATED_DAY = {"stop": 4.0, "target_r": 2.0, "patterns": "売りのみ（すべて）"}


def load_rule(swing=False):
    r = storage.get("swing_rule" if swing else "day_rule")
    if r is None:
        return VALIDATED_SWING if swing else VALIDATED_DAY
    return r


def save_rule(rule, swing=False):
    try:
        storage.put("swing_rule" if swing else "day_rule", rule)
    except Exception:
        pass


def event_guide(kind):
    """経済イベントの初心者向け解説"""
    g = ev.GUIDE[kind]
    st.markdown(f"**どんな発表？**　{g['what']}")
    cols = st.columns(2)
    for col, key, color, title in ((cols[0], "strong", "#e5484d", "📈 結果が"), (cols[1], "weak", "#3e7bfa", "📉 結果が")):
        cond, chain, effects = g[key]
        with col.container(border=True):
            st.markdown(f"<span style='color:{color};font-weight:700'>{title}{cond}</span>", unsafe_allow_html=True)
            st.markdown(" → ".join(f"**{c}**" if i == len(chain) - 1 else c for i, c in enumerate(chain)))
            st.markdown("\n".join(f"- {k}：{v}" for k, v in effects.items()))
    st.markdown(f"💡 {g['point']}")
    st.markdown(f"🔑 {ev.COMMON['rule']}")
    st.markdown(f"**初心者の対処法**\n- {ev.COMMON['day']}\n- {ev.COMMON['swing']}")


def card_event_hint(item, upcoming_events):
    """この銘柄にとってイベントが追い風か逆風か（為替タグがある日本株向け）"""
    fx = item.get("fx")
    kinds = {e["kind"] for e in upcoming_events}
    if not fx or not kinds:
        return None
    yen_weak_good = fx == "円安で上がりやすい"
    tips = []
    for k in ("雇用統計", "CPI", "FOMC"):
        if k in kinds:
            nm = ev.INFO[k]["name"]
            tips.append(f"{nm}が予想より強い（円安方向）なら{'追い風' if yen_weak_good else '逆風'}、"
                        f"弱い（円高方向）なら{'逆風' if yen_weak_good else '追い風'}")
    if "日銀会合" in kinds:
        tips.append(f"日銀が利上げ・タカ派（円高方向）なら{'逆風' if yen_weak_good else '追い風'}")
    return f"この銘柄は「{fx}」タイプ：" + "。".join(tips) if tips else None


def event_notes(style):
    days = 14 if style == "スイング" else 1
    return [ev.label(e) for e in ev.upcoming(days)]


def go_analyze(ticker):
    st.session_state["page"] = P_AN
    st.session_state["sym"] = ticker


def record_plan(ticker, plan, qty, lot):
    journal.add_trade(ticker, "買い", datetime.now(JST), round(plan.entry, 2), qty or lot,
                      round(plan.stop, 2), round(plan.target, 2), 0, plan.setup, "狙い目から記録")
    st.toast(f"{data.name_of(ticker)} をトレード記録に追加しました（価格は約定値に直してください）")


# ---------------------------------------------------------------------------
# サイドバー（共通設定）
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("**⚙️ 資金と1回のリスク**")
    capital = st.number_input("1回のトレードに使う資金（万円）", 1.0, 100000.0, 50.0, 5.0) * 10000
    risk_pct = st.slider("1回の許容損失（資金の%）", 0.5, 5.0, 2.0, 0.5,
                         help="損切りになったときに失う金額の上限。初心者は1〜2%が目安です。")
    st.caption(f"→ 損切りになっても最大 **{yen(capital * risk_pct / 100)}** の損失に収まる株数を計算します。")
    st.divider()
    src = st.radio("株価データ", ["Yahoo!Finance（自動取得）", "デモデータ（練習用）"])
    use_yahoo = src.startswith("Yahoo")
    auto = st.toggle("自動更新", value=False, help="指定した間隔で画面を更新します（デイトレ向け）")
    refresh_sec = st.select_slider("更新間隔（秒）", [30, 60, 120, 300], value=120, disabled=not auto)
    st.divider()
    _b = storage.backend()
    _cloud = Path("/mount/src").exists()
    if isinstance(_b, storage.SheetsBackend):
        st.caption("💾 保存先：Googleスプレッドシート ✅")
    elif _cloud:
        st.warning("💾 保存先：クラウドの一時フォルダ（アプリが再起動すると記録が消えます）。"
                   "Googleスプレッドシートを設定すると消えなくなります。")
        if getattr(storage.LocalBackend, "error", None):
            st.caption(f"スプレッドシート接続エラー：{storage.LocalBackend.error}")
    else:
        st.caption("💾 保存先：このパソコン")
    st.caption("⚠️ 本アプリは条件に合うチャートを機械的に探す分析ツールで、投資助言ではありません。"
               "表示される価格は目安です。売買はご自身の判断と責任で行ってください。")

fx, fx_live = usdjpy(use_yahoo)
_now = datetime.now(JST)
st.markdown(
    f"<div class='tl-brand'><div class='logo'><img src='data:image/png;base64,{LOGO_B64}'>短期トレード・ラボ</div>"
    f"<div class='meta'>{_now:%m/%d}（{'月火水木金土日'[_now.weekday()]}） <b>{_now:%H:%M}</b>　ドル円 <b>{fx:,.2f}</b></div></div>",
    unsafe_allow_html=True)
with st.container(key="topnav"):
    page = st.segmented_control("ページ", PAGES, key="page", label_visibility="collapsed")
if page is None:
    page = PAGES[0]
if not use_yahoo:
    st.warning("デモデータ（架空の値動き）を表示中です。実際の株価ではありません。")


# ===========================================================================
# 🎯 今日の狙い目
# ===========================================================================
def scan_one(cat, name, t, style, use_yahoo, fxdf=None):
    out = {"cat": cat, "name": name, "ticker": t, "plans": [], "watch": None, "err": None, "df": None, "fx": None}
    try:
        cur = data.currency_of(t)
        if style == "スイング":
            df = fetch(t, "2y", "1d", use_yahoo)
            plans = su.find_plans(df, "スイング", cur)
            srule = load_rule(swing=True)
            if srule and plans:  # 検証で採用したスイングのルールを当てはめる
                atr = ind.atr(df, 14)
                keep = []
                for p_ in plans:
                    if srule["patterns"] != "すべて" and p_.setup != srule["patterns"]:
                        continue
                    if srule.get("avoid_earnings") and cat in ("日本株", "米国株", "マイ銘柄"):
                        ed_ = get_earnings(t, use_yahoo)
                        if ed_ and 0 <= (ed_ - datetime.now(JST).date()).days <= 18:
                            continue  # 保有期間中に決算発表があるので見送り
                    if srule["filter"]:
                        try:
                            ix = fetch("^N225" if t.endswith(".T") else "^GSPC", "1y", "1d", use_yahoo)["Close"]
                            if not ix.iloc[-1] > ix.rolling(50).mean().iloc[-1]:
                                continue
                        except Exception:
                            pass
                    if srule["stop"] != "標準":
                        p_.stop = p_.entry - float(srule["stop"]) * float(atr.iloc[-1])
                    if srule["target_r"] is None:
                        p_.target = p_.entry + 2 * (p_.entry - p_.stop)
                        p_.reasons.append(f"採用ルール：利確の指値は置かず、{p_.hold}の期限か損切りで手じまい（利確欄は参考値）")
                    else:
                        p_.target = p_.entry + srule["target_r"] * (p_.entry - p_.stop)
                    keep.append(p_)
                plans = keep
            out["plans"] = plans
            out["df"] = df
            if t.endswith(".T") and fxdf is not None:
                out["fx"] = mk.fx_label(mk.fx_sensitivity(df, fxdf))
        else:
            df = fetch(t, "60d", "5m", use_yahoo)
            plans = su.find_plans(df, "デイトレ", cur)
            rule = load_rule()
            if not rule:  # 採用ルールがなければ最初のルール（買いのみ）
                plans = [p_ for p_ in plans if p_.side == "買い"]
            if rule and plans:  # 検証で採用した損切り・利確ルールを当てはめる
                atr = ind.atr(df, 14)
                keep = []
                for p_ in plans:
                    if p_.setup not in pt._pattern_set(rule["patterns"]):
                        continue
                    a_ = float(atr.loc[p_.signal_time])
                    sg_ = 1 if p_.side == "買い" else -1
                    if rule["stop"] != "標準":
                        p_.stop = p_.entry - sg_ * float(rule["stop"]) * a_
                    rr_ = 2.0 if rule["target_r"] is None else rule["target_r"]
                    p_.target = p_.entry + sg_ * rr_ * abs(p_.entry - p_.stop)
                    if rule["target_r"] is None:
                        p_.reasons.append("採用ルール：利確の指値は置かず、引けまでに手じまい（利確欄は参考値）")
                    keep.append(p_)
                plans = keep
            out["plans"] = plans
            out["df"] = df
            daily = fetch(t, "6mo", "1d", use_yahoo)
            tz = JST if (t.endswith(".T") or t == "^N225") else ZoneInfo("America/New_York")
            if len(daily) and daily.index[-1].date() >= datetime.now(tz).date():
                daily = daily.iloc[:-1]  # 当日分（未確定）は除き「前日」の値を使う
            out["watch"] = su.watch_levels(daily)
    except Exception as e:
        out["err"] = str(e)[:80]
    return out


def run_scan(style, cats, extra):
    targets = data.universe(cats) + [("マイ銘柄", data.name_of(t), t) for t in extra if t not in
                                      {x[2] for x in data.universe(cats)}]
    with ThreadPoolExecutor(max_workers=8) as pool:
        try:
            fxdf = fetch("JPY=X", "2y", "1d", use_yahoo)
        except Exception:
            fxdf = None
        return list(pool.map(lambda a: scan_one(*a, style, use_yahoo, fxdf), targets))


def plan_card(rank, item, plan, style):
    t, name = item["ticker"], item["name"]
    cur = data.currency_of(t)
    tradable = data.is_tradable(t)
    lot = data.lot_of(t)
    stars = "★" * max(1, round(plan.score / 20)) + "☆" * (5 - max(1, round(plan.score / 20)))
    with st.container(border=True):
        left, right = st.columns([1.25, 1])
        with left:
            st.markdown(f"#### {rank}. {name} <span style='font-size:.8rem;color:gray'>{t}</span>", unsafe_allow_html=True)
            st.markdown(f"<span class='stars'>{stars}</span> <span style='color:gray;font-size:.85rem'>スコア {plan.score}</span>　"
                        f"<span class='tag tag-setup'>{'🔻空売り ' if plan.side == '売り' else ''}{plan.setup}</span><span class='tag'>{item['cat']}</span>"
                        f"<span class='tag'>保有 {plan.hold}</span>"
                        + (f"<span class='tag tag-fx'>💱 {item['fx']}</span>" if item.get("fx") else ""),
                        unsafe_allow_html=True)
            st.caption(su.SETUP_HELP[plan.setup])
            warns = []
            ed = get_earnings(t, use_yahoo) if tradable and item["cat"] not in ("ETF", "原油", "金・貴金属") else None
            if ed:
                days_to = (ed - datetime.now(JST).date()).days
                if 0 <= days_to <= (14 if style == "スイング" else 1):
                    warns.append(f"決算発表 {ed:%m/%d}（{days_to}日後）：決算をまたぐと大きく上下する可能性。保有するなら株数を減らすか決算前に手じまいを検討")
            ev_list = event_notes(style)
            if ev_list:
                warns.append("保有期間中の重要イベント：" + "、".join(ev_list[:3]))
                hint = card_event_hint(item, ev.upcoming(14 if style == "スイング" else 1))
                if hint:
                    warns.append(hint)
            for w in warns:
                st.markdown(f"<span class='tag tag-warn'>⚠️ {w}</span>", unsafe_allow_html=True)
            st.markdown("**狙い目の理由**")
            st.markdown("\n".join(f"- {r}" for r in plan.reasons))
            if plan.hist_n >= 3:
                good = plan.hist_avg_r > 0
                st.markdown(f"**この銘柄の過去成績**（同じパターン {plan.hist_n}回）：勝率 {plan.hist_win:.0f}% ／ "
                            f"1回平均 {plan.hist_avg_r:+.2f}R {'👍' if good else '⚠️ 成績は良くない'}")
            elif plan.hist_n > 0:
                st.markdown(f"**この銘柄の過去成績**：{plan.hist_n}回のみ（勝率 {plan.hist_win:.0f}%）※参考程度")
            else:
                st.markdown("**この銘柄の過去成績**：過去データ内に同じパターンなし")
        with right:
            short = plan.side == "売り"
            rows = [("🟠 空売り" if short else "🟠 買い", fmtp(plan.entry, cur), ""),
                    ("🔵 損切り（買い戻し）" if short else "🔵 損切り", fmtp(plan.stop, cur),
                     f"{'+' if short else '-'}{plan.risk_pct:.1f}%"),
                    ("🔴 利確（買い戻し）" if short else "🔴 利確", fmtp(plan.target, cur),
                     f"{'-' if short else '+'}{plan.reward_pct:.1f}%"),
                    ("リスクリワード", f"1 : {plan.rr:.1f}", "")]
            st.markdown("".join(f"<div class='plan-row'><span>{a}</span><span><b>{b}</b> "
                                f"<span style='color:gray;font-size:.85rem'>{c}</span></span></div>" for a, b, c in rows),
                        unsafe_allow_html=True)
            st.caption(f"📝 {plan.entry_how}")
            if tradable:
                pos = su.position(plan, t, capital, risk_pct, fx, lot)
                if pos["qty"] > 0:
                    st.success(f"**{pos['qty']:,}株** {'空売りする' if short else '買う'}場合：必要資金 約{yen(pos['cost'])}\n\n"
                               f"損切りなら −{yen(pos['loss'])}／利確なら +{yen(pos['gain'])}")
                    if short:
                        st.caption("※空売りには信用取引口座が必要です。米国株の空売りは対応していない証券会社もあります。")
                elif pos["raw"] > 0:
                    st.info(f"単元（{lot}株）だと資金か許容損失を超えます。単元未満株（S株・かぶミニ等）なら **{pos['raw']}株** が目安。")
                else:
                    st.info("この資金・許容損失では買える株数がありません。")
            else:
                st.info(f"指数・先物は直接は買えません。代わりに **{data.PROXY.get(t, '関連ETF')}** で取引できます。")
            b1, b2 = st.columns(2)
            b1.button("詳しく分析", key=f"an_{style}_{t}_{plan.setup}", on_click=go_analyze, args=(t,), width="stretch")
            if tradable:
                q = su.position(plan, t, capital, risk_pct, fx, lot)["qty"]
                b2.button("買ったら記録", key=f"rec_{style}_{t}_{plan.setup}", on_click=record_plan,
                          args=(t, plan, q, lot), width="stretch")
        with st.expander("チャートで確認"):
            st.plotly_chart(charts.plan_chart(item["df"], plan, style == "デイトレ"), **PKW,
                            key=f"pc_{style}_{t}_{plan.setup}", config={"displaylogo": False})


if page == P_PICK:
    ms = su.market_status()
    c1, c2, c3 = st.columns([2, 1, 1])
    c1.markdown("## 🎯 今日の狙い目")
    c2.metric("東証", ms["東証"])
    c3.metric("米国市場", ms["米国"], f"開始 {ms['米国_開始']}", delta_color="off")
    st.markdown(
        f"<div style='font-size:.85rem;color:gray;line-height:1.7'>🕘 <b>取引時間（日本時間）</b>　"
        f"東証：{ms['東証_時間']}　｜　米国株：{ms['米国_時間']}　｜　原油・金の先物：{ms['先物_時間']}</div>",
        unsafe_allow_html=True)

    style_label = st.segmented_control("スタイル", ["スイング（数日〜2週間）", "デイトレ（当日中）"],
                                       default="スイング（数日〜2週間）", key="style_sel")
    style = "デイトレ" if style_label and style_label.startswith("デイトレ") else "スイング"

    # 相場の天気と直近イベント
    msum, _ = macro(use_yahoo)
    if msum:
        w = mk.weather(msum)
        near = ev.upcoming(3)
        with st.container(border=True):
            a, b = st.columns([1, 2])
            a.markdown(f"#### {w['icon']} 相場の天気：{w['label']}")
            a.caption(w["advice"])
            b.markdown("**直近3日の重要イベント**：" + ("　".join(f"⚠️ {ev.label(e)}" for e in near) if near else "なし"))
            b.caption("　".join(w["notes"][:3]) + "　→ 詳しくは「🌏 相場環境」")

    with st.expander("対象銘柄・表示の設定"):
        cats = st.multiselect("カテゴリ", ALL_CATS, default=ALL_CATS)
        st.session_state.setdefault("watch_txt", ", ".join(load_watch()))
        extra_txt = st.text_input("マイ銘柄（カンマ区切り・自動で保存されます）", key="watch_txt",
                                  placeholder="例: 6501, 4063, PLTR　※日本株は4桁コード")
        hide_bad = st.checkbox("過去成績がマイナスのものは隠す（3回以上出現したパターン）", value=True)
        top_n = st.slider("表示する件数", 3, 30, 10)
        st.caption("標準の対象は、日本・米国の代表的な大型株、主要ETF、原油・金の関連銘柄です"
                   "（出来高が多く短期売買しやすいものを選んでいます）。気になる銘柄はマイ銘柄に追加してください。")
    extra = [data.normalize_ticker(x) for x in extra_txt.split(",") if x.strip()]
    if extra != load_watch():
        save_watch(extra)

    if style == "デイトレ":
        try:
            idx_t = "SPY"
            md = su.prep_intraday(fetch(idx_t, "5d", "5m", use_yahoo))
            r_ = md.iloc[-1]
            up_ok = r_["Close"] > r_["VWAP"] and r_["EMA9"] > r_["EMA20"]
            dn_ok = r_["Close"] < r_["VWAP"] and r_["EMA9"] < r_["EMA20"]
            jd = su.prep_intraday(fetch("1321.T", "5d", "5m", use_yahoo)).iloc[-1]
            jp_ok = jd["Close"] > jd["VWAP"] and jd["EMA9"] > jd["EMA20"]
            jp_dn = jd["Close"] < jd["VWAP"] and jd["EMA9"] < jd["EMA20"]
            lab = lambda u, d_: "🟢 買いOK" if u else ("🔻 売りOK" if d_ else "⚪ どちらも見送り")
            st.markdown(f"**相場フィルター**　米国（SPY）：{lab(up_ok, dn_ok)}　日本（1321）：{lab(jp_ok, jp_dn)}　"
                        "<span style='color:gray;font-size:.85rem'>（指数がVWAPより上・短期上向きなら買い、下・短期下向きなら売りだけを入れる）</span>",
                        unsafe_allow_html=True)
        except Exception:
            pass
    if style == "スイング":
        st.caption("毎日の終値で判定します。**夜や朝に見て、翌営業日に注文**する使い方を想定しています。")
        sr_ = load_rule(swing=True)
        if sr_:
            st.success(f"✅ 検証済みルールを適用中：{pt.swing_rule_label(sr_)}（過去5年の実データで、学習・検証の両期間ともプラス）")
    else:
        st.caption("5分足で判定します（直近15分以内に出たシグナルのみ）。**取引時間中に開いて使う**想定です。")
        st.warning("🧪 検証結果：デイトレのパターンは、実データの過去60日では**勝てる設定が見つかっていません**。"
                   "練習・観察用としてお使いください（実際のお金で使うのはおすすめしません）。")

    key = (style, tuple(cats), tuple(extra), use_yahoo)
    n_targets = len(data.universe(cats)) + len([t for t in extra if t not in {x[2] for x in data.universe(cats)}])
    cols = st.columns([1, 4])
    refresh = cols[0].button("🔄 最新に更新", width="stretch")
    if refresh or st.session_state.get("scan_key") != key or \
            (time.time() - st.session_state.get("scan_at", 0)) > (900 if style == "スイング" else 180):
        with st.spinner(f"{n_targets}銘柄をチェック中…（初回は30秒ほどかかります）"):
            if refresh:
                fetch.clear()
            st.session_state["scan"] = run_scan(style, cats, extra)
            st.session_state["scan_key"] = key
            st.session_state["scan_at"] = time.time()
    results = st.session_state["scan"]
    cols[1].caption(f"最終チェック {datetime.fromtimestamp(st.session_state['scan_at'], JST):%m/%d %H:%M}　"
                    f"／ ドル円 {fx:.2f}{'' if fx_live else '（仮の値）'}")

    items = [(it, p) for it in results for p in it["plans"]]
    if hide_bad:
        items = [(it, p) for it, p in items if not (p.hist_n >= 3 and p.hist_avg_r < 0)]
    items.sort(key=lambda x: x[1].score, reverse=True)
    errs = [it for it in results if it["err"]]

    if items:
        st.markdown(f"**{len(results)}銘柄中 {len(items)}件** が条件に合いました。スコアの高い順に表示しています。")
        for i, (it, p) in enumerate(items[:top_n], 1):
            plan_card(i, it, p, style)
        if len(items) > top_n:
            with st.expander(f"残り {len(items) - top_n} 件を一覧で見る"):
                st.dataframe(pd.DataFrame([{
                    "銘柄": it["name"], "ティッカー": it["ticker"], "パターン": p.setup, "スコア": p.score,
                    "買い": round(p.entry, 2), "損切り": round(p.stop, 2), "利確": round(p.target, 2)}
                    for it, p in items[top_n:]]), hide_index=True, width="stretch")
    else:
        st.info("今は条件に合う銘柄がありません。**無理にトレードしないのも大事な戦略です。**"
                + ("" if style == "スイング" else "　デイトレのシグナルは取引時間中に出ます。"))

    if style == "デイトレ":
        watch = [(it, it["watch"]) for it in results if it["watch"]]
        watch.sort(key=lambda x: x[1]["_score"], reverse=True)
        if watch:
            st.markdown("### 👀 デイトレ監視リスト（値動きが大きく、出来高が多い銘柄）")
            st.caption("寄り付き前に確認し、「前日高値」を出来高を伴って上抜けたら買い候補、「前日安値」を割ったら様子見、が基本の見方です。")
            st.dataframe(pd.DataFrame([{
                "銘柄": it["name"], "ティッカー": it["ticker"], "トレンド": w["トレンド"],
                "1日の値幅(ATR%)": round(w["ATR%"], 2), "出来高倍率": round(w["出来高倍率"], 2),
                "前日高値": round(w["高値"], 2), "前日安値": round(w["安値"], 2), "前日終値": round(w["終値"], 2)}
                for it, w in watch[:15]]), hide_index=True, width="stretch")
    if errs:
        with st.expander(f"⚠️ 取得できなかった銘柄（{len(errs)}件）"):
            st.write(", ".join(f"{e['name']}（{e['err']}）" for e in errs))


# ===========================================================================
# 🌏 相場環境
# ===========================================================================
if page == P_ENV:
    st.markdown("## 🌏 相場環境")
    with st.spinner("為替・金利・指数を取得中…"):
        msum, frames = macro(use_yahoo)
    if not msum:
        st.error("相場データを取得できませんでした。")
    else:
        w = mk.weather(msum)
        with st.container(border=True):
            st.markdown(f"#### {w['icon']} 相場の天気：{w['label']}")
            st.markdown(w["advice"])
            st.markdown("\n".join(f"- {n}" for n in w["notes"]))

        st.markdown("#### 為替・金利・主要指数")
        st.caption("左から現在値・前日比。下段は1週間／1ヶ月の変化。米10年金利の変化は bp（0.01%）単位。")
        names = list(msum)
        for row in range(0, len(names), 5):
            cols = st.columns(5)
            for col, n in zip(cols, names[row:row + 5]):
                x = msum[n]
                unit = "bp" if n == "米10年金利" else "%"
                digits = 3 if n == "米10年金利" else 2
                col.metric(n, f"{x['last']:,.{digits}f}", f"{x['d1']:+.2f}{unit}", delta_color="inverse")
                col.caption(f"1週 {x['d5']:+.1f}{unit} ／ 1月 {x['d20']:+.1f}{unit}")

        st.markdown("#### 3ヶ月の動き（スタート=100）")
        default = [n for n in ("ドル円", "日経平均", "S&P500", "米10年金利") if n in frames]
        sel = st.multiselect("表示する項目", list(frames), default=default)
        fig = go.Figure()
        for n in sel:
            sr = frames[n].tail(63)
            sr = sr[sr.index >= sr.index[-1] - pd.Timedelta(days=92)]
            fig.add_trace(go.Scatter(x=sr.index, y=sr / sr.iloc[0] * 100, name=n, mode="lines"))
        fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=1.1),
                          hovermode="x unified")
        st.plotly_chart(fig, **PKW)

    st.markdown("#### 📅 重要イベント（今後30日・日本時間）")
    st.caption("クリックすると「結果によってどう動きやすいか」をやさしく解説します。")
    up = ev.upcoming(30)
    if up:
        for i, e in enumerate(up):
            with st.expander(f"⚠️ {ev.label(e)}", expanded=(i == 0)):
                event_guide(e["kind"])
    else:
        st.info("登録済みのイベントはありません。")
    st.caption(f"登録済み日程は {ev.last_known():%Y/%m/%d} まで。以降は events.py に追加してください。")

    st.markdown("#### 📰 マーケットニュース")
    if not use_yahoo:
        st.info("デモデータ表示中はニュースを取得しません。")
    else:
        tabs = st.tabs(["日本株", "米国株", "為替", "原油・金"])
        for tab, tks in zip(tabs, [["^N225"], ["^GSPC", "^IXIC"], ["JPY=X"], ["CL=F", "GC=F"]]):
            with tab:
                items = [it for t in tks for it in get_news(t, use_yahoo)]
                items.sort(key=lambda it: it["time"] or pd.Timestamp(0, tz="Asia/Tokyo"), reverse=True)
                if not items:
                    st.caption("ニュースを取得できませんでした。")
                for it in items[:10]:
                    tm = f"{it['time']:%m/%d %H:%M}" if it["time"] is not None else ""
                    st.markdown(f"- [{it['title']}]({it['url']})　<span style='color:gray;font-size:.8rem'>{it['publisher']} {tm}</span>",
                                unsafe_allow_html=True)
        st.caption("ニュースは Yahoo!Finance 経由（多くは英語）。見出しの売り買い判断は自動では行いません。")


# ===========================================================================
# 📈 銘柄分析
# ===========================================================================
def symbol_picker():
    opts = [t for _, _, t in data.universe(list(data.PRESETS))]
    cur_sym = st.session_state["sym"]
    if cur_sym not in opts:
        opts = [cur_sym] + opts
    c1, c2 = st.columns([2, 1])
    pick = c1.selectbox("銘柄", opts, index=opts.index(cur_sym),
                        format_func=lambda t: f"{data.name_of(t)}（{t}）")
    free = c2.text_input("コード入力で探す", "", placeholder="例: 6501 / PLTR / CL=F")
    sym = data.normalize_ticker(free) if free.strip() else pick
    st.session_state["sym"] = sym
    return sym


if page == P_AN:
    st.markdown("## 📈 銘柄分析")
    ticker = symbol_picker()
    c1, c2, c3 = st.columns(3)
    iv_label = c1.selectbox("足", list(data.INTERVALS), index=4)
    iv = data.INTERVALS[iv_label]
    period = c2.selectbox("期間", iv["periods"], index=iv["periods"].index(iv["default"]),
                          format_func=lambda x: data.PERIOD_LABELS.get(x, x))
    intraday = iv["code"] in ("1m", "5m", "15m", "60m")
    try:
        df = fetch(ticker, period, iv["code"], use_yahoo)
    except Exception as e:
        st.error(f"データを取得できませんでした: {e}")
        st.stop()
    cur = data.currency_of(ticker)
    p = dict(ind.DEFAULT_PARAMS, intraday=intraday)
    d = ind.add_indicators(df, p)
    last, prev = df["Close"].iloc[-1], df["Close"].iloc[-2]
    m = st.columns(4)
    m[0].metric("現在値", fmtp(last, cur), f"{(last / prev - 1) * 100:+.2f}%", delta_color="inverse")
    m[1].metric("1本の平均値幅 (ATR)", fmtp(d["ATR"].iloc[-1], cur), f"{d['ATR'].iloc[-1] / last * 100:.2f}%", delta_color="off")
    m[2].metric("RSI(14)", f"{d['RSI'].iloc[-1]:.1f}")
    m[3].metric("出来高（20本平均比）", f"{d['Volume'].iloc[-1] / d['VOL_MA'].iloc[-1]:.2f}倍")

    # この銘柄の狙い目判定（日足スイング＋5分足デイトレ）
    st.markdown("#### 🎯 この銘柄の現在の判定")
    found = []
    try:
        dd = fetch(ticker, "2y", "1d", use_yahoo)
        found += [("スイング", p_, dd) for p_ in su.find_plans(dd, "スイング", cur)]
        di = fetch(ticker, "60d", "5m", use_yahoo)
        found += [("デイトレ", p_, di) for p_ in su.find_plans(di, "デイトレ", cur)]
    except Exception:
        pass
    if found:
        for style_, pl, dfx in found:
            plan_card("", {"ticker": ticker, "name": data.name_of(ticker), "cat": style_, "df": dfx}, pl, style_)
    else:
        st.info("今はどの狙い目パターンにも当てはまりません（様子見）。")

    ed = get_earnings(ticker, use_yahoo)
    if ed:
        st.info(f"📅 次の決算発表予定：{ed:%Y/%m/%d}（{(ed - datetime.now(JST).date()).days}日後）")

    st.markdown("#### チャート")
    c1, c2, c3 = st.columns(3)
    ov_opts = ["移動平均", "ボリンジャー"] + (["VWAP"] if intraday else [])
    overlays = c1.multiselect("価格に重ねる", ov_opts, default=ov_opts[:1] + (["VWAP"] if intraday else []))
    lower = c2.multiselect("サブチャート", ["RSI", "MACD", "ストキャスティクス"], default=["RSI"])
    mk = c3.selectbox("売買シグナル（検証用の戦略）", ["なし"] + list(strat.STRATEGIES))
    markers = strat.entry_points(strat.run_strategy(mk, df)) if mk != "なし" else None
    st.plotly_chart(charts.price_chart(d, p, overlays, lower, markers, intraday, iv["code"]), **PKW,
                    config={"scrollZoom": True, "displaylogo": False})
    if use_yahoo:
        nws = get_news(ticker, use_yahoo)
        if nws:
            with st.expander(f"📰 この銘柄のニュース（{len(nws)}件）"):
                for it in nws:
                    tm = f"{it['time']:%m/%d %H:%M}" if it["time"] is not None else ""
                    st.markdown(f"- [{it['title']}]({it['url']})　<span style='color:gray;font-size:.8rem'>{it['publisher']} {tm}</span>",
                                unsafe_allow_html=True)
    with st.expander("テクニカル指標の詳細"):
        snap = strat.snapshot(df)
        st.dataframe(pd.DataFrame([{"指標": a, "値": b, "判定": {1: "🔴 強気", -1: "🔵 弱気", 0: "⚪ 中立"}[c]}
                                   for a, b, c in snap["checks"]]), hide_index=True, width="stretch")


# ===========================================================================
# 📅 毎日の成績記録（フォワードテスト）
# ===========================================================================
def _fetch_many(pairs, period, interval):
    frames, names = {}, {}

    def get(a):
        n, t = a
        try:
            return t, n, fetch(t, period, interval, use_yahoo)
        except Exception:
            return t, n, None
    with ThreadPoolExecutor(max_workers=8) as pool:
        for t, n, df in pool.map(get, pairs):
            if df is not None and len(df):
                frames[t], names[t] = df, n
    return frames, names


def run_forward_update(store):
    msgs = []
    rule = load_rule()
    for mname, cats, idx_t, us in (("米国", ["米国株", "ETF"], "SPY", True), ("日本", ["日本株", "ETF"], "1321.T", False)):
        tk = [(n, t) for _, n, t in data.universe(cats) if data.is_tradable(t) and (t.endswith(".T") != us)]
        frames, names = _fetch_many(tk, "60d", "5m")
        try:
            idx = fetch(idx_t, "60d", "5m", use_yahoo)
        except Exception:
            idx = None
        if frames:
            n = fw.update_day(store, mname, frames, names, idx, capital, risk_pct, fx, rule)
            if n:
                msgs.append(f"{mname}：{n}日分を記録")
    # スイング
    srule = load_rule(swing=True) or pt.SWING_DEFAULT
    tk = [(n, t) for _, n, t in data.universe(ALL_CATS) if data.is_tradable(t)]
    frames, names = _fetch_many(tk, "2y", "1d")
    idxs = {}
    for k, it in (("US", "^GSPC"), ("JP", "^N225")):
        try:
            idxs[k] = fetch(it, "2y", "1d", use_yahoo)
        except Exception:
            idxs[k] = None
    earn = {}
    if srule.get("avoid_earnings"):
        stocks = [t for c_, _, t in data.universe(ALL_CATS) if c_ in ("日本株", "米国株") and t in frames]
        with ThreadPoolExecutor(max_workers=8) as pool:
            earn = dict(zip(stocks, pool.map(lambda t: get_earn_hist(t, use_yahoo), stocks)))
        for t in stocks:
            if not earn.get(t):
                earn[t] = mk.estimated_event_days(frames[t])
    st.session_state["fw_swing"] = (fw.swing_forward(frames, names, idxs, earn, capital, risk_pct, fx, srule, store.start()),
                                    pt.swing_rule_label(srule))
    return msgs


def forward_section():
    store = fw.Store()
    with st.container(border=True):
        st.markdown("### 📅 毎日の成績記録（フォワードテスト）")
        st.caption(f"{store.start():%Y/%m/%d} から、採用中のルールで毎日仮想売買した結果を記録しています。"
                   "アプリを開くと、終わった取引日が自動で追加されます。後でルールを変えても、記録済みの日は書き換えません。"
                   "これが「本当の実力」を測る一番正直な成績です。")
        c1, c2 = st.columns([1, 3])
        stale = time.time() - st.session_state.get("fw_checked", 0) > 1800
        if c1.button("🔄 記録を更新") or stale:
            with st.spinner("終わった取引日を記録中…（初回は1分ほど）"):
                msgs = run_forward_update(store)
            st.session_state["fw_checked"] = time.time()
            if msgs:
                st.toast("、".join(msgs))
        c2.caption(f"最終確認 {datetime.fromtimestamp(st.session_state.get('fw_checked', time.time()), JST):%m/%d %H:%M}")
        tab_d, tab_s = st.tabs(["デイトレ（毎日記録）", "スイング（開始日からの仮想売買）"])
        with tab_d:
            days = store.load_days()
            if not len(days):
                st.info("まだ記録がありません。取引日が終わると自動で追加されます。")
            else:
                days = days.sort_values("日付")
                m = st.columns(4)
                for col, mname in zip(m[:2], ("米国", "日本")):
                    x = days[days["市場"] == mname]
                    col.metric(f"{mname}：累積損益", f"{x['損益'].sum():+,.0f}円", f"{len(x)}日・{int(x['取引数'].sum())}回", delta_color="off")
                tot = days["取引数"].sum()
                m[2].metric("勝率", f"{days['勝ち'].sum() / tot * 100:.0f}%" if tot else "—")
                m[3].metric("取引しなかった日", f"{int((days['取引数'] == 0).sum())}日")
                fig = go.Figure()
                for mname, col_ in (("米国", UP), ("日本", DOWN)):
                    x = days[days["市場"] == mname]
                    if len(x):
                        fig.add_trace(go.Scatter(x=x["日付"], y=x["損益"].cumsum(), name=mname, mode="lines+markers",
                                                 line=dict(color=col_, width=2)))
                fig.update_layout(height=260, margin=dict(l=10, r=10, t=20, b=10), legend=dict(orientation="h", y=1.15),
                                  yaxis_title="累積損益（円）")
                st.plotly_chart(fig, **PKW, config={"displaylogo": False})
                show = days.sort_values("日付", ascending=False).assign(日付=lambda x: x["日付"].dt.strftime("%Y/%m/%d"))
                st.dataframe(show[["日付", "市場", "取引数", "勝ち", "損益", "ルール"]], hide_index=True, width="stretch")
                trs = store.load_trades()
                if len(trs):
                    with st.expander(f"取引の明細（{len(trs)}件）"):
                        st.dataframe(trs, hide_index=True, width="stretch")
        with tab_s:
            if "fw_swing" in st.session_state:
                res, lab = st.session_state["fw_swing"]
                tr, op = res["trades"], res["open"]
                st.caption(f"ルール：{lab}")
                m = st.columns(3)
                realized = tr["損益(円)"].sum() if len(tr) else 0
                unreal = op["含み損益(円)"].sum() if len(op) else 0
                m[0].metric("確定損益", f"{realized:+,.0f}円", f"{len(tr)}回", delta_color="off")
                m[1].metric("含み損益", f"{unreal:+,.0f}円", f"{len(op)}件保有/約定待ち", delta_color="off")
                m[2].metric("勝率", f"{(tr['R'] > 0).mean() * 100:.0f}%" if len(tr) else "—")
                if len(op):
                    st.markdown("**保有中・約定待ち**")
                    st.dataframe(op.assign(**{c_: op[c_].round(2) for c_ in op.select_dtypes("number").columns}),
                                 hide_index=True, width="stretch")
                if len(tr):
                    st.markdown("**決済済み**")
                    st.dataframe(tr.assign(**{c_: tr[c_].round(2) for c_ in tr.select_dtypes("number").columns}),
                                 hide_index=True, width="stretch")
                if not len(tr) and not len(op):
                    st.info("開始日以降、スイングの取引はまだありません（相場フィルターで見送り中の可能性）。")
        with st.expander("記録の開始日を変える"):
            new_start = st.date_input("開始日", store.start().date())
            if st.button("この日から記録し直す（今までの記録は消えます）"):
                store.reset(pd.Timestamp(new_start))
                st.session_state.pop("fw_checked", None)
                st.rerun()


# ===========================================================================
# 🎮 仮想売買（リプレイ）
# ===========================================================================
if page == P_PAPER:
    st.markdown("## 🎮 仮想売買")
    forward_section()
    st.divider()
    st.markdown("### ⏪ デイトレのリプレイ（過去の日を再生）")
    st.markdown("**実際の過去の5分足**を1本ずつ進めながら、このアプリのデイトレのルールどおりに"
                "売り買いしたらどうなったかを再現します。お金は動きません。")
    c = st.columns(4)
    mkt = c[0].selectbox("市場", ["米国株・米国ETF", "日本株・国内ETF"])
    ndays = c[1].slider("さかのぼる取引日数", 1, 20, 5)
    max_pos = c[2].slider("同時に持つ最大銘柄数", 1, 5, 3)
    min_score = c[3].slider("最低スコア", 30, 80, 50, 5, help="これ未満の狙い目は見送り")
    c = st.columns(3)
    cost = c[0].number_input("売買コスト %（片道・手数料＋スリッページ）", 0.0, 1.0, 0.05, 0.01)
    odd = c[1].checkbox("日本株は単元未満株（1株単位）でも買う", value=True)
    hide_bad_pt = c[2].checkbox("過去成績マイナスのパターンは見送り", value=True)
    use_filter = st.checkbox("相場フィルター：指数（米国=SPY／日本=1321）がVWAPより上・上向きの時だけ買い、下・下向きの時だけ売る", value=True,
                             help="下げ相場で買いに逆らわないためのルール")
    adopted = load_rule()
    rule_opts = {"標準（最初のルール）": pt.DEFAULT_RULE}
    if adopted:
        rule_opts = {f"採用ルール：{pt.rule_label(adopted)}": adopted, **rule_opts}
    rule_name = st.selectbox("損切り・利確のルール", list(rule_opts))
    us = mkt.startswith("米国")

    def load_frames():
        cats = ["米国株", "ETF"] if us else ["日本株", "ETF"]
        tk = [(n, t) for _, n, t in data.universe(cats) if data.is_tradable(t) and (t.endswith(".T") != us)]
        frames, names = {}, {}
        with st.spinner(f"{len(tk)}銘柄の5分足（過去60日）を取得中…"):
            def get(a):
                n, t = a
                try:
                    return t, n, fetch(t, "60d", "5m", use_yahoo)
                except Exception:
                    return t, n, None
            with ThreadPoolExecutor(max_workers=8) as pool:
                for t, n, df in pool.map(get, tk):
                    if df is not None and len(df):
                        frames[t], names[t] = df, n
        mdf = None
        if use_filter:
            try:
                mdf = fetch("SPY" if us else "1321.T", "60d", "5m", use_yahoo)
            except Exception:
                st.warning("相場フィルター用の指数データを取得できなかったため、フィルターなしで実行します。")
        return frames, names, mdf

    if st.button("▶️ 仮想売買を実行", type="primary"):
        frames, names, mdf = load_frames()
        with st.spinner("1本ずつ再生中…"):
            res = pt.replay(frames, names, ndays, capital, risk_pct, fx, max_pos, min_score, hide_bad_pt, odd, cost, mdf,
                            rule=rule_opts[rule_name])
            res["filter"] = mdf is not None
            res["rule"] = pt.rule_label(rule_opts[rule_name])
        st.session_state["paper"] = (res, mkt, use_yahoo)
    if "paper" in st.session_state:
        res, mkt_done, src_done = st.session_state["paper"]
        if not src_done:
            st.warning("⚠️ デモデータでの結果です。デモデータは架空の値動きなので、成績に意味はありません。")
        s_ = res["summary"]
        if not s_:
            st.info("この期間は条件に合う取引がありませんでした。")
        else:
            st.markdown(f"#### 結果：{mkt_done}　直近{res['days']}取引日（{res['start']:%m/%d}〜）"
                        f"　相場フィルター{'あり' if res.get('filter') else 'なし'}")
            st.caption(f"ルール：{res.get('rule', '標準')}")
            m = st.columns(6)
            m[0].metric("損益合計", f"{s_['損益合計']:+,.0f}円", f"資金比 {s_['損益合計'] / capital * 100:+.2f}%", delta_color="off")
            m[1].metric("取引数", f"{s_['取引数']}回")
            m[2].metric("勝率", f"{s_['勝率%']:.1f}%")
            m[3].metric("平均R", f"{s_['平均R']:+.2f}")
            pf = s_["プロフィットファクター"]
            m[4].metric("プロフィットファクター", "∞" if np.isinf(pf) else f"{pf:.2f}")
            m[5].metric("最大ドローダウン", f"{s_['最大ドローダウン']:,.0f}円")
            tr = res["trades"].copy()
            us = mkt_done.startswith("米国")
            for col in ("買い時刻", "売り時刻"):
                ts = tr[col]
                if us:
                    ts = ts.dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("Asia/Tokyo")
                tr[col.replace("時刻", "（日本時間）")] = ts.dt.strftime("%m/%d %H:%M")
            fig = go.Figure()
            fig.add_trace(go.Bar(x=list(range(1, len(tr) + 1)), y=tr["損益(円)"], name="各取引",
                                 marker_color=np.where(tr["損益(円)"] > 0, UP, DOWN), opacity=0.6,
                                 hovertext=tr["銘柄"] + " " + tr["パターン"]))
            fig.add_trace(go.Scatter(x=list(range(1, len(tr) + 1)), y=tr["累積損益(円)"], name="累積損益",
                                     line=dict(color="#333", width=2)))
            fig.update_layout(height=300, margin=dict(l=10, r=10, t=20, b=10), xaxis_title="取引の順番",
                              legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig, **PKW, config={"displaylogo": False})
            a, b = st.columns([1, 1.4])
            a.markdown("**日別**")
            a.dataframe(res["daily"].round(0), hide_index=True, width="stretch")
            byp = tr.groupby("パターン").agg(回数=("R", "size"), 勝率=("R", lambda x: (x > 0).mean() * 100),
                                            平均R=("R", "mean"), 損益=("損益(円)", "sum")).round(2)
            b.markdown("**パターン別**")
            b.dataframe(byp, width="stretch")
            st.markdown("**取引の明細**")
            show = tr[["買い（日本時間）", "銘柄", "売買", "パターン", "スコア", "買値", "損切り", "利確", "売り（日本時間）", "売値",
                       "株数", "決済理由", "損益(円)", "R"]]
            st.dataframe(show.assign(**{c_: show[c_].round(2) for c_ in ("買値", "損切り", "利確", "売値", "R")},
                                     **{"損益(円)": show["損益(円)"].round(0)}), hide_index=True, width="stretch", height=400)
            st.download_button("明細をCSVで保存", show.to_csv(index=False).encode("utf-8-sig"), "paper_trades.csv", "text/csv")
        st.caption("再生の条件：各時点ではその時点までのデータだけで判断／シグナルの次の足で約定（逆指値は3本以内に届かなければ取消）／"
                   "同じ足で損切りと利確の両方に届いたら損切り扱い／引けで必ず決済／同時保有と合計金額に上限。"
                   "それでも実際の約定（板の薄さ・急変時の滑り）より有利になりがちなので、少し割り引いて見てください。")


    st.divider()
    st.markdown("### 🔬 損切り・利確ルールの検証（いちばん勝てる設定を探す）")
    st.markdown("過去60日を **前半（学習）** と **後半（検証）** に分けます。前半で一番成績の良かった設定が、"
                "**使っていない後半の期間でも勝てるか**を確かめます。後半でも勝てる設定だけが「本物」です。")
    c = st.columns(3)
    test_days = c[0].slider("検証に使う直近の取引日数", 5, 25, 15)
    min_tr = c[1].slider("学習期間の最低取引数", 5, 40, 15)
    if c[2].button("🔬 検証を実行（1〜3分）"):
        frames, names, mdf = load_frames()
        with st.spinner(f"{4 * 5 * len(pt.GRID['patterns'])}通りの設定を検証中…"):
            rs = pt.research(frames, names, 55, test_days, capital, risk_pct, fx, mdf, min_tr,
                             max_pos=max_pos, min_score=min_score, hide_bad=False, allow_odd_lot=odd, cost_pct=cost)
        st.session_state["research"] = (rs, mkt)
    if "research" in st.session_state:
        rs, mkt_r = st.session_state["research"]
        st.markdown(f"**{mkt_r}**　学習：{rs['train_from']:%m/%d}〜（{rs['n_train']}日）　"
                    f"検証：{rs['split']:%m/%d}〜{rs['end']:%m/%d}（{rs['n_test']}日）")
        best, base = rs["best"], rs["base"]
        if best:
            a, b = st.columns(2)
            with a.container(border=True):
                st.markdown(f"**🏆 選ばれた設定**（パターンを1つに絞らない設定の中で学習成績が最良）\n\n{best['ルール']}")
                st.markdown(f"- 学習：{best['学習_回数']}回 平均 {best['学習_平均R']:+.2f}R（{best['学習_損益']:+,.0f}円）\n"
                            f"- **検証：{best['検証_回数']}回 平均 {best['検証_平均R']:+.2f}R（{best['検証_損益']:+,.0f}円）**")
                if best["検証_回数"] >= 5 and best["検証_平均R"] > 0:
                    st.success("未使用の期間でもプラス。採用する価値あり。")
                else:
                    st.warning("未使用の期間ではプラスにならず。たまたま学習期間に合っただけの可能性が高いです。")
                if st.button("この設定を採用する", key="adopt"):
                    save_rule(best["_rule"])
                    st.toast("採用しました。仮想売買とデイトレの狙い目で使われます。")
                    st.rerun()
            if base:
                with b.container(border=True):
                    st.markdown(f"**📏 比較：最初のルール**\n\n{base['ルール']}")
                    st.markdown(f"- 学習：{base['学習_回数']}回 平均 {base['学習_平均R']:+.2f}R（{base['学習_損益']:+,.0f}円）\n"
                                f"- 検証：{base['検証_回数']}回 平均 {base['検証_平均R']:+.2f}R（{base['検証_損益']:+,.0f}円）")
        tbl = rs["table"].drop(columns="_rule").head(20)
        st.dataframe(tbl.round(2), hide_index=True, width="stretch")
        st.caption("学習期間の平均Rが高い順。検証の列がプラスで揃っている設定ほど信頼できます。")
        if load_rule() and st.button("採用ルールを取り消して最初のルールに戻す"):
            save_rule(None)
            st.rerun()


    st.divider()
    st.markdown("### 🔬 スイング（数日〜2週間）の検証：過去5年・資金50万円で仮想売買")
    st.markdown("日本株・米国株・ETF・原油・金の全銘柄を対象に、**前半約3年（学習）で一番良かった設定が、後半約2年（検証）でも勝てるか**"
                "を240通りの設定（決算回避あり/なしを含む）で確かめます。同時に持つのは最大5銘柄、売買コストは片道0.1%で計算します。")
    if st.button("🔬 スイングの検証を実行（1〜3分）"):
        tk = [(n, t) for _, n, t in data.universe(ALL_CATS) if data.is_tradable(t)]
        frames, names = {}, {}
        with st.spinner(f"{len(tk)}銘柄の日足（5年分）を取得中…"):
            def get_d(a):
                n, t = a
                try:
                    return t, n, fetch(t, "5y", "1d", use_yahoo)
                except Exception:
                    return t, n, None
            with ThreadPoolExecutor(max_workers=8) as pool:
                for t, n, df in pool.map(get_d, tk):
                    if df is not None and len(df):
                        frames[t], names[t] = df, n
            idx = {}
            for k, it in (("US", "^GSPC"), ("JP", "^N225")):
                try:
                    idx[k] = fetch(it, "5y", "1d", use_yahoo)
                except Exception:
                    idx[k] = None
        stocks = [t for c_, _, t in data.universe(ALL_CATS) if c_ in ("日本株", "米国株") and t in frames]
        with st.spinner("過去の決算発表日を取得中…"):
            with ThreadPoolExecutor(max_workers=8) as pool:
                earn = dict(zip(stocks, pool.map(lambda t: get_earn_hist(t, use_yahoo), stocks)))
        n_ok = sum(1 for v in earn.values() if v)
        n_est = 0
        for t in stocks:  # 履歴が取れない銘柄は、株価の大きな窓＋出来高急増から推定
            if not earn.get(t):
                earn[t] = mk.estimated_event_days(frames[t])
                n_est += 1 if earn[t] else 0
        st.session_state["earn_cov"] = (n_ok, n_est, len(stocks))
        with st.spinner("240通りの設定を検証中…"):
            rsw = pt.research_swing(frames, names, idx, capital, risk_pct, fx, test_frac=0.4, min_trades=30,
                                    earnings=earn, allow_odd_lot=odd, cost_pct=0.1)
            if rsw["best"]:
                rsw["best_trades"] = pt.simulate_swing(rsw["prep"], names, capital, risk_pct, fx, rsw["best"]["_rule"],
                                                       start=rsw["split"], allow_odd_lot=odd, cost_pct=0.1)
            rsw.pop("prep")
        st.session_state["research_sw"] = rsw
    if "research_sw" in st.session_state:
        rs = st.session_state["research_sw"]
        st.markdown(f"学習：{rs['train_from']:%Y/%m/%d}〜（{rs['n_train']}日）　検証：{rs['split']:%Y/%m/%d}〜{rs['end']:%Y/%m/%d}（{rs['n_test']}日）")
        if "earn_cov" in st.session_state:
            n_ok, n_est, n_all = st.session_state["earn_cov"]
            st.caption(f"過去の決算日：公式データ {n_ok}銘柄＋株価から推定 {n_est}銘柄 ／ 個別株 {n_all}銘柄"
                       "（推定＝大きな窓と出来高急増の日。ETF・原油・金は決算なし）")
        best, base = rs["best"], rs["base"]
        if best:
            a, b = st.columns(2)
            with a.container(border=True):
                st.markdown(f"**🏆 選ばれた設定**（全パターン・学習150回以上の中で学習成績が最良）\n\n{best['ルール']}")
                st.markdown(f"- 学習：{best['学習_回数']}回 勝率{best['学習_勝率%']:.0f}% 平均 {best['学習_平均R']:+.2f}R（{best['学習_損益']:+,.0f}円）\n"
                            f"- **検証：{best['検証_回数']}回 勝率{best['検証_勝率%']:.0f}% 平均 {best['検証_平均R']:+.2f}R（{best['検証_損益']:+,.0f}円）**")
                if best["検証_回数"] >= 15 and best["検証_平均R"] >= 0.05 and best["検証_損益"] > 0:
                    st.success("未使用の期間でもプラス。採用する価値あり。")
                else:
                    st.warning("未使用の期間ではプラスにならず。")
                if st.button("このスイング設定を採用する", key="adopt_sw"):
                    save_rule(best["_rule"], swing=True)
                    st.toast("採用しました。")
            if base:
                with b.container(border=True):
                    st.markdown(f"**📏 比較：最初のルール**\n\n{base['ルール']}")
                    st.markdown(f"- 学習：{base['学習_回数']}回 勝率{base['学習_勝率%']:.0f}% 平均 {base['学習_平均R']:+.2f}R（{base['学習_損益']:+,.0f}円）\n"
                                f"- 検証：{base['検証_回数']}回 勝率{base['検証_勝率%']:.0f}% 平均 {base['検証_平均R']:+.2f}R（{base['検証_損益']:+,.0f}円）")
            pr = rs.get("pair")
            if pr:
                st.markdown(f"**🔁 決算回避の効果**（同じ設定で切り替え）　{pr['ルール']}：学習 {pr['学習_回数']}回 平均 {pr['学習_平均R']:+.2f}R"
                            f"（{pr['学習_損益']:+,.0f}円）／検証 {pr['検証_回数']}回 平均 {pr['検証_平均R']:+.2f}R（{pr['検証_損益']:+,.0f}円）")
            bt_ = rs.get("best_trades")
            if bt_ is not None and len(bt_):
                eq_ = bt_.sort_values("売り日")
                fig = go.Figure(go.Scatter(x=eq_["売り日"], y=eq_["損益(円)"].cumsum(), mode="lines", line=dict(color=UP, width=2),
                                           name="累積損益"))
                fig.update_layout(height=280, margin=dict(l=10, r=10, t=30, b=10), title="検証期間の累積損益（選ばれた設定）")
                st.plotly_chart(fig, **PKW, config={"displaylogo": False})
                with st.expander(f"検証期間の取引明細（{len(bt_)}件）"):
                    st.dataframe(bt_.assign(**{c_: bt_[c_].round(2) for c_ in bt_.select_dtypes("number").columns}),
                                 hide_index=True, width="stretch")
        st.dataframe(rs["table"].drop(columns="_rule").head(25).round(2), hide_index=True, width="stretch")


# ===========================================================================
# 🧪 検証
# ===========================================================================
@st.cache_data(ttl=3600, show_spinner=False)
def pattern_table(style, use_yahoo):
    rows = []

    def one(a):
        c, n, t = a
        try:
            df = fetch(t, "2y", "1d", use_yahoo) if style == "スイング" else fetch(t, "60d", "5m", use_yahoo)
            return [dict(r, 銘柄=n, カテゴリ=c) for r in su.pattern_stats(df, style)]
        except Exception:
            return []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for r in pool.map(one, data.universe(ALL_CATS)):
            rows += r
    return pd.DataFrame(rows)


if page == P_VAL:
    st.markdown("## 🧪 検証")
    st.markdown("#### 狙い目パターンの過去成績（全銘柄）")
    st.caption("各パターンが出たあと、損切りより先に利確に届いたかを過去データで集計。"
               "**R** は「損切り幅＝1」としたときの損益（+2R＝損切り幅の2倍の利益）。平均Rがプラスなら、続けるほど増える傾向です。")
    vstyle = st.segmented_control("スタイル", ["スイング", "デイトレ"], default="スイング", key="v_style") or "スイング"
    with st.spinner("集計中…"):
        pt = pattern_table(vstyle, use_yahoo)
    if len(pt):
        pt = pt[pt["回数"] > 0].copy()
        pt["勝ち"] = pt["勝率%"] / 100 * pt["回数"]
        pt["R合計"] = pt["平均R"] * pt["回数"]
        agg = pt.groupby("パターン").agg(回数=("回数", "sum"), 勝ち=("勝ち", "sum"), R合計=("R合計", "sum")).reset_index()
        agg["勝率%"] = (agg["勝ち"] / agg["回数"] * 100).round(1)
        agg["平均R"] = (agg["R合計"] / agg["回数"]).round(2)
        agg["説明"] = agg["パターン"].map(su.SETUP_HELP)
        st.dataframe(agg[["パターン", "回数", "勝率%", "平均R", "説明"]], hide_index=True, width="stretch")
        by_cat = pt.groupby(["カテゴリ", "パターン"]).agg(回数=("回数", "sum"), R合計=("R合計", "sum"))
        by_cat["平均R"] = (by_cat["R合計"] / by_cat["回数"]).round(2)
        with st.expander("カテゴリ別"):
            st.dataframe(by_cat["平均R"].unstack(), width="stretch")
        st.caption("※ 手数料・スリッページは含みません。過去の成績は将来を保証しません。")

    st.divider()
    st.markdown("#### 戦略のバックテスト（1銘柄）")
    ticker = symbol_picker()
    c = st.columns(3)
    iv_label = c[0].selectbox("足", ["日足", "1時間足", "15分足", "5分足"], key="bt_iv")
    iv = data.INTERVALS[iv_label]
    period = c[1].selectbox("期間", iv["periods"], index=len(iv["periods"]) - 1, key="bt_period",
                            format_func=lambda x: data.PERIOD_LABELS.get(x, x))
    sname = c[2].selectbox("戦略", list(strat.STRATEGIES), key="bt_strat")
    try:
        df = fetch(ticker, period, iv["code"], use_yahoo)
    except Exception as e:
        st.error(f"データを取得できませんでした: {e}")
        st.stop()
    pdefs = strat.STRATEGIES[sname][1]
    cols = st.columns(len(pdefs))
    params = {k: col.number_input(label, lo, hi, dv, step, key=f"bt_{sname}_{k}")
              for col, (k, (label, dv, lo, hi, step)) in zip(cols, pdefs.items())}
    c = st.columns(5)
    fee = c[0].number_input("手数料 %（片道）", 0.0, 2.0, 0.0, 0.01)
    slip = c[1].number_input("スリッページ %", 0.0, 2.0, 0.05, 0.01)
    sl = c[2].number_input("損切り %（0=なし）", 0.0, 50.0, 0.0, 0.5)
    tp = c[3].number_input("利確 %（0=なし）", 0.0, 100.0, 0.0, 0.5)
    short = c[4].checkbox("空売りも行う", value=False)
    target = strat.run_strategy(sname, df, params)
    res = bt.run_backtest(df, target, capital, fee, slip, sl or None, tp or None, short, bars_per_year=iv["bars_per_year"])
    s = res["stats"]
    m = st.columns(5)
    m[0].metric("総リターン", f"{s['総リターン%']:+.2f}%", f"買って持つだけ {s['バイ&ホールド%']:+.2f}%", delta_color="off")
    m[1].metric("最大ドローダウン", f"{s['最大ドローダウン%']:.2f}%")
    m[2].metric("勝率", f"{s['勝率%']:.1f}%", f"{s['取引回数']}回", delta_color="off")
    pf = s["プロフィットファクター"]
    m[3].metric("プロフィットファクター", "∞" if np.isinf(pf) else f"{pf:.2f}")
    m[4].metric("平均保有", f"{s['平均保有本数']:.1f}本")
    eq = res["equity"]
    bh = capital * df["Close"] / df["Open"].iloc[0]
    ef = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03)
    ef.add_trace(go.Scatter(x=eq.index, y=eq, name="戦略", line=dict(color=UP, width=2)), 1, 1)
    ef.add_trace(go.Scatter(x=bh.index, y=bh, name="買って持つだけ", line=dict(color="#999", width=1.3, dash="dot")), 1, 1)
    dd = (eq / eq.cummax() - 1) * 100
    ef.add_trace(go.Scatter(x=dd.index, y=dd, name="ドローダウン%", fill="tozeroy", line=dict(color=DOWN, width=1)), 2, 1)
    ef.update_layout(height=400, margin=dict(l=10, r=10, t=20, b=10), legend=dict(orientation="h", y=1.08), hovermode="x unified")
    st.plotly_chart(ef, **PKW)
    if len(res["trades"]):
        with st.expander("取引一覧"):
            tr = res["trades"]
            st.dataframe(tr.assign(**{c_: tr[c_].round(2) for c_ in tr.select_dtypes("number").columns}),
                         hide_index=True, width="stretch")


# ===========================================================================
# 📒 トレード記録
# ===========================================================================
if page == P_LOG:
    st.markdown("## 📒 トレード記録")
    st.caption("実際に売買したら記録しましょう。勝率や「損切りを守れているか」を振り返るのが上達の近道です。")
    log = journal.load()
    stt = journal.stats(log)
    m = st.columns(5)
    if stt["n"]:
        m[0].metric("確定損益（合計）", f"{stt['total']:+,.0f}")
        m[1].metric("勝率", f"{stt['win_rate']:.1f}%", f"{stt['n']}回", delta_color="off")
        m[2].metric("平均利益 / 平均損失", f"{stt['avg_win']:,.0f} / {stt['avg_loss']:,.0f}")
        m[3].metric("期待値（1回あたり）", f"{stt['expectancy']:+,.0f}")
        m[4].metric("最大連敗", f"{stt['max_losing_streak']}回")

    with st.expander("➕ 新規エントリーを記録", expanded=log.empty):
        with st.form("new_trade", clear_on_submit=True):
            a, b, c = st.columns(3)
            sym = a.text_input("銘柄コード", st.session_state["sym"])
            side = b.selectbox("方向", ["買い", "売り"])
            qty = c.number_input("数量", 0.0, 1e9, 100.0, 1.0)
            a, b, c = st.columns(3)
            ep = a.number_input("約定価格", 0.0, 1e9, 0.0, 0.01, format="%.2f")
            sp = b.number_input("損切り価格", 0.0, 1e9, 0.0, 0.01, format="%.2f")
            tpp = c.number_input("利確目標", 0.0, 1e9, 0.0, 0.01, format="%.2f")
            a, b, c = st.columns(3)
            edate = a.date_input("日付", datetime.now(JST))
            etime = b.time_input("時刻", datetime.now(JST).replace(second=0, microsecond=0, tzinfo=None))
            fees = c.number_input("手数料", 0.0, 1e7, 0.0, 1.0)
            a, b = st.columns([1, 2])
            method = a.selectbox("手法", ["裁量"] + list(su.SWING) + list(su.DAY_ALL))
            notes = b.text_input("メモ（根拠・反省など）")
            if st.form_submit_button("記録する", type="primary"):
                if ep <= 0:
                    st.error("約定価格を入力してください")
                else:
                    journal.add_trade(data.normalize_ticker(sym), side, datetime.combine(edate, etime), ep, qty,
                                      sp or None, tpp or None, fees, method, notes)
                    st.rerun()

    open_t = log[log["exit_price"].isna()]
    if len(open_t):
        st.markdown("#### 📂 保有中")
        prices = {}
        for sym in open_t["symbol"].unique():
            try:
                prices[sym] = fetch(sym, "5d", "1d", use_yahoo)["Close"].iloc[-1]
            except Exception:
                prices[sym] = np.nan
        ot = open_t.copy()
        ot["現在値"] = ot["symbol"].map(prices)
        sign = np.where(ot["side"] == "買い", 1, -1)
        ot["含み損益"] = sign * (ot["現在値"] - ot["entry_price"]) * ot["qty"] - ot["fees"]
        ot["状態"] = np.where((ot["stop_price"].notna()) & (sign * (ot["現在値"] - ot["stop_price"]) <= 0), "⚠️ 損切りライン到達",
                            np.where((ot["target_price"].notna()) & (sign * (ot["現在値"] - ot["target_price"]) >= 0), "🎯 利確ライン到達", ""))
        show = ot[["id", "symbol", "side", "entry_time", "entry_price", "qty", "stop_price", "target_price",
                   "現在値", "含み損益", "状態", "strategy"]].rename(columns=journal.JP)
        st.dataframe(show.round(2), hide_index=True, width="stretch")
        with st.form("close_trade"):
            st.markdown("**決済を記録**")
            a, b, c, e = st.columns([2, 1, 1, 1])
            opts = {f"#{r.id} {data.name_of(r.symbol)} {r.side} {r.qty:g} @ {r.entry_price:g}": int(r.id) for r in open_t.itertuples()}
            pick = a.selectbox("ポジション", list(opts))
            xp = b.number_input("決済価格", 0.0, 1e9, 0.0, 0.01, format="%.2f")
            xdt = c.date_input("決済日", datetime.now(JST))
            xfee = e.number_input("追加手数料", 0.0, 1e7, 0.0)
            if st.form_submit_button("決済する"):
                if xp <= 0:
                    st.error("決済価格を入力してください")
                else:
                    journal.close_trade(opts[pick], datetime.combine(xdt, datetime.now(JST).time().replace(second=0, microsecond=0)), xp, xfee)
                    st.rerun()

    closed = log[log["exit_price"].notna()]
    if len(closed):
        st.markdown("#### 📊 損益の推移")
        cs = closed.sort_values("exit_time")
        n = list(range(1, len(cs) + 1))
        fig = go.Figure()
        fig.add_trace(go.Bar(x=n, y=cs["pnl"], name="各トレード", marker_color=np.where(cs["pnl"] > 0, UP, DOWN), opacity=0.6))
        fig.add_trace(go.Scatter(x=n, y=cs["pnl"].cumsum(), name="累積損益", line=dict(color="#333", width=2)))
        fig.update_layout(height=300, margin=dict(l=10, r=10, t=20, b=10), xaxis_title="トレード番号",
                          xaxis_dtick=1 if len(cs) <= 30 else None, legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, **PKW)
        bm = closed.groupby("strategy").agg(回数=("pnl", "size"), 損益=("pnl", "sum"),
                                            勝率=("pnl", lambda x: (x > 0).mean() * 100)).round(1).rename_axis("手法")
        st.markdown("**手法別の成績**")
        st.dataframe(bm.sort_values("損益", ascending=False), width="stretch")

    if len(log):
        with st.expander("📜 全履歴・CSV・削除"):
            hist = log.rename(columns={**journal.JP, "pnl": "損益", "pnl_pct": "損益率%", "r_multiple": "R倍数"})
            st.dataframe(hist.round(2), hide_index=True, width="stretch")
            a, b = st.columns(2)
            a.download_button("CSVで書き出し", hist.to_csv(index=False).encode("utf-8-sig"), "trades.csv", "text/csv")
            del_id = b.selectbox("削除するID", log["id"].tolist())
            if b.button("この記録を削除"):
                journal.delete_trade(int(del_id))
                st.rerun()


# ===========================================================================
# ❓ 使い方
# ===========================================================================
if page == P_HELP:
    st.markdown("""
## ❓ 使い方

### 基本の流れ（3ステップ）
1. **「🎯 今日の狙い目」を開く**
   約50銘柄を自動でチェックして、条件に合う銘柄をスコア順に並べます。
   - **スイング**：夜か朝に見て、翌営業日に注文（保有は数日〜2週間）
   - **デイトレ**：取引時間中に開いて使う（当日中に決済）
2. **カードの3つの価格で注文する**
   - 🟠 **買い**：書かれた方法で買い注文（「逆指値」＝その価格を上回ったら買う注文）
   - 🔵 **損切り**：買ったらすぐ、この価格に**逆指値の売り注文**を入れておく（損失を限定）
   - 🔴 **利確**：この価格に**指値の売り注文**を入れる
   多くの証券会社にある **OCO注文**（損切りと利確を同時に出せる注文）を使うと楽です。
3. **「買ったら記録」→ 決済したら「📒 トレード記録」で決済を記録**
   勝率と、損切りを守れているかを振り返ります。

### カードの見方
| 項目 | 意味 |
|---|---|
| ★とスコア | チャートの形の良さ・リスクリワード・この銘柄での過去成績を合わせた点数（100点満点） |
| パターン | どんな形の狙い目か（下の表） |
| リスクリワード | 損切り幅に対して利確幅が何倍か。1:2なら「1万円のリスクで2万円を狙う」 |
| 過去成績 | この銘柄で同じパターンが過去に出たときの勝率と平均R |
| 株数 | 左の「資金」と「許容損失」から計算した、買ってよい株数の目安 |

### パターン一覧
""" + "\n".join(f"- **{k}**：{v}" for k, v in su.SETUP_HELP.items()) + """

### 📅 経済指標の読み方（初心者向け）
""" + "\n\n".join(
    f"#### {ev.INFO[k]['name']}\n{g['what']}\n\n"
    f"- 📈 **{g['strong'][0]}**：{' → '.join(g['strong'][1])}\n"
    f"- 📉 **{g['weak'][0]}**：{' → '.join(g['weak'][1])}\n\n💡 {g['point']}"
    for k, g in ev.GUIDE.items()) + f"""

🔑 {ev.COMMON['rule']}

- {ev.COMMON['day']}
- {ev.COMMON['swing']}

### 🕘 取引時間（日本時間）
| 市場 | 取引時間 | 休憩 |
|---|---|---|
| 東証（日本株・国内ETF） | 前場 9:00〜11:30、後場 12:30〜15:30 | 昼休み 11:30〜12:30 |
| 米国株（NYSE・NASDAQ） | 夏時間 22:30〜翌5:00 ／ 冬時間 23:30〜翌6:00 | なし |
| 原油・金の先物（CME） | ほぼ24時間（月曜朝〜土曜朝） | 毎朝1時間（夏 6:00〜7:00 ／ 冬 7:00〜8:00） |

- 米国の夏時間は3月第2日曜〜11月第1日曜。
- 土日・祝日は休み（日本と米国で祝日が違うので注意）。
- 東証の15:25〜15:30は「引け」の注文をまとめる時間で、値段が付くのは15:30。

### 🎮 仮想売買ページ
- **📅 毎日の成績記録（フォワードテスト）**：記録開始日から、採用中のルールで毎日仮想売買した結果を自動で記録します。アプリを開くたびに、終わった取引日が追加されます。後でルールを変えても、記録済みの日は書き換えません。**本当の実力はこの成績で判断**してください。
- **デイトレの売り（空売り）**：VWAP戻り売り／寄り付きレンジ下抜け／前日安値割れ。指数がVWAPより下・下向きのときだけ売ります（実際の空売りには信用取引口座が必要）。
- **スイングの決算回避**：保有期間中に決算発表が入る取引を見送る設定も検証できます。

実際の過去の5分足を1本ずつ再生し、デイトレのルールどおりに売買した結果を表示します。お金をかけずに「このルールは勝てているか」を確かめられます。
数日だけの結果は運に左右されるので、**10〜20取引日**で見るのがおすすめです。

### 🌏 相場環境ページ
- **相場の天気**：VIX（恐怖指数）、日米の株価指数のトレンド、米金利、ドル円の急変から、全体が買いやすい環境かを判定します。☔のときは無理をしないのが基本です。
- **重要イベント**：米雇用統計・米CPI・FOMC・日銀会合の日程（日本時間）。狙い目カードにも「保有期間中のイベント」として表示します。
- **💱 為替タグ**：日本株カードの「円安で上がりやすい／円高で上がりやすい」は、過去半年の株価とドル円の連動から判定しています。

### 対象銘柄について
標準では、日本・米国の代表的な大型株、主要ETF、原油・金の関連銘柄（合計約50）をチェックします。出来高が多く短期売買しやすいものを選んでいます。
「対象銘柄・表示の設定」の **マイ銘柄** にコードを入れると、次回以降も対象に含まれます。

### アプリの終了
Dockのアイコンをもう一度クリックして「停止する」を選びます。ブラウザのタブを閉じるだけでは裏で動き続けます。

### 大事なルール
- **損切りは必ず守る**。勝率50%でも、損失を小さく・利益を大きくすれば資金は増えます（リスクリワード1:2なら勝率34%以上で黒字）。
- **1回の損失は資金の1〜2%まで**。連敗しても退場しないためです。
- **狙い目がない日は休む**。
- 決算発表の前後は値動きが荒くなるので、新規の買いは避けるのが無難です。
- 株価は最大20分ほど遅れることがあります。注文前に証券会社の画面で現在値を確認してください。

### 用語
- **R**：損切り幅を1としたときの損益。+2R＝損切り幅の2倍の利益、-1R＝損切り。
- **ATR**：1日（1本）の平均的な値動きの幅。損切り幅の目安に使っています。
- **VWAP**：その日の出来高で重み付けした平均価格。デイトレで「今日の買い手の平均コスト」の目安。

⚠️ 本アプリは条件に合うチャートを機械的に探すツールで、投資助言ではありません。
""")

# ---------------------------------------------------------------------------
if auto and use_yahoo:
    time.sleep(refresh_sec)
    st.rerun()

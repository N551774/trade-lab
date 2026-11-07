"""売買ルール（戦略）と現在のシグナル判定

各戦略は「その足の終値時点で取りたいポジション」を返す:
    1 = 買い（ロング）, -1 = 売り（ショート）, 0 = ノーポジション
バックテストでは、この値を次の足の始値で執行する。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import indicators as ind


def _state_machine(long_entry, long_exit, short_entry, short_exit) -> pd.Series:
    le, lx, se, sx = (np.asarray(x, dtype=bool) for x in (long_entry, long_exit, short_entry, short_exit))
    pos = np.zeros(len(le))
    cur = 0
    for i in range(len(le)):
        if cur == 1 and lx[i]:
            cur = 0
        elif cur == -1 and sx[i]:
            cur = 0
        if cur == 0:
            if le[i]:
                cur = 1
            elif se[i]:
                cur = -1
        pos[i] = cur
    return pd.Series(pos, index=long_entry.index)


def ma_cross(df, fast=5, slow=25):
    f, s = ind.ema(df["Close"], fast), ind.ema(df["Close"], slow)
    return pd.Series(np.where(f > s, 1, -1), index=df.index).where(s.notna(), 0)


def macd_cross(df, fast=12, slow=26, signal=9):
    line, sig, _ = ind.macd(df["Close"], fast, slow, signal)
    return pd.Series(np.where(line > sig, 1, -1), index=df.index).where(sig.notna(), 0)


def rsi_reversion(df, period=14, low=30, high=70):
    r = ind.rsi(df["Close"], period)
    return _state_machine(r < low, r > 50, r > high, r < 50)


def bollinger_reversion(df, period=20, k=2.0):
    u, m, l = ind.bollinger(df["Close"], period, k)
    c = df["Close"]
    return _state_machine(c < l, c >= m, c > u, c <= m)


def breakout(df, entry_n=20, exit_n=10):
    hh = df["High"].rolling(entry_n).max().shift(1)
    ll = df["Low"].rolling(entry_n).min().shift(1)
    xl = df["Low"].rolling(exit_n).min().shift(1)
    xh = df["High"].rolling(exit_n).max().shift(1)
    c = df["Close"]
    return _state_machine(c > hh, c < xl, c < ll, c > xh)


def trend_pullback(df, trend=50, period=3, low=20, high=80):
    """長期トレンド方向への押し目買い／戻り売り（短期RSIで判定）"""
    t = ind.sma(df["Close"], trend)
    r = ind.rsi(df["Close"], period)
    c = df["Close"]
    return _state_machine((c > t) & (r < low), r > 60, (c < t) & (r > high), r < 40)


# 名前 → (関数, パラメータ定義{名前: (表示名, 既定値, 最小, 最大, 刻み)})
STRATEGIES = {
    "移動平均クロス": (ma_cross, {
        "fast": ("短期EMA", 5, 2, 100, 1), "slow": ("長期EMA", 25, 5, 300, 1)}),
    "MACDクロス": (macd_cross, {
        "fast": ("短期", 12, 2, 50, 1), "slow": ("長期", 26, 5, 100, 1), "signal": ("シグナル", 9, 2, 30, 1)}),
    "RSI逆張り": (rsi_reversion, {
        "period": ("期間", 14, 2, 50, 1), "low": ("売られすぎ", 30, 5, 45, 1), "high": ("買われすぎ", 70, 55, 95, 1)}),
    "ボリンジャー逆張り": (bollinger_reversion, {
        "period": ("期間", 20, 5, 100, 1), "k": ("σ", 2.0, 1.0, 3.5, 0.1)}),
    "ブレイクアウト": (breakout, {
        "entry_n": ("高値/安値更新(本)", 20, 3, 120, 1), "exit_n": ("手仕舞い(本)", 10, 2, 60, 1)}),
    "押し目買い(トレンド+RSI)": (trend_pullback, {
        "trend": ("トレンドSMA", 50, 10, 200, 1), "period": ("RSI期間", 3, 2, 14, 1),
        "low": ("押し目RSI", 20, 5, 40, 1), "high": ("戻りRSI", 80, 60, 95, 1)}),
}


def default_params(name: str) -> dict:
    return {k: v[1] for k, v in STRATEGIES[name][1].items()}


def run_strategy(name: str, df: pd.DataFrame, params: dict | None = None) -> pd.Series:
    func, _ = STRATEGIES[name]
    return func(df, **(params or default_params(name))).fillna(0)


def entry_points(target: pd.Series, allow_short: bool = True) -> pd.DataFrame:
    """ポジションが変化した足（チャートに矢印を出す用）"""
    t = target if allow_short else target.clip(lower=0)
    chg = t.diff().fillna(t)
    return pd.DataFrame({"buy": chg > 0, "sell": chg < 0})


# ---------------------------------------------------------------------------
# 現在のシグナル要約
# ---------------------------------------------------------------------------
def snapshot(df: pd.DataFrame) -> dict:
    """指標の現在値と、各戦略の最新シグナル・総合スコア（-100〜+100）"""
    d = ind.add_indicators(df, ind.DEFAULT_PARAMS)
    last = d.iloc[-1]
    prev = d.iloc[-2] if len(d) > 1 else last
    checks = []  # (項目, 判定テキスト, スコア -1/0/+1)

    r = last["RSI"]
    if pd.notna(r):
        checks.append(("RSI(14)", f"{r:.1f}", 1 if r < 30 else -1 if r > 70 else 0))
    if pd.notna(last["MA_M"]):
        checks.append(("終値 vs 25本MA", "上" if last["Close"] > last["MA_M"] else "下",
                       1 if last["Close"] > last["MA_M"] else -1))
    if pd.notna(last["MA_L"]) and pd.notna(last["MA_M"]):
        checks.append(("25MA vs 75MA", "上（上昇トレンド）" if last["MA_M"] > last["MA_L"] else "下（下降トレンド）",
                       1 if last["MA_M"] > last["MA_L"] else -1))
    if pd.notna(last["MACD_HIST"]):
        rising = last["MACD_HIST"] > prev["MACD_HIST"]
        checks.append(("MACDヒストグラム", f"{last['MACD_HIST']:+.3g}（{'拡大' if rising else '縮小'}）",
                       1 if last["MACD_HIST"] > 0 else -1))
    if pd.notna(last["BB_U"]):
        width = last["BB_U"] - last["BB_L"]
        pb = (last["Close"] - last["BB_L"]) / width if width else 0.5
        checks.append(("ボリンジャー %B", f"{pb:.2f}", 1 if pb < 0 else -1 if pb > 1 else 0))
    if pd.notna(last["STO_K"]):
        k = last["STO_K"]
        checks.append(("ストキャス %K", f"{k:.1f}", 1 if k < 20 else -1 if k > 80 else 0))
    vol_ratio = last["Volume"] / last["VOL_MA"] if last.get("VOL_MA") else np.nan

    strat = []
    for name in STRATEGIES:
        t = run_strategy(name, df)
        cur, before = t.iloc[-1], (t.iloc[-2] if len(t) > 1 else 0)
        label = {1: "買い", -1: "売り", 0: "様子見"}[int(cur)]
        fresh = cur != before
        strat.append({"戦略": name, "シグナル": label, "新規": "★ 本日発生" if fresh and cur != 0 else "",
                      "_v": int(cur)})

    ind_score = np.mean([c[2] for c in checks]) if checks else 0
    strat_score = np.mean([s["_v"] for s in strat])
    score = int(round((ind_score * 0.5 + strat_score * 0.5) * 100))
    return {
        "price": last["Close"],
        "change_pct": (last["Close"] / prev["Close"] - 1) * 100,
        "atr_pct": last["ATR"] / last["Close"] * 100 if pd.notna(last["ATR"]) else np.nan,
        "vol_ratio": vol_ratio,
        "rsi": r,
        "checks": checks,
        "strategies": strat,
        "score": score,
    }


def score_label(score: int) -> str:
    if score >= 50:
        return "強い買い"
    if score >= 20:
        return "買い寄り"
    if score <= -50:
        return "強い売り"
    if score <= -20:
        return "売り寄り"
    return "中立"

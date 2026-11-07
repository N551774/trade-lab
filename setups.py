"""狙い目（売買プラン）判定エンジン

チャートのパターンを検出し、
  ・どこで買うか（エントリー）・どこで損切りするか・どこで利確するか
  ・なぜ狙い目なのか（理由）
  ・この銘柄で過去に同じパターンが出たときの成績
をまとめた「トレードプラン」を作る。スイングは買いのみ、デイトレは買い・売り（空売り）の両方。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import indicators as ind


@dataclass
class Plan:
    setup: str            # パターン名
    style: str            # スイング / デイトレ
    entry: float
    stop: float
    target: float
    entry_how: str        # 注文方法の説明
    reasons: list[str]
    quality: float        # 0〜1
    hold: str             # 想定保有期間
    signal_time: pd.Timestamp
    hist_n: int = 0
    hist_win: float = np.nan
    hist_avg_r: float = np.nan
    score: int = 0
    extra: dict = field(default_factory=dict)
    side: str = "買い"     # 買い / 売り（空売り）

    @property
    def risk_pct(self):
        return abs(self.entry - self.stop) / self.entry * 100

    @property
    def reward_pct(self):
        return abs(self.target - self.entry) / self.entry * 100

    @property
    def rr(self):
        return abs(self.target - self.entry) / abs(self.entry - self.stop)


# ---------------------------------------------------------------------------
# 指標の準備
# ---------------------------------------------------------------------------
def prep_daily(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    c = d["Close"]
    d["SMA20"], d["SMA50"], d["SMA200"] = ind.sma(c, 20), ind.sma(c, 50), ind.sma(c, 200)
    d["SMA50_SLOPE"] = d["SMA50"].diff(5)
    d["RSI14"], d["RSI2"] = ind.rsi(c, 14), ind.rsi(c, 2)
    d["ATR"] = ind.atr(d, 14)
    d["VOLMA"] = ind.sma(d["Volume"], 20)
    d["HH20"] = d["High"].rolling(20).max().shift(1)
    d["LL10"] = d["Low"].rolling(10).min().shift(1)
    d["LOW5"] = d["Low"].rolling(5).min()
    sd = c.rolling(20).std(ddof=0)
    d["BBW"] = 4 * sd / d["SMA20"]
    d["BBW_PCT"] = d["BBW"].rolling(120, min_periods=60).rank(pct=True)
    rng = (d["High"] - d["Low"]).replace(0, np.nan)
    d["CLOSE_POS"] = (c - d["Low"]) / rng  # 1=高値引け, 0=安値引け
    return d


def prep_intraday(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    c = d["Close"]
    day = d.index.normalize()
    d["DAY"] = day
    d["VWAP"] = ind.vwap(d)
    d["EMA9"], d["EMA20"] = ind.ema(c, 9), ind.ema(c, 20)
    d["ATR"] = ind.atr(d, 14)
    d["VOLMA"] = ind.sma(d["Volume"], 20)
    d["BAR_NO"] = d.groupby(day).cumcount()
    first6 = d["BAR_NO"] < 6  # 5分足×6本 = 寄り付き30分
    d["OR_H"] = d["High"].where(first6).groupby(day).transform("max")
    d["OR_L"] = d["Low"].where(first6).groupby(day).transform("min")
    daily = d.groupby(day).agg(H=("High", "max"), L=("Low", "min"), C=("Close", "last"))
    prev = daily.shift(1)
    d["PDH"] = day.map(prev["H"])
    d["PDL"] = day.map(prev["L"])
    d["PDC"] = day.map(prev["C"])
    d["DAY_HIGH"] = d.groupby(day)["High"].cummax()
    # 引けまでの残り本数：当日分が途中まででも正しく数えられるよう、過去データで一番遅い足の時刻を「引け」とみなす
    tod = d.index.hour * 60 + d.index.minute
    step = pd.Series(d.index).diff().dt.total_seconds().div(60).median() or 5
    d["BARS_LEFT"] = ((tod.max() - tod) / step).astype(int)
    d["LOW3"] = d["Low"].rolling(3).min()
    d["HIGH3"] = d["High"].rolling(3).max()
    d["CLOSE_POS"] = (c - d["Low"]) / (d["High"] - d["Low"]).replace(0, np.nan)
    return d


# ---------------------------------------------------------------------------
# パターン定義（各関数は、条件・エントリー・損切り・利確の Series を返す）
# ---------------------------------------------------------------------------
def _clip_stop(entry, stop, atr, lo=0.8, hi=2.5):
    """損切り幅を ATR の lo〜hi 倍に収める"""
    stop = np.maximum(stop, entry - hi * atr)
    return np.minimum(stop, entry - lo * atr)


def sw_pullback(d):
    cond = ((d["Close"] > d["SMA50"]) & (d["SMA20"] > d["SMA50"]) & (d["SMA50_SLOPE"] > 0)
            & (d["Low"].rolling(2).min() <= d["SMA20"] * 1.01) & (d["Close"] > d["SMA20"] * 0.98)
            & d["RSI14"].between(35, 58) & (d["Close"] > d["Open"]))
    entry = d["High"] * 1.002
    stop = _clip_stop(entry, d["LOW5"] - 0.2 * d["ATR"], d["ATR"])
    return cond, entry, stop, entry + 2 * (entry - stop)


def sw_breakout(d):
    cond = ((d["Close"] > d["HH20"]) & (d["Close"].shift(1) <= d["HH20"].shift(1))
            & (d["Volume"] > 1.5 * d["VOLMA"]) & (d["CLOSE_POS"] >= 0.6) & (d["Close"] > d["SMA50"]))
    entry = d["Close"]
    stop = _clip_stop(entry, np.minimum(d["Low"], d["HH20"]) - 0.3 * d["ATR"], d["ATR"], 1.0, 2.0)
    return cond, entry, stop, entry + 2 * (entry - stop)


def sw_squeeze(d):
    cond = ((d["BBW_PCT"] < 0.2) & (d["Close"] >= d["HH20"] * 0.97) & (d["Close"] < d["HH20"])
            & (d["Close"] > d["SMA50"]) & (d["SMA50_SLOPE"] > 0))
    entry = d["HH20"] * 1.003
    stop = _clip_stop(entry, d["LL10"] - 0.2 * d["ATR"], d["ATR"])
    return cond, entry, stop, entry + 2 * (entry - stop)


def sw_oversold(d):
    cond = ((d["Close"] > d["SMA200"]) & (d["RSI2"] < 10) & (d["Close"] < d["SMA20"])
            & ((d["Close"] > d["Open"]) | (d["CLOSE_POS"] > 0.5)))
    entry = d["Close"]
    stop = _clip_stop(entry, d["Low"] - 0.5 * d["ATR"], d["ATR"], 1.0, 2.5)
    target = np.maximum(d["SMA20"], entry + 1.2 * (entry - stop))
    return cond, entry, stop, target


def dt_vwap_pullback(d):
    cond = ((d["Close"] > d["VWAP"]) & (d["EMA9"] > d["EMA20"]) & (d["LOW3"] <= d["VWAP"] * 1.002)
            & (d["Close"] > d["Open"]) & (d["BAR_NO"] >= 6) & (d["BARS_LEFT"] >= 6))
    entry = d["High"] + 0.05 * d["ATR"]
    stop = _clip_stop(entry, np.minimum(d["LOW3"], d["VWAP"]) - 0.3 * d["ATR"], d["ATR"], 1.0, 3.0)
    return cond, entry, stop, entry + 2 * (entry - stop)


def dt_orb(d):
    above = d["Close"] > d["OR_H"]
    first = above & ~above.groupby(d["DAY"]).shift(1, fill_value=False)
    cond = (first & (d["BAR_NO"] >= 6) & (d["Volume"] > 1.5 * d["VOLMA"]) & (d["Close"] > d["VWAP"])
            & (d["BARS_LEFT"] >= 6))
    entry = d["Close"]
    stop = _clip_stop(entry, (d["OR_H"] + d["OR_L"]) / 2, d["ATR"], 1.0, 3.0)
    return cond, entry, stop, entry + 2 * (entry - stop)


def dt_pdh_break(d):
    cond = ((d["Close"] > d["PDH"]) & (d["Close"].shift(1) <= d["PDH"]) & (d["Close"] > d["VWAP"])
            & (d["Volume"] > 1.3 * d["VOLMA"]) & (d["BAR_NO"] >= 1) & (d["BARS_LEFT"] >= 6))
    entry = d["Close"]
    stop = _clip_stop(entry, np.minimum(d["Low"], d["PDH"]) - 0.5 * d["ATR"], d["ATR"], 1.0, 3.0)
    return cond, entry, stop, entry + 2 * (entry - stop)


# ---- 売り（空売り）：買いパターンの裏返し --------------------------------------
def _clip_stop_short(entry, stop, atr, lo=1.0, hi=3.0):
    stop = np.minimum(stop, entry + hi * atr)
    return np.maximum(stop, entry + lo * atr)


def dt_vwap_pullback_short(d):
    cond = ((d["Close"] < d["VWAP"]) & (d["EMA9"] < d["EMA20"]) & (d["HIGH3"] >= d["VWAP"] * 0.998)
            & (d["Close"] < d["Open"]) & (d["BAR_NO"] >= 6) & (d["BARS_LEFT"] >= 6))
    entry = d["Low"] - 0.05 * d["ATR"]
    stop = _clip_stop_short(entry, np.maximum(d["HIGH3"], d["VWAP"]) + 0.3 * d["ATR"], d["ATR"])
    return cond, entry, stop, entry - 2 * (stop - entry)


def dt_orb_short(d):
    below = d["Close"] < d["OR_L"]
    first = below & ~below.groupby(d["DAY"]).shift(1, fill_value=False)
    cond = (first & (d["BAR_NO"] >= 6) & (d["Volume"] > 1.5 * d["VOLMA"]) & (d["Close"] < d["VWAP"])
            & (d["BARS_LEFT"] >= 6))
    entry = d["Close"]
    stop = _clip_stop_short(entry, (d["OR_H"] + d["OR_L"]) / 2, d["ATR"])
    return cond, entry, stop, entry - 2 * (stop - entry)


def dt_pdl_break(d):
    cond = ((d["Close"] < d["PDL"]) & (d["Close"].shift(1) >= d["PDL"]) & (d["Close"] < d["VWAP"])
            & (d["Volume"] > 1.3 * d["VOLMA"]) & (d["BAR_NO"] >= 1) & (d["BARS_LEFT"] >= 6))
    entry = d["Close"]
    stop = _clip_stop_short(entry, np.maximum(d["High"], d["PDL"]) + 0.5 * d["ATR"], d["ATR"])
    return cond, entry, stop, entry - 2 * (stop - entry)


SWING = {
    "押し目買い": dict(func=sw_pullback, how="stop", hold=10, hold_txt="数日〜2週間"),
    "高値ブレイク": dict(func=sw_breakout, how="open", hold=10, hold_txt="数日〜2週間"),
    "ブレイク直前": dict(func=sw_squeeze, how="stop", hold=10, hold_txt="数日〜2週間"),
    "売られすぎ反発": dict(func=sw_oversold, how="open", hold=5, hold_txt="2〜5日"),
}
DAY = {
    "VWAP押し目": dict(func=dt_vwap_pullback, how="stop", hold=24, hold_txt="当日中（〜2時間）"),
    "寄り付きレンジ上抜け": dict(func=dt_orb, how="open", hold=24, hold_txt="当日中（〜2時間）"),
    "前日高値ブレイク": dict(func=dt_pdh_break, how="open", hold=24, hold_txt="当日中（〜2時間）"),
}
DAY_SHORT = {
    "VWAP戻り売り": dict(func=dt_vwap_pullback_short, how="stop", hold=24, hold_txt="当日中（〜2時間）", side="売り"),
    "寄り付きレンジ下抜け": dict(func=dt_orb_short, how="open", hold=24, hold_txt="当日中（〜2時間）", side="売り"),
    "前日安値割れ": dict(func=dt_pdl_break, how="open", hold=24, hold_txt="当日中（〜2時間）", side="売り"),
}
DAY_ALL = {**{k: {**v, "side": "買い"} for k, v in DAY.items()}, **DAY_SHORT}

SETUP_HELP = {
    "押し目買い": "上昇トレンド中に一時的に下がった所（20日線付近）で、反発し始めたタイミングを狙う。",
    "高値ブレイク": "直近20日の高値を、出来高を伴って上抜けた勢いに乗る。",
    "ブレイク直前": "値動きが小さく煮詰まり、高値の少し下で待機中。高値を抜けたら買う『待ち伏せ』型。",
    "売られすぎ反発": "長期上昇トレンドの銘柄が短期間で急落したときの、自律反発を短く取る。",
    "VWAP押し目": "当日の平均取引価格（VWAP）の上で推移する強い銘柄が、VWAPまで下がって反発する所を狙う。",
    "寄り付きレンジ上抜け": "寄り付き30分の高値を、出来高を伴って上抜けた勢いに乗る。",
    "前日高値ブレイク": "前日の高値を当日に上抜けた勢いに乗る。",
    "VWAP戻り売り": "【空売り】当日VWAPの下で推移する弱い銘柄が、VWAPまで戻して再び下がり始める所を売る。",
    "寄り付きレンジ下抜け": "【空売り】寄り付き30分の安値を、出来高を伴って下抜けた勢いに乗って売る。",
    "前日安値割れ": "【空売り】前日の安値を当日に下抜けた勢いに乗って売る。",
}


def _neg(d: pd.DataFrame) -> pd.DataFrame:
    """売りの成績を買いの計算で求めるため、価格を上下反転したデータ"""
    n = d.copy()
    n["Open"], n["High"], n["Low"], n["Close"] = -d["Open"], -d["Low"], -d["High"], -d["Close"]
    return n


def history_side(d, cond, entry, stop, target, how, hold, intraday, side):
    if side == "売り":
        return _history(_neg(d), cond, -entry, -stop, -target, how, hold, intraday)
    return _history(d, cond, entry, stop, target, how, hold, intraday)


# ---------------------------------------------------------------------------
# 過去成績（同じパターンが過去に出たとき、損切りより先に利確に届いたか）
# ---------------------------------------------------------------------------
def _history(d, cond, entry, stop, target, how, hold, intraday=False):
    o, h, l, c = (d[k].to_numpy() for k in ("Open", "High", "Low", "Close"))
    days = d["DAY"].to_numpy() if intraday else None
    idx = np.flatnonzero(cond.fillna(False).to_numpy())
    rs, last_used = [], -1
    n = len(d)
    for i in idx:
        if i <= last_used or i >= n - 2:
            continue
        e, s, t = entry.iloc[i], stop.iloc[i], target.iloc[i]
        if not (np.isfinite(e) and np.isfinite(s) and e > s):
            continue
        j = None
        if how == "open":
            j, px = i + 1, o[i + 1]
            if intraday and days[j] != days[i]:
                continue
        else:
            for k in range(i + 1, min(i + 4, n)):
                if intraday and days[k] != days[i]:
                    break
                if h[k] >= e:
                    j, px = k, max(o[k], e)
                    break
            if j is None:
                continue
        risk = px - s
        if risk <= 0:
            continue
        r = None
        end = min(j + hold, n)
        for k in range(j, end):
            if intraday and days[k] != days[j]:
                r = (c[k - 1] - px) / risk
                end = k
                break
            if l[k] <= s:
                r = -1.0 if o[k] > s or k == j else (o[k] - px) / risk
                end = k + 1
                break
            if h[k] >= t:
                r = (t - px) / risk if o[k] < t or k == j else (o[k] - px) / risk
                end = k + 1
                break
        if r is None:
            r = (c[end - 1] - px) / risk
        rs.append(r)
        last_used = end
    if not rs:
        return 0, np.nan, np.nan
    rs = np.array(rs)
    return len(rs), (rs > 0).mean() * 100, rs.mean()


# ---------------------------------------------------------------------------
# 理由文と質（0〜1）
# ---------------------------------------------------------------------------
def _reasons_quality(name, r, cur):
    f = lambda v: f"{cur}{v:,.0f}" if cur == "¥" and v >= 1000 else f"{cur}{v:,.2f}"
    rs, q = [], []
    if name == "押し目買い":
        gap = (r.Close / r.SMA50 - 1) * 100
        rs.append(f"50日線の上で上昇トレンド中（50日線も上向き、50日線から +{gap:.1f}%）")
        rs.append(f"20日線（{f(r.SMA20)}）付近まで下げてから陽線で反発")
        rs.append(f"RSI {r.RSI14:.0f}：過熱感はなく、まだ上値余地あり")
        vr = r.Volume / r.VOLMA
        if vr < 1:
            rs.append(f"下げの出来高は平均の{vr:.1f}倍と少なめ ＝ 売りの勢いは弱い")
        q = [1 - min(abs(gap - 6) / 12, 1), 1 - abs(r.RSI14 - 45) / 15, 1 if vr < 1 else 0.5, r.CLOSE_POS]
    elif name == "高値ブレイク":
        vr = r.Volume / r.VOLMA
        rs.append(f"直近20日の高値 {f(r.HH20)} を上抜け")
        rs.append(f"出来高が平均の{vr:.1f}倍 ＝ 買いが集まっている")
        rs.append("高値近くで引けた（上ヒゲが短い）" if r.CLOSE_POS > 0.8 else "引けにかけても強さを維持")
        ext = (r.Close / r.HH20 - 1) * 100
        q = [min(vr / 3, 1), r.CLOSE_POS, 1 - min(ext / 5, 1), 1 if r.SMA50_SLOPE > 0 else 0.4]
    elif name == "ブレイク直前":
        dist = (r.HH20 / r.Close - 1) * 100
        rs.append(f"値動きの幅（ボリンジャーバンド幅）が過去半年で下位{r.BBW_PCT * 100:.0f}% ＝ 煮詰まり")
        rs.append(f"20日高値 {f(r.HH20)} まであと {dist:.1f}%")
        rs.append("上昇トレンド中（50日線の上・50日線は上向き）")
        q = [1 - r.BBW_PCT * 4, 1 - dist / 3, 0.8]
    elif name == "売られすぎ反発":
        drop = (r.Close / r.SMA20 - 1) * 100
        rs.append("長期では上昇トレンド（200日線の上）")
        rs.append(f"RSI(2) {r.RSI2:.0f}：短期的に売られすぎ（20日線から {drop:.1f}%）")
        rs.append("陽線/下ヒゲで下げ止まりの兆し")
        q = [1 - r.RSI2 / 10, min(-drop / 8, 1), r.CLOSE_POS]
    elif name == "VWAP押し目":
        rs.append(f"当日はVWAP（{f(r.VWAP)}）の上で推移する強い流れ")
        rs.append("VWAPまで下げて陽線で反発")
        rs.append("5分足の短期移動平均が上向き（EMA9 > EMA20）")
        q = [0.7, r.CLOSE_POS if np.isfinite(r.CLOSE_POS) else 0.5, 0.7]
    elif name == "寄り付きレンジ上抜け":
        vr = r.Volume / r.VOLMA
        rs.append(f"寄り付き30分の高値 {f(r.OR_H)} を上抜け")
        rs.append(f"出来高が平均の{vr:.1f}倍")
        rs.append("VWAPより上 ＝ 当日の買い手が優勢")
        q = [min(vr / 3, 1), 0.7, 0.7]
    elif name == "VWAP戻り売り":
        rs.append(f"当日はVWAP（{f(r.VWAP)}）の下で推移する弱い流れ")
        rs.append("VWAPまで戻してから陰線で再び下落")
        rs.append("5分足の短期移動平均が下向き（EMA9 < EMA20）")
        q = [0.7, 1 - r.CLOSE_POS if np.isfinite(r.CLOSE_POS) else 0.5, 0.7]
    elif name == "寄り付きレンジ下抜け":
        vr = r.Volume / r.VOLMA
        rs.append(f"寄り付き30分の安値 {f(r.OR_L)} を下抜け")
        rs.append(f"出来高が平均の{vr:.1f}倍")
        rs.append("VWAPより下 ＝ 当日の売り手が優勢")
        q = [min(vr / 3, 1), 0.7, 0.7]
    elif name == "前日安値割れ":
        vr = r.Volume / r.VOLMA
        rs.append(f"前日の安値 {f(r.PDL)} を下抜け")
        rs.append(f"出来高が平均の{vr:.1f}倍")
        rs.append("VWAPより下で推移")
        q = [min(vr / 2.5, 1), 0.7, 0.7]
    elif name == "前日高値ブレイク":
        vr = r.Volume / r.VOLMA
        rs.append(f"前日の高値 {f(r.PDH)} を上抜け")
        rs.append(f"出来高が平均の{vr:.1f}倍")
        rs.append("VWAPより上で推移")
        q = [min(vr / 2.5, 1), 0.7, 0.7]
    qv = float(np.clip(np.nanmean([np.clip(x, 0, 1) for x in q]), 0, 1)) if q else 0.5
    return rs, qv


def _score(p: Plan) -> int:
    rr = min(p.rr, 3) / 3
    if p.hist_n >= 3:
        hist = np.clip(0.5 + p.hist_avg_r / 2, 0, 1)
    else:
        hist = 0.45
    return int(round(100 * (0.5 * p.quality + 0.2 * rr + 0.3 * hist)))


def _entry_text(name, how, entry, cur, style, side="買い"):
    f = lambda v: f"{cur}{v:,.0f}" if cur == "¥" and v >= 1000 else f"{cur}{v:,.2f}"
    if side == "売り":
        if how == "stop":
            return f"逆指値で {f(entry)} 以下になったら空売り（この後届かなければ見送り）"
        return f"成行/指値で {f(entry)} 付近で空売り（大きく離れたら見送り）"
    if how == "stop":
        when = "次の3営業日以内に" if style == "スイング" else "この後"
        return f"逆指値で {f(entry)} 以上になったら買い（{when}届かなければ見送り）"
    if style == "スイング":
        return f"次の寄り付きで買い（目安 {f(entry)}。+2%以上高く始まったら見送り）"
    return f"成行/指値で {f(entry)} 付近で買い（大きく離れたら見送り）"


# ---------------------------------------------------------------------------
# メイン：銘柄ごとのプランを作る
# ---------------------------------------------------------------------------
def find_plans(df: pd.DataFrame, style: str, cur: str, fresh_bars: int | None = None) -> list[Plan]:
    """最新の足（デイトレは直近数本）でパターンが出ていればプランを返す"""
    intraday = style == "デイトレ"
    if len(df) < (60 if intraday else 80):
        return []
    d = prep_intraday(df) if intraday else prep_daily(df)
    book = DAY_ALL if intraday else SWING
    fresh = fresh_bars or (3 if intraday else 1)
    plans = []
    for name, cfg in book.items():
        cond, entry, stop, target = cfg["func"](d)
        cond = cond.fillna(False)
        recent = np.flatnonzero(cond.to_numpy()[-fresh:])
        if not len(recent):
            continue
        i = len(d) - fresh + recent[-1]
        if intraday and d["DAY"].iloc[i] != d["DAY"].iloc[-1]:
            continue
        e, s, t = float(entry.iloc[i]), float(stop.iloc[i]), float(target.iloc[i])
        if not (np.isfinite(e) and np.isfinite(s) and (e > s if cfg.get("side", "買い") == "買い" else e < s)):
            continue
        hist_cond = cond.copy()
        hist_cond.iloc[-fresh:] = False
        side = cfg.get("side", "買い")
        n, win, avg_r = history_side(d, hist_cond, entry, stop, target, cfg["how"], cfg["hold"], intraday, side)
        reasons, q = _reasons_quality(name, d.iloc[i], cur)
        p = Plan(setup=name, style=style, entry=e, stop=s, target=t,
                 entry_how=_entry_text(name, cfg["how"], e, cur, style, side), reasons=reasons, quality=q,
                 hold=cfg["hold_txt"], signal_time=d.index[i], hist_n=n, hist_win=win, hist_avg_r=avg_r, side=side)
        p.score = _score(p)
        plans.append(p)
    return plans


def pattern_stats(df: pd.DataFrame, style: str) -> list[dict]:
    """全期間で各パターンの成績を集計（検証ページ用）"""
    intraday = style == "デイトレ"
    d = prep_intraday(df) if intraday else prep_daily(df)
    out = []
    for name, cfg in (DAY_ALL if intraday else SWING).items():
        cond, entry, stop, target = cfg["func"](d)
        n, win, avg_r = history_side(d, cond, entry, stop, target, cfg["how"], cfg["hold"], intraday,
                                     cfg.get("side", "買い"))
        out.append({"パターン": name, "回数": n, "勝率%": win, "平均R": avg_r})
    return out


def watch_levels(daily: pd.DataFrame) -> dict | None:
    """デイトレの監視候補：値動きの大きさ・出来高・トレンドと、注目価格"""
    if len(daily) < 60:
        return None
    d = prep_daily(daily)
    r = d.iloc[-1]
    atr_pct = r.ATR / r.Close * 100
    rvol = r.Volume / r.VOLMA if r.VOLMA else np.nan
    trend = 1 if (r.Close > r.SMA20 > r.SMA50) else (-1 if r.Close < r.SMA20 < r.SMA50 else 0)
    score = atr_pct * (0.6 + min(rvol, 3) / 3) * (1.3 if trend == 1 else 1.0 if trend == 0 else 0.7)
    return {"高値": r.High, "安値": r.Low, "終値": r.Close, "ATR%": atr_pct, "出来高倍率": rvol,
            "トレンド": {1: "上昇", 0: "横ばい", -1: "下降"}[trend], "_score": score}


# ---------------------------------------------------------------------------
# 株数の目安
# ---------------------------------------------------------------------------
def position(plan: Plan, ticker: str, capital_jpy: float, risk_pct: float, fx: float, lot: int) -> dict:
    rate = 1.0 if ticker.endswith(".T") else fx
    risk_jpy = capital_jpy * risk_pct / 100
    per = abs(plan.entry - plan.stop) * rate
    by_risk = risk_jpy / per if per > 0 else 0
    by_cap = capital_jpy / (plan.entry * rate)
    raw = int(min(by_risk, by_cap))
    qty = raw // lot * lot
    return {"qty": qty, "raw": raw, "lot": lot, "cost": qty * plan.entry * rate, "loss": qty * per,
            "gain": qty * abs(plan.target - plan.entry) * rate, "limit": "資金" if by_cap < by_risk else "許容損失"}


# ---------------------------------------------------------------------------
# 市場の状態
# ---------------------------------------------------------------------------
def market_status(now: datetime | None = None) -> dict:
    now = now or datetime.now(ZoneInfo("Asia/Tokyo"))
    jp = now.astimezone(ZoneInfo("Asia/Tokyo"))
    ny = now.astimezone(ZoneInfo("America/New_York"))
    hm = jp.hour * 60 + jp.minute
    jp_open = jp.weekday() < 5 and (540 <= hm < 690 or 750 <= hm < 930)
    jp_lunch = jp.weekday() < 5 and 690 <= hm < 750
    nhm = ny.hour * 60 + ny.minute
    us_open = ny.weekday() < 5 and 570 <= nhm < 960
    to_jst = lambda h, m: ny.replace(hour=h, minute=m, second=0, microsecond=0).astimezone(ZoneInfo("Asia/Tokyo")).strftime("%H:%M")
    dst = bool(ny.dst())
    us_open_t, us_close_t = to_jst(9, 30), to_jst(16, 0)
    fut_start, fut_end = to_jst(18, 0), to_jst(17, 0)
    return {
        "東証": "取引中" if jp_open else ("昼休み" if jp_lunch else "取引時間外"),
        "米国": "取引中" if us_open else "取引時間外",
        "米国_開始": "日本時間 " + us_open_t,
        "東証_時間": "前場 9:00〜11:30 ／ 昼休み 11:30〜12:30 ／ 後場 12:30〜15:30",
        "米国_時間": f"{us_open_t}〜翌{us_close_t}（昼休みなし）※いまは{'夏' if dst else '冬'}時間",
        "米国_季節": "夏時間（3月第2日曜〜11月第1日曜）は 22:30〜翌5:00、冬時間は 23:30〜翌6:00",
        "先物_時間": f"ほぼ24時間（月曜朝{fut_start}〜土曜朝{fut_end}、毎朝{fut_end}〜{fut_start}の1時間は休止）",
    }

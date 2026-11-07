"""超短期トレード（5分〜30分で手じまい）の狙い目と検証

・5分足を使い、シグナルの次の足の始値で入り、決めた時間（5/10/15/30分）がたったら終値で手じまい
・損切りは「なし」か「ATR1本分」。損切りに届いたらその値で決済（同じ足の中の順番は分からないので厳しめに扱う）
・1R ＝ ATR（5分足の平均値幅）1本分。損益はRと％で計算し、売買コスト（片道0.05%）を差し引く
・学習期間（前半60%）で一番良かった設定を選び、未使用の検証期間（後半40%）でも勝てるかを確かめる
・プロのデイトレーダーにならい「注目株（窓が大きい・出来高が多い）」と「寄り付き直後」に絞る設定も比べる
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

import indicators as ind

HOLDS = {"5分": 1, "10分": 2, "15分": 3, "30分": 6}
PATTERNS = {
    "寄り付きブレイク": "最初の15分の高値（安値）を抜けた方向について行く",
    "VWAP乗せ": "VWAP（その日の平均取得価格）を上に抜けて、短期の流れも上向き（売りは逆）",
    "勢いの急伸": "出来高を伴って平均の2倍以上動いた足の方向について行く",
    "行き過ぎの戻り": "RSIが極端（20以下/80以上）になった直後の反発を取る",
}
SIDES = ["買いのみ", "売りのみ", "買い＋売り"]
FOCUS = ["全銘柄", "注目株のみ"]  # 注目株＝窓2%以上 or 出来高が普段の2.5倍以上
WINDOWS = ["終日", "寄り後60分"]
STOPS = ["なし", "ATR1本"]
COST_PCT = 0.05  # 片道


def prep(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    c = d["Close"]
    day = d.index.normalize()
    d["DAY"] = day
    d["VWAP"] = ind.vwap(d)
    d["EMA9"], d["EMA20"] = ind.ema(c, 9), ind.ema(c, 20)
    d["ATR"] = ind.atr(d, 14)
    d["VOLMA"] = ind.sma(d["Volume"], 20)
    d["RSI"] = ind.rsi(c, 14)
    d["BAR_NO"] = d.groupby(day).cumcount()
    first3 = d["BAR_NO"] < 3
    d["OR_H"] = d["High"].where(first3).groupby(day).transform("max")
    d["OR_L"] = d["Low"].where(first3).groupby(day).transform("min")
    d["LEFT"] = d.groupby(day).cumcount(ascending=False)  # その日の残り本数
    # 「注目株」の判定：窓（前日終値からのすき間）が2%以上、または出来高が普段の2.5倍以上
    day_open = d["Open"].groupby(day).transform("first")
    prev_close = c.groupby(day).last().shift(1)
    d["GAP"] = (day_open / day.map(prev_close) - 1) * 100
    d["CUMV"] = d["Volume"].groupby(day).cumsum()
    d["CUMV_AVG"] = d.groupby("BAR_NO")["CUMV"].transform(lambda s: s.shift(1).rolling(10, min_periods=5).mean())
    d["RVOL"] = d["CUMV"] / d["CUMV_AVG"]
    d["INPLAY"] = (d["GAP"].abs() >= 2) | (d["RVOL"] >= 2.5)
    d["EARLY"] = d["BAR_NO"] < 12  # 寄り付きから60分以内
    return d


def signals(d: pd.DataFrame) -> dict[tuple[str, int], pd.Series]:
    """{(パターン, 方向 1=買い/-1=売り): 条件}"""
    c, o, h, l = d["Close"], d["Open"], d["High"], d["Low"]
    prev_c = c.shift(1)
    after_or = d["BAR_NO"] >= 3
    rng = h - l
    big = (rng > 2 * d["ATR"].shift(1)) & (d["Volume"] > 2 * d["VOLMA"].shift(1))
    out = {
        ("寄り付きブレイク", 1): after_or & (c > d["OR_H"]) & (prev_c <= d["OR_H"]),
        ("寄り付きブレイク", -1): after_or & (c < d["OR_L"]) & (prev_c >= d["OR_L"]),
        ("VWAP乗せ", 1): (c > d["VWAP"]) & (prev_c <= d["VWAP"].shift(1)) & (d["EMA9"] > d["EMA20"]) & (d["BAR_NO"] >= 2),
        ("VWAP乗せ", -1): (c < d["VWAP"]) & (prev_c >= d["VWAP"].shift(1)) & (d["EMA9"] < d["EMA20"]) & (d["BAR_NO"] >= 2),
        ("勢いの急伸", 1): big & (c > o) & ((c - l) > 0.7 * rng),
        ("勢いの急伸", -1): big & (c < o) & ((h - c) > 0.7 * rng),
        ("行き過ぎの戻り", 1): (d["RSI"].shift(1) < 20) & (c > h.shift(1)),
        ("行き過ぎの戻り", -1): (d["RSI"].shift(1) > 80) & (c < l.shift(1)),
    }
    return {k: v.fillna(False) for k, v in out.items()}


def trades_for(d: pd.DataFrame, sigs: dict, ticker: str) -> pd.DataFrame:
    """全パターン×方向×保有時間×損切りの組み合わせで、1回ごとの結果を計算（あとで組み合わせを選ぶ）"""
    o, h, l, c = (d[k].to_numpy() for k in ("Open", "High", "Low", "Close"))
    atr = d["ATR"].to_numpy()
    left = d["LEFT"].to_numpy()
    inplay = d["INPLAY"].fillna(False).to_numpy()
    early = d["EARLY"].to_numpy()
    idx = d.index
    rows = []
    for (pat, side), cond in sigs.items():
        for i in np.flatnonzero(cond.to_numpy()):
            a = atr[i]
            if not np.isfinite(a) or a <= 0 or i + 1 >= len(d):
                continue
            e_i = i + 1
            if left[i] < 1:  # 次の足が翌日になる
                continue
            entry = o[e_i]
            for hold_name, hb in HOLDS.items():
                if left[i] < hb:  # 引けまでに時間が足りない
                    continue
                x_i = e_i + hb - 1
                for stop in STOPS:
                    exit_p = c[x_i]
                    if stop == "ATR1本":
                        sp = entry - side * a
                        hit = (l[e_i:x_i + 1] <= sp) if side == 1 else (h[e_i:x_i + 1] >= sp)
                        if hit.any():
                            exit_p = sp
                    gross = side * (exit_p - entry)
                    cost = entry * COST_PCT / 100 * 2
                    r = (gross - cost) / a
                    rows.append((ticker, idx[i], idx[i].normalize(), pat, side, hold_name, stop, r,
                                 (gross - cost) / entry * 100, bool(inplay[i]), bool(early[i])))
    return pd.DataFrame(rows, columns=["銘柄", "時刻", "日", "パターン", "方向", "保有", "損切り", "R", "損益%", "注目株", "寄り後60分"])


def research(frames: dict[str, pd.DataFrame], test_frac: float = 0.4, min_trades: int = 60) -> dict:
    allt = []
    for t, df in frames.items():
        if df is None or len(df) < 300:
            continue
        d = prep(df)
        allt.append(trades_for(d, signals(d), t))
    if not allt:
        return {"best": None, "table": pd.DataFrame()}
    tr = pd.concat(allt, ignore_index=True)
    days = sorted(tr["日"].unique())
    split = days[int(len(days) * (1 - test_frac))]
    rows = []
    for pat, side_name, hold, stop, focus, win in itertools.product(list(PATTERNS) + ["すべて"], SIDES, HOLDS, STOPS,
                                                                    FOCUS, WINDOWS):
        x = select(tr, {"パターン": pat, "方向": side_name, "保有": hold, "損切り": stop, "対象": focus, "時間帯": win})
        a, b = x[x["日"] < split], x[x["日"] >= split]
        rows.append({"パターン": pat, "方向": side_name, "保有": hold, "損切り": stop, "対象": focus, "時間帯": win,
                     "学習_回数": len(a), "学習_勝率%": (a["R"] > 0).mean() * 100 if len(a) else np.nan,
                     "学習_平均R": a["R"].mean() if len(a) else np.nan,
                     "検証_回数": len(b), "検証_勝率%": (b["R"] > 0).mean() * 100 if len(b) else np.nan,
                     "検証_平均R": b["R"].mean() if len(b) else np.nan})
    tb = pd.DataFrame(rows)
    ok = tb[tb["学習_回数"] >= min_trades].sort_values("学習_平均R", ascending=False)
    best = ok.iloc[0].to_dict() if len(ok) else None
    cum = select(tr, best).sort_values("時刻")[["時刻", "日", "銘柄", "パターン", "方向", "R"]] if best else None
    return {"best": best, "table": ok, "split": split, "from": days[0], "end": days[-1],
            "n_days": len(days), "n_symbols": tr["銘柄"].nunique(), "trades": cum}


def select(tr: pd.DataFrame, rule: dict) -> pd.DataFrame:
    m = (tr["保有"] == rule["保有"]) & (tr["損切り"] == rule["損切り"])
    if rule["パターン"] != "すべて":
        m &= tr["パターン"] == rule["パターン"]
    if rule["方向"] == "買いのみ":
        m &= tr["方向"] == 1
    elif rule["方向"] == "売りのみ":
        m &= tr["方向"] == -1
    if rule.get("対象") == "注目株のみ":
        m &= tr["注目株"]
    if rule.get("時間帯") == "寄り後60分":
        m &= tr["寄り後60分"]
    return tr[m]


def passed(best: dict | None) -> bool:
    return bool(best and best["検証_回数"] >= 40 and best["検証_平均R"] > 0.03 and best["学習_平均R"] > 0)


def live(df: pd.DataFrame, rule: dict, tz: str, fresh_min: int = 10) -> list[dict]:
    """直近の足で出たシグナル（採用ルールに合うものだけ）。df の時刻は取引所の現地時間（タイムゾーンなし）"""
    if df is None or len(df) < 50:
        return []
    d = prep(df)
    last_t = d.index[-1]
    now = pd.Timestamp.now(tz=tz).tz_localize(None)
    if (now - last_t) > pd.Timedelta(minutes=fresh_min + 5):
        return []
    out = []
    for (pat, side), cond in signals(d).items():
        if rule["パターン"] != "すべて" and pat != rule["パターン"]:
            continue
        if rule["方向"] == "買いのみ" and side != 1 or rule["方向"] == "売りのみ" and side != -1:
            continue
        close_t = last_t.normalize() + pd.Timedelta(hours=16)  # 米国の引け（現地時間16:00）
        bars_left = int((close_t - last_t) / pd.Timedelta(minutes=5))
        if rule.get("対象") == "注目株のみ" and not bool(d["INPLAY"].iloc[-1]):
            continue
        if rule.get("時間帯") == "寄り後60分" and not bool(d["EARLY"].iloc[-1]):
            continue
        if bool(cond.iloc[-1]) and bars_left > HOLDS[rule["保有"]]:
            a = float(d["ATR"].iloc[-1])
            px = float(d["Close"].iloc[-1])
            out.append({"パターン": pat, "方向": "買い" if side == 1 else "空売り", "目安価格": px,
                        "損切り": px - side * a if rule["損切り"] == "ATR1本" else None,
                        "手じまい": (last_t + pd.Timedelta(minutes=5 * (HOLDS[rule["保有"]] + 1))),
                        "ATR": a, "シグナル時刻": last_t})
    return out

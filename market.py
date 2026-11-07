"""相場環境（為替・金利・恐怖指数・主要指数）・ニュース・決算日・為替感応度"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:  # pragma: no cover
    yf = None

MACRO = [
    ("ドル円", "JPY=X", "円"), ("ユーロ円", "EURJPY=X", "円"), ("ドル指数", "DX-Y.NYB", ""),
    ("米10年金利", "^TNX", "%"), ("VIX（恐怖指数）", "^VIX", ""),
    ("日経平均", "^N225", "円"), ("S&P500", "^GSPC", ""), ("NASDAQ", "^IXIC", ""),
    ("WTI原油", "CL=F", "$"), ("金", "GC=F", "$"),
]


def summarize(name: str, df: pd.DataFrame) -> dict:
    c = df["Close"]
    last = c.iloc[-1]

    def chg(n):
        if len(c) <= n:
            return np.nan
        return (last - c.iloc[-1 - n]) * 100 if name == "米10年金利" else (last / c.iloc[-1 - n] - 1) * 100

    sma50 = c.rolling(50).mean().iloc[-1]
    return {"name": name, "last": last, "d1": chg(1), "d5": chg(5), "d20": chg(20),
            "above50": bool(last > sma50) if np.isfinite(sma50) else None}


def weather(s: dict[str, dict]) -> dict:
    """相場の天気（リスクオン/オフ）と、そう判断した理由"""
    score, notes = 0.0, []
    v = s.get("VIX（恐怖指数）")
    if v:
        if v["last"] < 16:
            score += 1
            notes.append(f"VIX {v['last']:.1f}：市場は落ち着いている")
        elif v["last"] > 25:
            score -= 1.5
            notes.append(f"VIX {v['last']:.1f}：市場は不安が強い（急落に注意）")
        elif v["last"] > 20:
            score -= 0.5
            notes.append(f"VIX {v['last']:.1f}：やや警戒")
        if np.isfinite(v["d5"]) and v["d5"] > 25:
            score -= 1
            notes.append(f"VIXが1週間で{v['d5']:+.0f}%急上昇")
    for k in ("S&P500", "日経平均"):
        x = s.get(k)
        if x and x["above50"] is not None:
            score += 1 if x["above50"] else -1
            notes.append(f"{k}は50日線の{'上（上昇基調）' if x['above50'] else '下（下落基調）'}（1ヶ月 {x['d20']:+.1f}%）")
    t = s.get("米10年金利")
    if t and np.isfinite(t["d20"]):
        if t["d20"] > 25:
            score -= 0.5
            notes.append(f"米10年金利が1ヶ月で{t['d20']:+.0f}bp上昇：ハイテク・グロース株に逆風")
        elif t["d20"] < -25:
            score += 0.3
            notes.append(f"米10年金利が1ヶ月で{t['d20']:+.0f}bp低下：株には追い風になりやすい")
    u = s.get("ドル円")
    if u and np.isfinite(u["d5"]):
        if u["d5"] < -2:
            score -= 1
            notes.append(f"1週間で{abs(u['d5']):.1f}%の急な円高：日本の輸出株に逆風")
        elif u["d5"] > 2:
            score += 0.3
            notes.append(f"1週間で{u['d5']:.1f}%の円安：輸出株に追い風、為替介入には注意")
    if score >= 1.5:
        icon, label, advice = "☀️", "晴れ（リスクオン）", "買いの狙い目は通常どおり活用しやすい環境です。"
    elif score <= -1.5:
        icon, label, advice = "☔", "雨（リスクオフ）", "買いは見送るか、株数を半分にするなど慎重に。損切りは必ず守りましょう。"
    else:
        icon, label, advice = "⛅", "くもり（どっちつかず）", "スコアの高い狙い目だけに絞り、無理な取引は控えめに。"
    return {"icon": icon, "label": label, "advice": advice, "notes": notes, "score": score}


def news(ticker: str, n: int = 8) -> list[dict]:
    if yf is None:
        return []
    try:
        items = yf.Ticker(ticker).news or []
    except Exception:
        return []
    out = []
    for it in items:
        c = it.get("content", it)
        title = c.get("title")
        url = (c.get("canonicalUrl") or {}).get("url") or (c.get("clickThroughUrl") or {}).get("url") or c.get("link")
        pub = (c.get("provider") or {}).get("displayName") or c.get("publisher", "")
        ts = c.get("pubDate") or c.get("providerPublishTime")
        try:
            when = pd.to_datetime(ts, unit="s" if isinstance(ts, (int, float)) else None, utc=True).tz_convert("Asia/Tokyo")
        except Exception:
            when = None
        if title and url:
            out.append({"title": title, "url": url, "publisher": pub, "time": when})
    return out[:n]


def earnings_date(ticker: str):
    """次の決算発表日（分からなければ None）"""
    if yf is None:
        return None
    try:
        cal = yf.Ticker(ticker).calendar
        dates = cal.get("Earnings Date") if isinstance(cal, dict) else None
        if dates:
            today = datetime.now().date()
            fut = [pd.Timestamp(d).date() for d in dates if pd.Timestamp(d).date() >= today - timedelta(days=1)]
            return min(fut) if fut else None
    except Exception:
        pass
    return None


def fx_sensitivity(stock: pd.DataFrame, fx: pd.DataFrame, days: int = 120) -> float:
    """日本株の値動きとドル円の連動度（相関 -1〜+1）"""
    a = stock["Close"].pct_change()
    b = fx["Close"].pct_change()
    a.index, b.index = a.index.normalize(), b.index.normalize()
    j = pd.concat([a, b], axis=1, join="inner").dropna().tail(days)
    if len(j) < 40:
        return np.nan
    return float(j.iloc[:, 0].corr(j.iloc[:, 1]))


def fx_label(corr: float) -> str | None:
    if not np.isfinite(corr):
        return None
    if corr >= 0.25:
        return "円安で上がりやすい"
    if corr <= -0.15:
        return "円高で上がりやすい"
    return None


def earnings_history(ticker: str, limit: int = 28) -> list:
    """過去〜直近の決算発表日の一覧（取れなければ空）。日本株は取れないことがある。"""
    if yf is None:
        return []
    try:
        df = yf.Ticker(ticker).get_earnings_dates(limit=limit)
        if df is None or not len(df):
            return []
        return sorted({pd.Timestamp(x).tz_localize(None).normalize() if pd.Timestamp(x).tzinfo else pd.Timestamp(x).normalize()
                       for x in df.index})
    except Exception:
        return []


def estimated_event_days(df: pd.DataFrame) -> list:
    """過去の決算日の推定：大きな窓（ギャップ）＋出来高急増の日。40日以内に重なったら最大のものだけ残す。
    決算発表日の履歴が取れない銘柄の代わりに使う（推定なので完全ではない）。"""
    if df is None or len(df) < 60:
        return []
    c, o, v = df["Close"], df["Open"], df["Volume"]
    prev = c.shift(1)
    tr = pd.concat([df["High"] - df["Low"], (df["High"] - prev).abs(), (df["Low"] - prev).abs()], axis=1).max(axis=1)
    atr_pct = (tr.rolling(20).mean() / prev).shift(1)
    gap = (o / prev - 1).abs()
    volr = v / v.rolling(20).mean().shift(1)
    hit = (gap > np.maximum(0.03, 2.0 * atr_pct)) & (volr > 1.8)
    days = []
    for d_, g in gap[hit].sort_values(ascending=False).items():
        d_ = pd.Timestamp(d_).normalize()
        if all(abs((d_ - x).days) > 40 for x in days):
            days.append(d_)
    # 決算発表は前日の引け後のことが多いので、窓が開いた日の前日を「発表日」とみなす
    return sorted(x - pd.Timedelta(days=1) for x in days)

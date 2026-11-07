"""テクニカル指標"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = gain / loss.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    return out.where(loss != 0, 100.0)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    line = ema(close, fast) - ema(close, slow)
    sig = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return line, sig, line - sig


def bollinger(close: pd.Series, n: int = 20, k: float = 2.0):
    mid = sma(close, n)
    sd = close.rolling(n, min_periods=n).std(ddof=0)
    return mid + k * sd, mid, mid - k * sd


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    prev = df["Close"].shift(1)
    tr = pd.concat([df["High"] - df["Low"], (df["High"] - prev).abs(), (df["Low"] - prev).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def stochastic(df: pd.DataFrame, k: int = 14, d: int = 3):
    lo = df["Low"].rolling(k).min()
    hi = df["High"].rolling(k).max()
    pk = 100 * (df["Close"] - lo) / (hi - lo).replace(0, np.nan)
    return pk, pk.rolling(d).mean()


def vwap(df: pd.DataFrame) -> pd.Series:
    """日中足用：日ごとにリセットする VWAP"""
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    day = df.index.normalize()
    pv = (tp * df["Volume"]).groupby(day).cumsum()
    v = df["Volume"].groupby(day).cumsum().replace(0, np.nan)
    return pv / v


def add_indicators(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    out = df.copy()
    c = out["Close"]
    out["MA_S"] = sma(c, p["ma_short"])
    out["MA_M"] = sma(c, p["ma_mid"])
    out["MA_L"] = sma(c, p["ma_long"])
    out["BB_U"], out["BB_M"], out["BB_L"] = bollinger(c, p["bb_n"], p["bb_k"])
    out["RSI"] = rsi(c, p["rsi_n"])
    out["MACD"], out["MACD_SIG"], out["MACD_HIST"] = macd(c, p["macd_fast"], p["macd_slow"], p["macd_sig"])
    out["ATR"] = atr(out, 14)
    out["STO_K"], out["STO_D"] = stochastic(out)
    out["VOL_MA"] = sma(out["Volume"], 20)
    if p.get("intraday"):
        out["VWAP"] = vwap(out)
    return out


DEFAULT_PARAMS = {
    "ma_short": 5, "ma_mid": 25, "ma_long": 75,
    "bb_n": 20, "bb_k": 2.0,
    "rsi_n": 14,
    "macd_fast": 12, "macd_slow": 26, "macd_sig": 9,
}

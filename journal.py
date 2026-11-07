"""トレード記録（保存先は storage.py：Macではローカル、クラウドではGoogleスプレッドシート）"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import storage

TABLE = "trades"
OLD_DB = Path(__file__).with_name("trades.db")  # 以前の保存形式（自動で引き継ぐ）

COLUMNS = ["id", "symbol", "side", "entry_time", "entry_price", "qty", "stop_price", "target_price",
           "exit_time", "exit_price", "fees", "strategy", "notes"]
JP = {"id": "ID", "symbol": "銘柄", "side": "方向", "entry_time": "エントリー日時", "entry_price": "エントリー価格",
      "qty": "数量", "stop_price": "損切り", "target_price": "利確目標", "exit_time": "決済日時",
      "exit_price": "決済価格", "fees": "手数料", "strategy": "手法", "notes": "メモ"}


def _raw() -> pd.DataFrame:
    df = storage.backend().read(TABLE)
    if not len(df) and isinstance(storage.backend(), storage.LocalBackend) and OLD_DB.exists():
        try:  # 古い SQLite の記録を引き継ぐ
            with sqlite3.connect(OLD_DB) as con:
                df = pd.read_sql("SELECT * FROM trades", con)
            if len(df):
                storage.backend().write(TABLE, df[COLUMNS])
        except Exception:
            df = pd.DataFrame()
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = np.nan
    df = df[COLUMNS].copy()
    for c in ("id", "entry_price", "qty", "stop_price", "target_price", "exit_price", "fees"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ("symbol", "side", "entry_time", "exit_time", "strategy", "notes"):
        df[c] = df[c].astype(object).where(df[c].notna() & (df[c].astype(str) != ""), None)
    return df


def _save(df: pd.DataFrame):
    storage.backend().write(TABLE, df[COLUMNS])


def _ts(v) -> str:
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M")
    return str(v)


def add_trade(symbol, side, entry_time, entry_price, qty, stop_price=None, target_price=None,
              fees=0.0, strategy="", notes="") -> None:
    df = _raw()
    new_id = int(df["id"].max()) + 1 if len(df) and df["id"].notna().any() else 1
    row = {"id": new_id, "symbol": symbol, "side": side, "entry_time": _ts(entry_time), "entry_price": entry_price,
           "qty": qty, "stop_price": stop_price or None, "target_price": target_price or None, "exit_time": None,
           "exit_price": None, "fees": fees, "strategy": strategy, "notes": notes}
    _save(pd.concat([df, pd.DataFrame([row])], ignore_index=True))


def close_trade(trade_id: int, exit_time, exit_price: float, extra_fees: float = 0.0) -> None:
    df = _raw()
    m = df["id"] == trade_id
    df.loc[m, "exit_time"] = _ts(exit_time)
    df.loc[m, "exit_price"] = exit_price
    df.loc[m, "fees"] = df.loc[m, "fees"].fillna(0) + extra_fees
    _save(df)


def delete_trade(trade_id: int) -> None:
    df = _raw()
    _save(df[df["id"] != trade_id])


def import_csv(src: pd.DataFrame) -> int:
    inv = {v: k for k, v in JP.items()}
    src = src.rename(columns=inv)
    n = 0
    for _, r in src.iterrows():
        add_trade(r.get("symbol"), r.get("side", "買い"), r.get("entry_time"), r.get("entry_price"), r.get("qty"),
                  r.get("stop_price"), r.get("target_price"), r.get("fees", 0) or 0, r.get("strategy", ""),
                  r.get("notes", ""))
        if pd.notna(r.get("exit_price")):
            close_trade(int(_raw()["id"].max()), r.get("exit_time"), r.get("exit_price"))
        n += 1
    return n


def load() -> pd.DataFrame:
    df = _raw()
    if df.empty:
        return pd.DataFrame(columns=COLUMNS + ["pnl", "pnl_pct", "r_multiple"])
    df = df.sort_values(["entry_time", "id"], ascending=False).reset_index(drop=True)
    df["id"] = df["id"].astype(int)
    sign = np.where(df["side"] == "買い", 1, -1)
    df["fees"] = df["fees"].fillna(0)
    df["pnl"] = sign * (df["exit_price"] - df["entry_price"]) * df["qty"] - df["fees"]
    df["pnl_pct"] = sign * (df["exit_price"] / df["entry_price"] - 1) * 100
    risk = (df["entry_price"] - df["stop_price"]).abs() * df["qty"]
    df["r_multiple"] = df["pnl"] / risk.replace(0, np.nan)
    return df


def stats(df: pd.DataFrame) -> dict:
    closed = df[df["exit_price"].notna()]
    n = len(closed)
    if n == 0:
        return {"n": 0}
    w = closed[closed["pnl"] > 0]
    lo = closed[closed["pnl"] <= 0]
    gl = -lo["pnl"].sum()
    win_rate = len(w) / n
    avg_w = w["pnl"].mean() if len(w) else 0
    avg_l = lo["pnl"].mean() if len(lo) else 0
    streak = mx = 0
    for p in closed.sort_values("exit_time")["pnl"]:
        streak = streak + 1 if p <= 0 else 0
        mx = max(mx, streak)
    return {
        "n": n, "total": closed["pnl"].sum(), "win_rate": win_rate * 100,
        "avg_win": avg_w, "avg_loss": avg_l,
        "payoff": avg_w / -avg_l if avg_l < 0 else np.nan,
        "pf": w["pnl"].sum() / gl if gl > 0 else np.nan,
        "expectancy": win_rate * avg_w + (1 - win_rate) * avg_l,
        "max_losing_streak": mx,
        "avg_r": closed["r_multiple"].mean(),
    }


def position_size(account: float, risk_pct: float, entry: float, stop: float, lot: int = 1) -> dict:
    """許容損失から建てられる数量を計算（日本株は lot=100）"""
    per_share = abs(entry - stop)
    if per_share <= 0 or entry <= 0:
        return {"qty": 0, "risk": 0, "notional": 0}
    risk_amt = account * risk_pct / 100
    qty = int(risk_amt / per_share // lot * lot)
    return {"qty": qty, "risk": qty * per_share, "notional": qty * entry, "per_share": per_share}

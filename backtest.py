"""バックテスト（シグナル足の次の始値で執行、損切り・利確は足中の高安で判定）"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

import strategies as st


def run_backtest(df: pd.DataFrame, target: pd.Series, capital: float = 1_000_000,
                 fee_pct: float = 0.0, slip_pct: float = 0.0,
                 sl_pct: float | None = None, tp_pct: float | None = None,
                 allow_short: bool = False, size_pct: float = 100.0,
                 bars_per_year: int = 252) -> dict:
    o, h, l, c = (df[k].to_numpy() for k in ("Open", "High", "Low", "Close"))
    idx = df.index
    tgt = target.shift(1).fillna(0).to_numpy()  # 前の足の判断を今の足の始値で執行
    if not allow_short:
        tgt = np.clip(tgt, 0, None)
    fee, slip = fee_pct / 100, slip_pct / 100
    sl = sl_pct / 100 if sl_pct else None
    tp = tp_pct / 100 if tp_pct else None

    cash = capital
    side, qty, entry_px, entry_i, entry_fee = 0, 0.0, 0.0, -1, 0.0
    blocked = None  # 損切り/利確後、シグナルが変わるまで再エントリーしない
    trades, equity = [], np.empty(len(df))

    def close_pos(i, px, reason):
        nonlocal cash, side, qty
        exit_fee = qty * px * fee
        pnl = side * qty * (px - entry_px) - entry_fee - exit_fee
        cash += side * qty * (px - entry_px) - exit_fee
        trades.append({
            "エントリー日時": idx[entry_i], "決済日時": idx[i], "方向": "買い" if side == 1 else "売り",
            "エントリー価格": entry_px, "決済価格": px, "数量": qty, "損益": pnl,
            "損益率%": side * (px / entry_px - 1) * 100 - fee * 200, "保有本数": i - entry_i, "決済理由": reason,
        })
        side, qty = 0, 0.0

    for i in range(len(df)):
        want = tgt[i]
        if blocked is not None:
            if want != blocked:
                blocked = None
            else:
                want = 0
        # 1) 始値でシグナル執行
        if side != 0 and want != side:
            close_pos(i, o[i] * (1 - side * slip), "シグナル")
        if side == 0 and want != 0:
            side = int(want)
            entry_px = o[i] * (1 + side * slip)
            qty = cash * size_pct / 100 / (entry_px * (1 + fee))
            entry_fee = qty * entry_px * fee
            cash -= entry_fee
            entry_i = i
        # 2) 足中の損切り・利確
        if side != 0:
            if side == 1:
                sl_px = entry_px * (1 - sl) if sl else None
                tp_px = entry_px * (1 + tp) if tp else None
                if sl_px and l[i] <= sl_px:
                    blocked = 1
                    close_pos(i, min(o[i], sl_px) if entry_i < i else sl_px, "損切り")
                elif tp_px and h[i] >= tp_px:
                    blocked = 1
                    close_pos(i, max(o[i], tp_px) if entry_i < i else tp_px, "利確")
            else:
                sl_px = entry_px * (1 + sl) if sl else None
                tp_px = entry_px * (1 - tp) if tp else None
                if sl_px and h[i] >= sl_px:
                    blocked = -1
                    close_pos(i, max(o[i], sl_px) if entry_i < i else sl_px, "損切り")
                elif tp_px and l[i] <= tp_px:
                    blocked = -1
                    close_pos(i, min(o[i], tp_px) if entry_i < i else tp_px, "利確")
        equity[i] = cash + (side * qty * (c[i] - entry_px) if side else 0)

    open_pos = None
    if side != 0:
        open_pos = {"方向": "買い" if side == 1 else "売り", "エントリー価格": entry_px,
                    "含み損益": side * qty * (c[-1] - entry_px)}

    eq = pd.Series(equity, index=idx)
    tr = pd.DataFrame(trades)
    return {"equity": eq, "trades": tr, "stats": _stats(eq, tr, capital, df, bars_per_year), "open": open_pos}


def _stats(eq: pd.Series, tr: pd.DataFrame, capital: float, df: pd.DataFrame, bpy: int) -> dict:
    rets = eq.pct_change().fillna(0)
    dd = eq / eq.cummax() - 1
    n = len(tr)
    wins = tr[tr["損益"] > 0] if n else tr
    losses = tr[tr["損益"] <= 0] if n else tr
    gross_win = wins["損益"].sum() if n else 0
    gross_loss = -losses["損益"].sum() if n else 0
    years = max(len(eq) / bpy, 1e-9)
    total = eq.iloc[-1] / capital - 1
    bh = df["Close"].iloc[-1] / df["Open"].iloc[0] - 1
    return {
        "最終資産": eq.iloc[-1],
        "総リターン%": total * 100,
        "年率リターン%": ((1 + total) ** (1 / years) - 1) * 100 if total > -1 else -100,
        "バイ&ホールド%": bh * 100,
        "最大ドローダウン%": dd.min() * 100,
        "シャープレシオ": rets.mean() / rets.std() * np.sqrt(bpy) if rets.std() > 0 else 0,
        "取引回数": n,
        "勝率%": len(wins) / n * 100 if n else 0,
        "プロフィットファクター": gross_win / gross_loss if gross_loss > 0 else (np.inf if gross_win > 0 else 0),
        "平均利益": wins["損益"].mean() if len(wins) else 0,
        "平均損失": losses["損益"].mean() if len(losses) else 0,
        "平均保有本数": tr["保有本数"].mean() if n else 0,
    }


def optimize(df: pd.DataFrame, name: str, grid: dict[str, list], metric: str = "総リターン%",
             min_trades: int = 3, **bt_kwargs) -> pd.DataFrame:
    """パラメータの総当たり。過剰最適化に注意（別期間での検証を推奨）。"""
    keys = list(grid)
    rows = []
    base = st.default_params(name)
    for combo in itertools.product(*(grid[k] for k in keys)):
        params = {**base, **dict(zip(keys, combo))}
        if name in ("移動平均クロス", "MACDクロス") and params["fast"] >= params["slow"]:
            continue
        res = run_backtest(df, st.run_strategy(name, df, params), **bt_kwargs)
        s = res["stats"]
        if s["取引回数"] < min_trades:
            continue
        rows.append({**params, **{k: s[k] for k in ("総リターン%", "最大ドローダウン%", "勝率%",
                                                      "プロフィットファクター", "シャープレシオ", "取引回数")}})
    out = pd.DataFrame(rows)
    return out.sort_values(metric, ascending=False).reset_index(drop=True) if len(out) else out

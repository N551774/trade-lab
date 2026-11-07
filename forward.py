"""毎日の成績記録（フォワードテスト）

開始日以降の取引日について、その日が終わったあとに「採用中のルールで仮想売買したらどうなったか」を
自動で記録する。記録した日の結果は後から書き換えない（後でルールを変えても、過去の記録はそのまま）。
  ・デイトレ：取引日ごとに、5分足のリプレイ結果を1行ずつ保存（取引なしの日も保存）
  ・スイング：開始日からの仮想売買を日足で計算（決済済みの取引と、保有中のポジション）
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import papertrade as pt

JST, NY = ZoneInfo("Asia/Tokyo"), ZoneInfo("America/New_York")
DEFAULT_START = "2026-11-05"


class Store:
    """保存先は storage.py（ローカル or Googleスプレッドシート）"""
    DAYS, TRADES = "forward_day", "forward_day_trades"

    def __init__(self, folder: Path | None = None):
        import storage
        self.st = storage
        # 以前の保存形式（forward_meta.json）を引き継ぐ
        old = Path(folder or storage.DATA_DIR) / "forward_meta.json"
        if storage.get("forward_start") is None and old.exists():
            try:
                storage.put("forward_start", json.loads(old.read_text(encoding="utf-8"))["start"])
            except Exception:
                pass

    def start(self) -> pd.Timestamp:
        return pd.Timestamp(self.st.get("forward_start", DEFAULT_START))

    def reset(self, start: pd.Timestamp):
        self.st.put("forward_start", f"{start:%Y-%m-%d}")
        self.st.backend().write(self.DAYS, pd.DataFrame(columns=["市場", "日付", "取引数", "勝ち", "損益", "ルール", "記録時刻"]))
        self.st.backend().write(self.TRADES, pd.DataFrame())

    def load_days(self) -> pd.DataFrame:
        df = self.st.backend().read(self.DAYS)
        if not len(df) or "日付" not in df.columns:
            return pd.DataFrame(columns=["市場", "日付", "取引数", "勝ち", "損益", "ルール", "記録時刻"])
        df["日付"] = pd.to_datetime(df["日付"])
        for c in ("取引数", "勝ち", "損益"):
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        return df

    def load_trades(self) -> pd.DataFrame:
        return self.st.backend().read(self.TRADES)

    def append(self, days: pd.DataFrame, trades: pd.DataFrame):
        if len(days):
            self.st.backend().append(self.DAYS, days)
        if len(trades):
            self.st.backend().append(self.TRADES, trades)


def completed_sessions(sessions, market: str, now: datetime | None = None) -> list:
    """取引が終わった日だけ（当日は引け後のみ）"""
    now = now or datetime.now(JST)
    if market == "米国":
        loc = now.astimezone(NY)
        close_min = 16 * 60 + 5
    else:
        loc = now.astimezone(JST)
        close_min = 15 * 60 + 35
    today = pd.Timestamp(loc.date())
    done_today = loc.hour * 60 + loc.minute >= close_min
    return [s for s in sessions if s < today or (s == today and done_today)]


def update_day(store: Store, market: str, frames: dict, names: dict, index_df, capital, risk, fx,
               rule: dict | None) -> int:
    """未記録の取引日を記録する。戻り値＝新しく記録した日数"""
    start = store.start()
    rec = store.load_days()
    have = set(pd.to_datetime(rec[rec["市場"] == market]["日付"]).dt.normalize()) if len(rec) else set()
    sess = sorted(set().union(*[set(df.index.normalize()) for df in frames.values() if len(df)]))
    todo = [s for s in completed_sessions(sess, market) if s >= start and s not in have]
    if not todo:
        return 0
    k = sum(1 for s in sess if s >= todo[0])
    prep = pt.prepare(frames, k, index_df)
    tr = pt.simulate(prep, names, capital, risk, fx, rule, use_filter=index_df is not None)
    label = pt.rule_label(rule or pt.DEFAULT_RULE) + "／相場フィルターあり"
    rows, trows = [], []
    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    for s in todo:
        t_ = tr[tr["買い時刻"].dt.normalize() == s] if len(tr) else tr
        rows.append({"市場": market, "日付": s, "取引数": len(t_), "勝ち": int((t_["損益(円)"] > 0).sum()) if len(t_) else 0,
                     "損益": round(float(t_["損益(円)"].sum()), 0) if len(t_) else 0.0, "ルール": label, "記録時刻": now})
        if len(t_):
            x = t_.drop(columns=["累積損益(円)"], errors="ignore").copy()
            x.insert(0, "市場", market)
            trows.append(x)
    store.append(pd.DataFrame(rows), pd.concat(trows) if trows else pd.DataFrame())
    return len(todo)


def swing_forward(frames: dict, names: dict, index_frames: dict, earnings: dict, capital, risk, fx, rule: dict,
                  start: pd.Timestamp) -> dict:
    prep = pt.prepare_swing(frames, index_frames, earnings)
    tr, open_pos = pt.simulate_swing(prep, names, capital, risk, fx, rule, start=start, return_open=True)
    return {"trades": tr, "open": open_pos}

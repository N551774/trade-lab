"""仮想売買（リプレイ）と、ルールの検証（学習期間で選び、未使用の期間で確かめる）

実際の5分足データを使い、取引日を「1本ずつ時間を進めながら」再生して、
アプリの狙い目ルールどおりに売買したらどうなったかを記録する。
  ・各時点では、その時点までのデータだけで判断（未来のデータは使わない）
  ・シグナル足の次の足で約定（逆指値は3本以内に届かなければ取り消し）
  ・損切り・利確は足の高値/安値で判定。同じ足で両方に届いた場合は損切りを優先（厳しめ）
  ・引けの足で必ず決済（持ち越しなし）
  ・同時保有は最大N銘柄、合計の買付金額は資金以内
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

import setups as su

DEFAULT_RULE = {"stop": "標準", "target_r": 2.0, "patterns": "すべて"}
# パターンのまとまり（「すべて」は買いのみ＝最初のルールと同じ）
GROUPS = {
    "すべて": set(su.DAY),
    "売りのみ（すべて）": set(su.DAY_SHORT),
    "買い＋売り（すべて）": set(su.DAY_ALL),
}


def _signals(df: pd.DataFrame, start: pd.Timestamp, cur: str) -> list[dict]:
    d = su.prep_intraday(df)
    atr = d["ATR"].to_numpy()
    out = []
    for name, cfg in su.DAY_ALL.items():
        side = cfg["side"]
        cond, entry, stop, target = cfg["func"](d)
        cond = cond.fillna(False)
        past = cond & (d.index < start)
        n, win, avg_r = su.history_side(d, past, entry, stop, target, cfg["how"], cfg["hold"], True, side)
        for i in np.flatnonzero((cond & (d.index >= start)).to_numpy()):
            e, s, t = float(entry.iloc[i]), float(stop.iloc[i]), float(target.iloc[i])
            ok = e > s if side == "買い" else e < s
            if not (np.isfinite(e) and np.isfinite(s) and ok and np.isfinite(atr[i])):
                continue
            reasons, q = su._reasons_quality(name, d.iloc[i], cur)
            p = su.Plan(setup=name, style="デイトレ", entry=e, stop=s, target=t, entry_how="", reasons=reasons,
                        quality=q, hold=cfg["hold_txt"], signal_time=d.index[i], hist_n=n, hist_win=win,
                        hist_avg_r=avg_r, side=side)
            p.score = su._score(p)
            out.append({"i": i, "time": d.index[i], "plan": p, "how": cfg["how"], "atr": float(atr[i])})
    return out


def prepare(frames: dict[str, pd.DataFrame], days: int, market: pd.DataFrame | None = None) -> dict:
    """シグナル計算など重い処理を1回だけ行う（ルール違いの比較で使い回す）"""
    sess = sorted(set().union(*[set(df.index.normalize()) for df in frames.values() if len(df)]))
    if len(sess) < days + 5:
        days = max(1, len(sess) - 5)
    start = sess[-days]
    bars, raw = {}, {}
    for t, df in frames.items():
        if len(df) < 200:
            continue
        cur = "¥" if t.endswith(".T") else "$"
        raw[t] = _signals(df, start, cur)
        day = df.index.normalize()
        last = np.r_[day[1:] != day[:-1], True]
        o, h, l, c = (df[k].to_numpy() for k in ("Open", "High", "Low", "Close"))
        # 売りは「価格を上下反転した買い」として同じ計算で扱う
        bars[t] = {1: (o, h, l, c), -1: (-o, -l, -h, -c), "idx": df.index, "day": day, "last": last}
    events = []
    for t, b in bars.items():
        events += [(b["idx"][i], t, i) for i in np.flatnonzero(b["idx"] >= start)]
    events.sort()
    mkt_up = mkt_dn = None
    if market is not None and len(market):
        md = su.prep_intraday(market)
        mkt_up = ((md["Close"] > md["VWAP"]) & (md["EMA9"] > md["EMA20"])).to_dict()
        mkt_dn = ((md["Close"] < md["VWAP"]) & (md["EMA9"] < md["EMA20"])).to_dict()
    return {"bars": bars, "raw": raw, "events": events, "start": start, "days": days,
            "mkt_up": mkt_up, "mkt_dn": mkt_dn, "sessions": [s for s in sess if s >= start]}


def _apply_rule(sig: dict, rule: dict):
    """損切り・利確のルールを差し替える（買いは下に、売りは上に損切り）"""
    p = sig["plan"]
    e = p.entry
    sgn = 1 if p.side == "買い" else -1
    stop = p.stop if rule["stop"] == "標準" else e - sgn * float(rule["stop"]) * sig["atr"]
    if rule["target_r"] is None:
        target = sgn * np.inf  # 利確なし（損切りか引けまで）
    else:
        target = e + sgn * rule["target_r"] * abs(e - stop)
    return stop, target


def _pattern_set(name: str):
    return GROUPS.get(name, {name})


def simulate(prep: dict, names: dict, capital_jpy: float, risk_pct: float, fx: float, rule: dict | None = None,
             max_pos: int = 3, min_score: int = 50, hide_bad: bool = True, allow_odd_lot: bool = True,
             cost_pct: float = 0.05, use_filter: bool = True) -> pd.DataFrame:
    rule = rule or DEFAULT_RULE
    pats = _pattern_set(rule["patterns"])
    sigs = {}
    for t, lst in prep["raw"].items():
        sigs[t] = {}
        for s in lst:
            p = s["plan"]
            if p.setup not in pats:
                continue
            if hide_bad and p.hist_n >= 3 and p.hist_avg_r < 0:
                continue
            if p.score < min_score:
                continue
            prev = sigs[t].get(s["i"])
            if prev is None or p.score > prev["plan"].score:
                sigs[t][s["i"]] = s
    positions, pending, trades, traded_today = {}, {}, [], set()
    cur_day = None
    cost = cost_pct / 100
    for ts, t, i in prep["events"]:
        b = prep["bars"][t]
        rate = 1.0 if t.endswith(".T") else fx
        lot = 1 if (allow_odd_lot or not t.endswith(".T")) else 100
        day = b["day"][i]
        if day != cur_day:
            cur_day, traded_today = day, set()
            pending.clear()

        # 1) 約定待ち（売りは上下反転した価格で、買いと同じ判定）
        if t in pending and t not in positions:
            pd_ = pending[t]
            sg = pd_["sg"]
            o, h, l, c = (x[i] for x in b[sg])
            fill = o if pd_["how"] == "open" else (max(o, pd_["entry"]) if h >= pd_["entry"] else None)
            if fill is not None and fill > pd_["stop"]:
                used = sum(x["qty"] * abs(x["entry_px"]) * x["rate"] for x in positions.values())
                per = (fill - pd_["stop"]) * rate
                qty = min(capital_jpy * risk_pct / 100 / per, (capital_jpy - used) / (abs(fill) * rate))
                qty = int(qty // lot * lot)
                if qty >= lot and len(positions) < max_pos:
                    positions[t] = {**pd_, "entry_px": fill + abs(fill) * cost, "qty": qty, "rate": rate,
                                    "t_in": ts, "i_in": i}
                    traded_today.add(t)
                del pending[t]
            elif fill is None:
                pd_["wait"] += 1
                if pd_["wait"] > 3:
                    del pending[t]
            else:
                del pending[t]

        # 2) 決済
        if t in positions:
            pos = positions[t]
            sg = pos["sg"]
            o, h, l, c = (x[i] for x in b[sg])
            ex = why = None
            if l <= pos["stop"]:
                ex, why = (min(o, pos["stop"]) if i > pos["i_in"] else pos["stop"]), "損切り"
            elif h >= pos["target"]:
                ex, why = (max(o, pos["target"]) if i > pos["i_in"] else pos["target"]), "利確"
            elif b["last"][i]:
                ex, why = c, "引けで決済"
            if ex is not None:
                ex = ex - abs(ex) * cost
                p = pos["plan"]
                tg = pos["target"] * sg
                trades.append({
                    "日付": pos["t_in"].strftime("%m/%d"), "銘柄": names.get(t, t), "ティッカー": t,
                    "売買": p.side, "パターン": p.setup, "スコア": p.score, "買い時刻": pos["t_in"],
                    "買値": pos["entry_px"] * sg, "損切り": pos["stop"] * sg, "利確": tg if np.isfinite(tg) else np.nan,
                    "売り時刻": ts, "売値": ex * sg, "株数": pos["qty"], "決済理由": why,
                    "損益(円)": (ex - pos["entry_px"]) * pos["qty"] * pos["rate"],
                    "R": (ex - pos["entry_px"]) / (pos["entry_px"] - pos["stop"]),
                })
                del positions[t]

        # 3) 新しいシグナル（引けの直前は新規なし）
        if t not in positions and t not in pending and t not in traded_today and i in sigs.get(t, {}) and not b["last"][i]:
            s = sigs[t][i]
            p = s["plan"]
            sg = 1 if p.side == "買い" else -1
            if use_filter and prep["mkt_up"] is not None:
                ok = (prep["mkt_up"] if sg == 1 else prep["mkt_dn"]).get(ts, False)
            else:
                ok = True
            if ok and len(positions) + len(pending) < max_pos:
                stop, target = _apply_rule(s, rule)
                if (p.entry - stop) * sg > 0:
                    pending[t] = {"plan": p, "how": s["how"], "wait": 0, "sg": sg, "entry": p.entry * sg,
                                  "stop": stop * sg, "target": target * sg}
    tr = pd.DataFrame(trades)
    if len(tr):
        tr = tr.sort_values("買い時刻").reset_index(drop=True)
        tr["累積損益(円)"] = tr["損益(円)"].cumsum()
    return tr


def summarize(tr: pd.DataFrame, days: int) -> dict:
    if not len(tr):
        return {}
    w = tr[tr["損益(円)"] > 0]
    lo = tr[tr["損益(円)"] <= 0]
    cum = tr["損益(円)"].cumsum()
    return {"取引日数": days, "取引数": len(tr), "勝率%": len(w) / len(tr) * 100,
            "損益合計": tr["損益(円)"].sum(), "平均R": tr["R"].mean(),
            "プロフィットファクター": w["損益(円)"].sum() / -lo["損益(円)"].sum() if len(lo) and lo["損益(円)"].sum() < 0 else np.inf,
            "最大の負け": tr["損益(円)"].min(), "最大の勝ち": tr["損益(円)"].max(),
            "最大ドローダウン": (cum - cum.cummax()).min()}


def replay(frames, names, days, capital_jpy, risk_pct, fx, max_pos=3, min_score=50, hide_bad=True,
           allow_odd_lot=True, cost_pct=0.05, market=None, rule=None) -> dict:
    prep = prepare(frames, days, market)
    tr = simulate(prep, names, capital_jpy, risk_pct, fx, rule, max_pos, min_score, hide_bad, allow_odd_lot,
                  cost_pct, use_filter=market is not None)
    daily = (tr.groupby("日付").agg(取引数=("損益(円)", "size"), 勝ち=("損益(円)", lambda x: int((x > 0).sum())),
                                   損益=("損益(円)", "sum")).reset_index() if len(tr) else pd.DataFrame())
    return {"trades": tr, "daily": daily, "summary": summarize(tr, prep["days"]), "start": prep["start"], "days": prep["days"]}


# ---------------------------------------------------------------------------
# ルールの検証：学習期間で選んだ設定が、未使用の期間でも勝てるか
# ---------------------------------------------------------------------------
GRID = {
    "stop": ["標準", 1.5, 2.5, 4.0],            # 標準=パターン既定 / 数字=ATRの何倍に損切り
    "target_r": [1.0, 1.5, 2.0, 3.0, None],      # 損切り幅の何倍で利確 / None=利確なし（引けまで）
    "patterns": list(GROUPS) + list(su.DAY_ALL),
}


def rule_label(r: dict) -> str:
    st_ = "損切り=標準" if r["stop"] == "標準" else f"損切り=ATR×{r['stop']}"
    tg = "利確なし(引けまで)" if r["target_r"] is None else f"利確={r['target_r']}R"
    pat = "買いのみ（すべて）" if r["patterns"] == "すべて" else r["patterns"]
    return f"{st_}／{tg}／{pat}"


def research(frames, names, total_days, test_days, capital_jpy, risk_pct, fx, market=None, min_trades=15,
             **kw) -> dict:
    prep = prepare(frames, total_days, market)
    sess = prep["sessions"]
    split = sess[-test_days] if len(sess) > test_days else sess[0]
    rows = []
    for stop, tgt, pat in itertools.product(*GRID.values()):
        rule = {"stop": stop, "target_r": tgt, "patterns": pat}
        tr = simulate(prep, names, capital_jpy, risk_pct, fx, rule, use_filter=market is not None, **kw)
        if not len(tr):
            continue
        d = tr["買い時刻"].dt.normalize()
        a, b = tr[d < split], tr[d >= split]
        rows.append({"ルール": rule_label(rule), "_rule": rule,
                     "学習_回数": len(a), "学習_勝率%": (a["R"] > 0).mean() * 100 if len(a) else np.nan,
                     "学習_平均R": a["R"].mean() if len(a) else np.nan, "学習_損益": a["損益(円)"].sum(),
                     "検証_回数": len(b), "検証_勝率%": (b["R"] > 0).mean() * 100 if len(b) else np.nan,
                     "検証_平均R": b["R"].mean() if len(b) else np.nan, "検証_損益": b["損益(円)"].sum()})
    df = pd.DataFrame(rows)
    ok = df[df["学習_回数"] >= min_trades].sort_values("学習_平均R", ascending=False) if len(df) else df
    # 選び方：パターンを1つに絞らない（まとまり）設定の中から、学習期間の成績で選ぶ（スイングの反省を反映）
    grp = ok[ok["_rule"].map(lambda r: r["patterns"] in GROUPS)] if len(ok) else ok
    pick = grp if len(grp) else ok
    best = pick.iloc[0].to_dict() if len(pick) else None
    base = df[df["ルール"] == rule_label(DEFAULT_RULE)]
    return {"table": ok, "best": best, "base": base.iloc[0].to_dict() if len(base) else None,
            "train_from": sess[0], "split": split, "end": sess[-1],
            "n_train": sum(s < split for s in sess), "n_test": sum(s >= split for s in sess)}


# ===========================================================================
# スイング（日足）の仮想売買と検証
# ===========================================================================
SWING_GRID = {
    "avoid_earnings": [False, True],           # 保有期間に決算発表が入る取引は見送る
    "filter": [True, False],                   # 指数が50日線の上の時だけ買う
    "patterns": ["すべて", "押し目買い", "高値ブレイク", "ブレイク直前", "売られすぎ反発"],
    "stop": ["標準", 1.5, 2.5],                 # 標準=パターン既定 / 数字=ATR(日足)の何倍下
    "target_r": [1.5, 2.0, 3.0, None],          # None=利確なし（保有期限まで）
}
SWING_DEFAULT = {"avoid_earnings": False, "filter": False, "patterns": "すべて", "stop": "標準", "target_r": 2.0}


def swing_rule_label(r: dict) -> str:
    st_ = "損切り=標準" if r["stop"] == "標準" else f"損切り=ATR×{r['stop']}"
    tg = "利確なし(期限まで)" if r["target_r"] is None else f"利確={r['target_r']}R"
    ea = "／決算回避" if r.get("avoid_earnings") else ""
    return f"{'相場フィルターあり' if r['filter'] else 'フィルターなし'}{ea}／{st_}／{tg}／{r['patterns']}"


def prepare_swing(frames: dict[str, pd.DataFrame], index_frames: dict[str, pd.DataFrame],
                  earnings: dict[str, list] | None = None) -> dict:
    """index_frames: {'US': ^GSPC日足, 'JP': ^N225日足} / earnings: {ティッカー: 決算発表日のリスト}"""
    earnings = earnings or {}
    regime = {}
    for k, df in index_frames.items():
        if df is not None and len(df):
            c = df["Close"]
            regime[k] = (c > c.rolling(50).mean()).rename(None)
            regime[k].index = regime[k].index.normalize()
    bars, raw = {}, {}
    for t, df in frames.items():
        if len(df) < 260:
            continue
        cur = "¥" if t.endswith(".T") else "$"
        d = su.prep_daily(df)
        d.index = d.index.normalize()
        lst = []
        for name, cfg in su.SWING.items():
            cond, entry, stop, target = cfg["func"](d)
            for i in np.flatnonzero(cond.fillna(False).to_numpy()):
                if i < 200:
                    continue
                e, s = float(entry.iloc[i]), float(stop.iloc[i])
                tg = float(target.iloc[i])
                a = float(d["ATR"].iloc[i])
                if not (np.isfinite(e) and np.isfinite(s) and e > s and np.isfinite(a)):
                    continue
                _, q = su._reasons_quality(name, d.iloc[i], cur)
                dt0 = d.index[i]
                horizon = dt0 + pd.Timedelta(days=int(cfg["hold"] * 1.5) + 4)
                earn = any(dt0 < x <= horizon for x in earnings.get(t, []))
                lst.append({"i": i, "date": dt0, "setup": name, "how": cfg["how"], "hold": cfg["hold"],
                            "entry": e, "stop": s, "target": tg, "atr": a, "q": q, "earn": earn})
        raw[t] = lst
        bars[t] = {"o": d["Open"].to_numpy(), "h": d["High"].to_numpy(), "l": d["Low"].to_numpy(),
                   "c": d["Close"].to_numpy(), "idx": d.index}
    days = sorted(set().union(*[set(b["idx"]) for b in bars.values()]))
    return {"bars": bars, "raw": raw, "regime": regime, "days": days}


def simulate_swing(prep: dict, names: dict, capital_jpy: float, risk_pct: float, fx: float, rule: dict,
                   start=None, max_pos: int = 5, allow_odd_lot: bool = True, cost_pct: float = 0.1,
                   return_open: bool = False):
    pats = None if rule["patterns"] == "すべて" else {rule["patterns"]}
    by_day: dict = {}
    for t, lst in prep["raw"].items():
        for s in lst:
            if pats and s["setup"] not in pats:
                continue
            if start is not None and s["date"] < start:
                continue
            if rule.get("avoid_earnings") and s["earn"]:
                continue
            if rule["filter"]:
                reg = prep["regime"].get("JP" if t.endswith(".T") else "US")
                if reg is None or not bool(reg.get(s["date"], False)):
                    continue
            by_day.setdefault(s["date"], []).append((t, s))
    pos_idx = {t: {d: k for k, d in enumerate(b["idx"])} for t, b in prep["bars"].items()}
    cost = cost_pct / 100
    positions, pending, trades = {}, {}, []
    for day in prep["days"]:
        if start is not None and day < start:
            continue
        # 1) 約定待ち・保有中の処理
        for t in list(pending):
            k = pos_idx[t].get(day)
            if k is None:
                continue
            b = prep["bars"][t]
            pdx = pending[t]
            o, h = b["o"][k], b["h"][k]
            fill = None
            if pdx["how"] == "open":
                fill = o if o <= pdx["entry"] * 1.02 else None
                if fill is None:
                    del pending[t]
                    continue
            elif h >= pdx["entry"]:
                fill = max(o, pdx["entry"])
            if fill is not None and fill > pdx["stop"] and len(positions) < max_pos:
                rate = 1.0 if t.endswith(".T") else fx
                lot = 1 if (allow_odd_lot or not t.endswith(".T")) else 100
                used = sum(x["qty"] * x["entry_px"] * x["rate"] for x in positions.values())
                qty = min(capital_jpy * risk_pct / 100 / ((fill - pdx["stop"]) * rate), (capital_jpy - used) / (fill * rate))
                qty = int(qty // lot * lot)
                if qty >= lot:
                    positions[t] = {**pdx, "entry_px": fill * (1 + cost), "qty": qty, "rate": rate, "d_in": day, "k_in": k}
                del pending[t]
            else:
                pdx["wait"] += 1
                if pdx["wait"] >= 3 or fill is not None:
                    pending.pop(t, None)
        for t in list(positions):
            k = pos_idx[t].get(day)
            if k is None:
                continue
            b = prep["bars"][t]
            ps = positions[t]
            o, h, l, c = b["o"][k], b["h"][k], b["l"][k], b["c"][k]
            ex = why = None
            if l <= ps["stop"]:
                ex, why = (min(o, ps["stop"]) if k > ps["k_in"] else ps["stop"]), "損切り"
            elif h >= ps["target"]:
                ex, why = (max(o, ps["target"]) if k > ps["k_in"] else ps["target"]), "利確"
            elif k - ps["k_in"] >= ps["hold"]:
                ex, why = c, "保有期限"
            if ex is not None:
                ex *= (1 - cost)
                trades.append({"銘柄": names.get(t, t), "ティッカー": t, "パターン": ps["setup"], "買い日": ps["d_in"],
                               "買値": ps["entry_px"], "損切り": ps["stop"],
                               "利確": ps["target"] if np.isfinite(ps["target"]) else np.nan,
                               "売り日": day, "売値": ex, "株数": ps["qty"], "決済理由": why,
                               "損益(円)": (ex - ps["entry_px"]) * ps["qty"] * ps["rate"],
                               "R": (ex - ps["entry_px"]) / (ps["entry_px"] - ps["stop"])})
                del positions[t]
        # 2) 今日のシグナル → 翌日以降に約定（質の高い順に、空き枠ぶんだけ）
        cands = sorted(by_day.get(day, []), key=lambda x: -x[1]["q"])
        for t, s in cands:
            if len(positions) + len(pending) >= max_pos:
                break
            if t in positions or t in pending:
                continue
            e = s["entry"]
            stop = s["stop"] if rule["stop"] == "標準" else e - float(rule["stop"]) * s["atr"]
            if not e > stop:
                continue
            target = np.inf if rule["target_r"] is None else e + rule["target_r"] * (e - stop)
            pending[t] = {"setup": s["setup"], "how": s["how"], "hold": s["hold"], "entry": e, "stop": stop,
                          "target": target, "wait": 0}
    tr = pd.DataFrame(trades)
    if len(tr):
        tr = tr.sort_values("買い日").reset_index(drop=True)
        tr["累積損益(円)"] = tr["損益(円)"].cumsum()
    if not return_open:
        return tr
    opens = []
    for t, ps in positions.items():
        b = prep["bars"][t]
        last = b["c"][-1]
        opens.append({"状態": "保有中", "銘柄": names.get(t, t), "ティッカー": t, "パターン": ps["setup"], "買い日": ps["d_in"],
                      "買値": ps["entry_px"], "損切り": ps["stop"], "現在値": last,
                      "含み損益(円)": (last - ps["entry_px"]) * ps["qty"] * ps["rate"], "株数": ps["qty"],
                      "残り日数": ps["hold"] - (len(b["idx"]) - 1 - ps["k_in"])})
    for t, pdx in pending.items():
        opens.append({"状態": "約定待ち", "銘柄": names.get(t, t), "ティッカー": t, "パターン": pdx["setup"], "買い日": pd.NaT,
                      "買値": pdx["entry"], "損切り": pdx["stop"], "現在値": prep["bars"][t]["c"][-1],
                      "含み損益(円)": 0.0, "株数": 0, "残り日数": None})
    return tr, pd.DataFrame(opens)


def research_swing(frames, names, index_frames, capital_jpy, risk_pct, fx, test_frac=0.4, min_trades=20,
                   earnings=None, **kw) -> dict:
    prep = prepare_swing(frames, index_frames, earnings)
    days = [d for d in prep["days"]]
    usable = days[200:]  # 指標の準備期間を除く
    split = usable[int(len(usable) * (1 - test_frac))]
    rows = []
    for ae, f, pat, stop, tgt in itertools.product(*SWING_GRID.values()):
        rule = {"avoid_earnings": ae, "filter": f, "patterns": pat, "stop": stop, "target_r": tgt}
        tr = simulate_swing(prep, names, capital_jpy, risk_pct, fx, rule, start=usable[0], **kw)
        if not len(tr):
            continue
        a, b = tr[tr["買い日"] < split], tr[tr["買い日"] >= split]
        rows.append({"ルール": swing_rule_label(rule), "_rule": rule,
                     "学習_回数": len(a), "学習_勝率%": (a["R"] > 0).mean() * 100 if len(a) else np.nan,
                     "学習_平均R": a["R"].mean() if len(a) else np.nan, "学習_損益": a["損益(円)"].sum(),
                     "検証_回数": len(b), "検証_勝率%": (b["R"] > 0).mean() * 100 if len(b) else np.nan,
                     "検証_平均R": b["R"].mean() if len(b) else np.nan, "検証_損益": b["損益(円)"].sum()})
    df = pd.DataFrame(rows)
    ok = df[df["学習_回数"] >= min_trades].sort_values("学習_平均R", ascending=False) if len(df) else df
    base = df[df["ルール"] == swing_rule_label(SWING_DEFAULT)]
    # 選び方（PDCAで改善）：1パターンに絞った設定は過去に合わせすぎて未来で崩れやすかったため、
    # 「全パターン」かつ学習期間に十分な回数（150回以上）がある設定の中から、学習期間の成績で選ぶ。
    robust = ok[(ok["_rule"].map(lambda r: r["patterns"]) == "すべて") & (ok["学習_回数"] >= 150)] if len(ok) else ok
    pick = robust if len(robust) else ok
    best = pick.iloc[0].to_dict() if len(pick) else None
    pair = None
    if best:  # 同じ設定で「決算回避」だけを切り替えた比較
        r2 = {**best["_rule"], "avoid_earnings": not best["_rule"].get("avoid_earnings")}
        m = df[df["ルール"] == swing_rule_label(r2)]
        pair = m.iloc[0].to_dict() if len(m) else None
    return {"table": ok, "best": best, "pair": pair,
            "base": base.iloc[0].to_dict() if len(base) else None,
            "train_from": usable[0], "split": split, "end": usable[-1],
            "n_train": sum(d < split for d in usable), "n_test": sum(d >= split for d in usable), "prep": prep}

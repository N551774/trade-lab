"""帳簿の計算（仕訳 → 元帳・試算表・損益計算書・貸借対照表）。UIに依存しない純粋ロジック。"""
from __future__ import annotations

from collections import defaultdict

from content import ACCOUNTS

CATS = ["資産", "負債", "純資産", "収益", "費用"]
DEBIT_NORMAL = {"資産", "費用"}  # 借方（左）が増える側の区分


def category(acct: str) -> str:
    return ACCOUNTS[acct]["cat"]


def side_totals(lines: list[dict]) -> tuple[int, int]:
    dr = sum(l["amount"] for l in lines if l["side"] == "借方")
    cr = sum(l["amount"] for l in lines if l["side"] == "貸方")
    return dr, cr


def normalize(lines: list[dict]) -> dict[str, dict[str, int]]:
    """仕訳行を {借方: {科目: 金額}, 貸方: {...}} にまとめる（行の順番・分け方の違いを吸収）。"""
    out: dict[str, dict[str, int]] = {"借方": defaultdict(int), "貸方": defaultdict(int)}
    for l in lines:
        if l["acct"] and l["amount"]:
            out[l["side"]][l["acct"]] += int(l["amount"])
    return {k: dict(v) for k, v in out.items()}


def is_same_entry(a: list[dict], b: list[dict]) -> bool:
    return normalize(a) == normalize(b)


def balances(entries: list[dict]) -> dict[str, int]:
    """科目ごとの残高（その科目の“増える側”をプラスとして返す）。"""
    bal: dict[str, int] = defaultdict(int)
    for e in entries:
        for l in e["lines"]:
            sign = 1 if (l["side"] == "借方") == (category(l["acct"]) in DEBIT_NORMAL) else -1
            bal[l["acct"]] += sign * int(l["amount"])
    return dict(bal)


def ledger(entries: list[dict], acct: str) -> list[dict]:
    """総勘定元帳（1科目分）。相手科目つき。"""
    rows, run = [], 0
    debit_normal = category(acct) in DEBIT_NORMAL
    for e in entries:
        mine = [l for l in e["lines"] if l["acct"] == acct]
        for l in mine:
            others = [o["acct"] for o in e["lines"] if o["side"] != l["side"]]
            partner = others[0] if len(others) == 1 else "諸口"
            dr = l["amount"] if l["side"] == "借方" else 0
            cr = l["amount"] if l["side"] == "貸方" else 0
            run += (dr - cr) if debit_normal else (cr - dr)
            rows.append({"日付": e.get("date", ""), "摘要": e.get("memo", ""), "相手科目": partner,
                         "借方": dr, "貸方": cr, "残高": run})
    return rows


def trial_balance(entries: list[dict]) -> list[dict]:
    """残高試算表。科目の並びは区分順。"""
    bal = balances(entries)
    rows = []
    for acct in sorted(bal, key=lambda a: (CATS.index(category(a)), list(ACCOUNTS).index(a))):
        v = bal[acct]
        if v == 0:
            continue
        debit_normal = category(acct) in DEBIT_NORMAL
        dr = v if (debit_normal and v > 0) or (not debit_normal and v < 0) else 0
        cr = abs(v) if not dr else 0
        rows.append({"区分": category(acct), "勘定科目": acct, "借方残高": abs(dr), "貸方残高": cr})
    return rows


def statements(entries: list[dict]) -> dict:
    bal = balances(entries)
    by = {c: {a: v for a, v in bal.items() if category(a) == c and v != 0} for c in CATS}
    revenue = sum(by["収益"].values())
    expense = sum(by["費用"].values())
    net = revenue - expense
    assets = sum(by["資産"].values())
    liab = sum(by["負債"].values())
    equity = sum(by["純資産"].values())
    return {"by": by, "revenue": revenue, "expense": expense, "net_income": net,
            "assets": assets, "liabilities": liab, "equity": equity,
            "balanced": assets == liab + equity + net}

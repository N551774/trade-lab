"""データの保存先

・ローカル（Macで動かすとき）：アプリのデータフォルダに CSV / JSON で保存
・Googleスプレッドシート（クラウドで動かすとき）：Streamlit の Secrets に
    sheet_url = "https://docs.google.com/spreadsheets/d/...."
    [gcp_service_account]  ← サービスアカウントの JSON の中身
  を設定すると、表ごとにシート（タブ）を作って保存する。

保存するもの：トレード記録 / 毎日の成績 / 採用ルール / マイ銘柄 など（どれも小さな表）
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pandas as pd

# クラウドの一時フォルダでも書き込めるよう、環境変数で場所を変えられる
DATA_DIR = Path(os.environ.get("TRADELAB_DATA", Path(__file__).parent))
KV_TABLE = "settings"
VERSION = 2  # 書き込みのやり直し・追記に対応


class LocalBackend:
    name = "このパソコン"
    persistent = True

    def __init__(self, folder: Path = DATA_DIR):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)

    def _p(self, table):
        return self.folder / f"{table}.csv"

    def read(self, table: str) -> pd.DataFrame:
        try:
            return pd.read_csv(self._p(table))
        except Exception:
            return pd.DataFrame()

    def write(self, table: str, df: pd.DataFrame):
        df.to_csv(self._p(table), index=False, encoding="utf-8")

    def append(self, table: str, df: pd.DataFrame):
        if len(df):
            p = self._p(table)
            df.to_csv(p, mode="a", header=not p.exists(), index=False, encoding="utf-8")


def _retry(fn, tries: int = 5):
    """Google の一時的なエラー（使いすぎ制限 429・サーバーエラー 5xx）は少し待ってやり直す"""
    import gspread
    for k in range(tries):
        try:
            return fn()
        except gspread.exceptions.APIError as e:
            code = getattr(getattr(e, "response", None), "status_code", 0) or 0
            if k == tries - 1 or not (code == 429 or code >= 500):
                raise
            time.sleep(min(30, 2 ** k * 2))


class SheetsBackend:
    name = "Googleスプレッドシート"
    persistent = True

    def __init__(self, sheet_url: str, sa_info: dict):
        import gspread
        from google.oauth2.service_account import Credentials
        creds = Credentials.from_service_account_info(
            sa_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        self.book = gspread.authorize(creds).open_by_url(sheet_url)
        self._cache: dict = {}

    def _ws(self, table):
        import gspread
        if table in getattr(self, "_ws_cache", {}):
            return self._ws_cache[table]
        self._ws_cache = getattr(self, "_ws_cache", {})
        try:
            ws = _retry(lambda: self.book.worksheet(table))
        except gspread.WorksheetNotFound:
            ws = _retry(lambda: self.book.add_worksheet(title=table, rows=200, cols=30))
        self._ws_cache[table] = ws
        return ws

    def read(self, table: str) -> pd.DataFrame:
        hit = self._cache.get(table)
        if hit and time.time() - hit[0] < 60:
            return hit[1].copy()
        ws = self._ws(table)
        vals = _retry(lambda: ws.get_all_values())
        df = pd.DataFrame(vals[1:], columns=vals[0]) if len(vals) >= 1 and vals[0] else pd.DataFrame()
        # 数値に戻せる列は数値に
        for c in df.columns:
            conv = pd.to_numeric(df[c].replace("", None), errors="coerce")
            if conv.notna().sum() == (df[c] != "").sum():
                df[c] = conv
        self._cache[table] = (time.time(), df)
        return df.copy()

    def write(self, table: str, df: pd.DataFrame):
        ws = self._ws(table)
        out = df.copy()
        for c in out.columns:
            if pd.api.types.is_datetime64_any_dtype(out[c]):
                out[c] = out[c].dt.strftime("%Y-%m-%d %H:%M:%S")
        out = out.astype(object).where(out.notna(), "")
        _retry(lambda: ws.clear())
        _retry(lambda: ws.update([list(map(str, out.columns))] + out.values.tolist(), value_input_option="RAW"))
        self._cache[table] = (time.time(), df.copy())

    def append(self, table: str, df: pd.DataFrame):
        if not len(df):
            return
        cur = self.read(table)
        if len(cur) and list(cur.columns) == list(map(str, df.columns)):
            # 列が同じなら、表を消さずに下へ書き足すだけ（書き込み回数が少なく、失敗しにくい）
            out = df.copy()
            for c in out.columns:
                if pd.api.types.is_datetime64_any_dtype(out[c]):
                    out[c] = out[c].dt.strftime("%Y-%m-%d %H:%M:%S")
            out = out.astype(object).where(out.notna(), "")
            ws = self._ws(table)
            _retry(lambda: ws.append_rows(out.values.tolist(), value_input_option="RAW"))
            self._cache.pop(table, None)
        else:
            self.write(table, pd.concat([cur, df], ignore_index=True) if len(cur) else df)


_backend = None


def backend():
    """Secrets にスプレッドシートの設定があればそれを、なければローカルを使う"""
    global _backend
    if _backend is not None:
        return _backend
    try:
        import streamlit as st
        sec = st.secrets
        if "sheet_url" in sec and ("gcp_service_account" in sec or "gcp_service_account_json" in sec):
            info = (json.loads(sec["gcp_service_account_json"]) if "gcp_service_account_json" in sec
                    else dict(sec["gcp_service_account"]))
            _backend = SheetsBackend(sec["sheet_url"], info)
            return _backend
    except Exception as e:  # 設定ミスなど → ローカルに切り替え、理由を残す
        LocalBackend.error = str(e)[:200]
    _backend = LocalBackend()
    return _backend


# ---- 小さな設定値（キーと値） -----------------------------------------------
def get(key: str, default=None):
    df = backend().read(KV_TABLE)
    if not len(df) or "key" not in df.columns:
        return default
    m = df[df["key"] == key]
    if not len(m):
        return default
    v = m.iloc[-1]["value"]
    if not isinstance(v, str):
        return v
    try:
        return json.loads(v)
    except Exception:
        return default


def put(key: str, value):
    b = backend()
    df = b.read(KV_TABLE)
    if not len(df) or "key" not in df.columns:
        df = pd.DataFrame(columns=["key", "value"])
    df = df[df["key"] != key]
    if value is not None:
        df = pd.concat([df, pd.DataFrame([{"key": key, "value": json.dumps(value, ensure_ascii=False)}])],
                       ignore_index=True)
    b.write(KV_TABLE, df)

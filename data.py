"""価格データの取得（Yahoo!Finance / CSV / デモデータ）"""
from __future__ import annotations

import hashlib
import io
import re

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:  # pragma: no cover
    yf = None

# ---------------------------------------------------------------------------
# 銘柄プリセット（Yahoo!Finance のティッカー表記）
# ---------------------------------------------------------------------------
PRESETS: dict[str, dict[str, str]] = {
    "日本株": {
        "トヨタ自動車": "7203.T",
        "ソニーグループ": "6758.T",
        "三菱UFJ FG": "8306.T",
        "ソフトバンクG": "9984.T",
        "東京エレクトロン": "8035.T",
        "任天堂": "7974.T",
        "キーエンス": "6861.T",
        "ファーストリテイリング": "9983.T",
        "レーザーテック": "6920.T",
        "アドバンテスト": "6857.T",
        "日立製作所": "6501.T",
        "三菱重工業": "7011.T",
        "三菱商事": "8058.T",
        "三井住友FG": "8316.T",
        "みずほFG": "8411.T",
        "ルネサス": "6723.T",
        "日本製鉄": "5401.T",
        "日本郵船": "9101.T",
        "NTT": "9432.T",
        "日産自動車": "7201.T",
        "日経平均（指数）": "^N225",
    },
    "米国株": {
        "Apple": "AAPL",
        "Microsoft": "MSFT",
        "NVIDIA": "NVDA",
        "Tesla": "TSLA",
        "Amazon": "AMZN",
        "Meta": "META",
        "Alphabet": "GOOGL",
        "AMD": "AMD",
        "Broadcom": "AVGO",
        "Palantir": "PLTR",
        "Netflix": "NFLX",
        "S&P500（指数）": "^GSPC",
        "NASDAQ総合（指数）": "^IXIC",
    },
    "ETF": {
        "SPDR S&P500 (SPY)": "SPY",
        "Invesco QQQ": "QQQ",
        "ProShares TQQQ": "TQQQ",
        "Direxion SOXL": "SOXL",
        "Vanguard VOO": "VOO",
        "TOPIX連動 (1306)": "1306.T",
        "日経225連動 (1321)": "1321.T",
        "日経レバレッジ (1570)": "1570.T",
        "MAXIS 米国株S&P500 (2558)": "2558.T",
    },
    "原油": {
        "WTI原油先物": "CL=F",
        "ブレント原油先物": "BZ=F",
        "United States Oil (USO)": "USO",
        "WTI原油ETF (1671)": "1671.T",
        "NF 原油ETF (1699)": "1699.T",
    },
    "金・貴金属": {
        "金先物": "GC=F",
        "SPDR Gold (GLD)": "GLD",
        "iShares Gold (IAU)": "IAU",
        "純金上場信託 (1540)": "1540.T",
        "SPDRゴールド (1326)": "1326.T",
        "銀先物": "SI=F",
    },
    "為替": {
        "米ドル/円": "JPY=X",
        "ユーロ/円": "EURJPY=X",
    },
}


# ---------------------------------------------------------------------------
# 拡大した対象（約220銘柄）：売買が多く短期売買しやすい大型株・主要ETF
# ---------------------------------------------------------------------------
WIDE_EXTRA: dict[str, dict[str, str]] = {
    "日本株": {
        "伊藤忠商事": "8001.T", "三井物産": "8031.T", "住友商事": "8053.T", "丸紅": "8002.T", "豊田通商": "8015.T",
        "JT": "2914.T", "信越化学": "4063.T", "武田薬品": "4502.T", "アステラス製薬": "4503.T", "中外製薬": "4519.T",
        "第一三共": "4568.T", "リクルートHD": "6098.T", "ダイキン工業": "6367.T", "三菱電機": "6503.T", "ニデック": "6594.T",
        "富士通": "6702.T", "パナソニックHD": "6752.T", "TDK": "6762.T", "デンソー": "6902.T", "ファナック": "6954.T",
        "京セラ": "6971.T", "村田製作所": "6981.T", "ホンダ": "7267.T", "スズキ": "7269.T", "SUBARU": "7270.T",
        "HOYA": "7741.T", "キヤノン": "7751.T", "バンダイナムコ": "7832.T", "オリックス": "8591.T", "野村HD": "8604.T",
        "SOMPO HD": "8630.T", "MS&AD": "8725.T", "東京海上HD": "8766.T", "三井不動産": "8801.T", "三菱地所": "8802.T",
        "JR東日本": "9020.T", "JR東海": "9022.T", "商船三井": "9104.T", "川崎汽船": "9107.T", "KDDI": "9433.T",
        "ソフトバンク": "9434.T", "コナミG": "9766.T", "ニトリHD": "9843.T", "オリエンタルランド": "4661.T",
        "セブン&アイ": "3382.T", "味の素": "2802.T", "花王": "4452.T", "富士フイルム": "4901.T", "ブリヂストン": "5108.T",
        "住友電工": "5802.T", "ディスコ": "6146.T", "SMC": "6273.T", "コマツ": "6301.T", "クボタ": "6326.T",
        "オリンパス": "7733.T", "川崎重工業": "7012.T", "IHI": "7013.T", "第一生命HD": "8750.T", "エムスリー": "2413.T",
        "メルカリ": "4385.T", "楽天G": "4755.T", "日本郵政": "6178.T", "JAL": "9201.T", "ANA HD": "9202.T",
        "INPEX": "1605.T", "ENEOS HD": "5020.T", "住友金属鉱山": "5713.T", "旭化成": "3407.T", "資生堂": "4911.T",
    },
    "米国株": {
        "JPMorgan": "JPM", "Visa": "V", "Mastercard": "MA", "UnitedHealth": "UNH", "Eli Lilly": "LLY", "J&J": "JNJ",
        "P&G": "PG", "Exxon Mobil": "XOM", "Chevron": "CVX", "Home Depot": "HD", "Costco": "COST", "Walmart": "WMT",
        "Coca-Cola": "KO", "PepsiCo": "PEP", "Merck": "MRK", "AbbVie": "ABBV", "Bank of America": "BAC",
        "Wells Fargo": "WFC", "Goldman Sachs": "GS", "Morgan Stanley": "MS", "Citigroup": "C", "Salesforce": "CRM",
        "Oracle": "ORCL", "Adobe": "ADBE", "Cisco": "CSCO", "Intel": "INTC", "Qualcomm": "QCOM", "Texas Instruments": "TXN",
        "IBM": "IBM", "Applied Materials": "AMAT", "Micron": "MU", "Lam Research": "LRCX", "Disney": "DIS",
        "McDonald's": "MCD", "Nike": "NKE", "Starbucks": "SBUX", "Boeing": "BA", "Caterpillar": "CAT", "Deere": "DE",
        "GE Aerospace": "GE", "Honeywell": "HON", "Lockheed Martin": "LMT", "RTX": "RTX", "UPS": "UPS",
        "Union Pacific": "UNP", "AT&T": "T", "Verizon": "VZ", "Comcast": "CMCSA", "Thermo Fisher": "TMO",
        "Abbott": "ABT", "Danaher": "DHR", "Pfizer": "PFE", "Amgen": "AMGN", "Gilead": "GILD", "Intuitive Surgical": "ISRG",
        "Booking": "BKNG", "Uber": "UBER", "PayPal": "PYPL", "NextEra Energy": "NEE", "Duke Energy": "DUK",
        "Southern Co": "SO", "Linde": "LIN", "Berkshire B": "BRK-B", "American Express": "AXP", "BlackRock": "BLK",
        "Schwab": "SCHW", "Lowe's": "LOW", "Target": "TGT", "Medtronic": "MDT", "Bristol-Myers": "BMY", "CVS Health": "CVS",
        "ConocoPhillips": "COP", "S&P Global": "SPGI", "ServiceNow": "NOW", "Intuit": "INTU", "Palo Alto Networks": "PANW",
    },
    "ETF": {
        "SPDR ダウ (DIA)": "DIA", "iShares ラッセル2000 (IWM)": "IWM", "VanEck 半導体 (SMH)": "SMH",
        "エネルギー (XLE)": "XLE", "金融 (XLF)": "XLF", "ヘルスケア (XLV)": "XLV", "公益 (XLU)": "XLU",
        "テクノロジー (XLK)": "XLK", "資本財 (XLI)": "XLI", "生活必需品 (XLP)": "XLP", "一般消費財 (XLY)": "XLY",
        "素材 (XLB)": "XLB", "不動産 (XLRE)": "XLRE", "通信 (XLC)": "XLC", "米国債20年超 (TLT)": "TLT",
        "米国債7-10年 (IEF)": "IEF", "新興国株 (EEM)": "EEM", "日本株 (EWJ)": "EWJ",
        "日経高配当50 (1489)": "1489.T", "東証銀行業 (1615)": "1615.T", "MAXIS NASDAQ100 (2631)": "2631.T",
        "iShares S&P500 (1655)": "1655.T",
    },
    "金・貴金属": {"金鉱株 (GDX)": "GDX", "iShares 銀 (SLV)": "SLV"},
}
WIDE = False  # True のとき universe() が拡大した対象を返す（アプリの設定で切り替え）

# 直接は売買できない（指数・先物）ものと、代わりに使える ETF
PROXY = {
    "^N225": "1321.T（日経225連動）/ 1570.T（レバ）", "^GSPC": "SPY / VOO / 2558.T", "^IXIC": "QQQ",
    "CL=F": "1671.T（WTI原油）/ USO", "BZ=F": "1671.T / USO", "GC=F": "1540.T（純金）/ GLD",
    "SI=F": "1542.T（純銀）/ SLV",
}


def is_tradable(ticker: str) -> bool:
    return ticker not in PROXY and not ticker.endswith("=X")


def lot_of(ticker: str) -> int:
    """売買単位（日本株・国内ETF=100株 ※一部ETFは1口/10口）"""
    if ticker in ("1540.T", "1326.T", "1306.T", "1321.T", "2558.T", "1671.T", "1699.T", "1570.T",
                  "1489.T", "2631.T", "1655.T"):
        return 1
    if ticker == "1615.T":
        return 10
    return 100 if ticker.endswith(".T") else 1


def universe(categories, wide: bool | None = None) -> list[tuple[str, str, str]]:
    """(カテゴリ, 名前, ティッカー)。wide=True（または WIDE）なら拡大した対象も含める"""
    wide = WIDE if wide is None else wide
    out = [(c, n, t) for c in categories for n, t in PRESETS[c].items()]
    if wide:
        have = {t for _, _, t in out}
        out += [(c, n, t) for c in categories for n, t in WIDE_EXTRA.get(c, {}).items() if t not in have]
    return out


# 足の種類と、Yahoo!Finance で取得可能な期間
INTERVALS: dict[str, dict] = {
    "1分足": {"code": "1m", "periods": ["1d", "5d", "7d"], "default": "1d", "bars_per_year": 252 * 390},
    "5分足": {"code": "5m", "periods": ["1d", "5d", "1mo", "60d"], "default": "5d", "bars_per_year": 252 * 78},
    "15分足": {"code": "15m", "periods": ["5d", "1mo", "60d"], "default": "1mo", "bars_per_year": 252 * 26},
    "1時間足": {"code": "60m", "periods": ["1mo", "3mo", "6mo", "1y", "2y"], "default": "3mo", "bars_per_year": 252 * 7},
    "日足": {"code": "1d", "periods": ["3mo", "6mo", "1y", "2y", "5y", "10y"], "default": "1y", "bars_per_year": 252},
    "週足": {"code": "1wk", "periods": ["1y", "2y", "5y", "10y"], "default": "5y", "bars_per_year": 52},
}

PERIOD_LABELS = {
    "1d": "1日", "5d": "5日", "7d": "7日", "1mo": "1ヶ月", "60d": "60日", "3mo": "3ヶ月",
    "6mo": "6ヶ月", "1y": "1年", "2y": "2年", "5y": "5年", "10y": "10年",
}


def normalize_ticker(raw: str) -> str:
    """'7203' → '7203.T' のように日本株コードを補完する。"""
    t = raw.strip().upper()
    if re.fullmatch(r"\d{4}|\d{3}[A-Z]", t):
        return t + ".T"
    return t


def name_of(ticker: str) -> str:
    for group in list(PRESETS.values()) + list(WIDE_EXTRA.values()):
        for name, t in group.items():
            if t == ticker:
                return name
    return ticker


def currency_of(ticker: str) -> str:
    if ticker.endswith(".T") or ticker in ("^N225", "JPY=X", "EURJPY=X"):
        return "¥"
    return "$"


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    rename = {c: c.capitalize() for c in df.columns}
    df = df.rename(columns=rename)
    keep = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    df = df[keep].copy()
    if "Volume" not in df.columns:
        df["Volume"] = 0
    idx = pd.to_datetime(df.index)
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)
    df.index = idx
    df.index.name = "Date"
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df.astype(float)


# まとめて取得した結果（サーバー全体で共有。fetch_yahoo が先に見る）
_BULK: dict = {}
BULK_TTL = {"1d": 900, "1wk": 3600}


def fetch_many(tickers: list[str], period: str, interval: str, chunk: int = 60) -> dict[str, pd.DataFrame]:
    """多数の銘柄を yf.download でまとめて取得（1銘柄ずつより大幅に速い）"""
    import time as _t
    out = {}
    if yf is None:
        return out
    for i in range(0, len(tickers), chunk):
        part = tickers[i:i + chunk]
        try:
            raw = yf.download(part, period=period, interval=interval, group_by="ticker", auto_adjust=False,
                              threads=True, progress=False, prepost=False)
        except Exception:
            continue
        for t in part:
            try:
                sub = raw[t] if isinstance(raw.columns, pd.MultiIndex) else raw
                df = _clean(sub.copy())
                if len(df):
                    out[t] = df
                    _BULK[(t, period, interval)] = (_t.time(), df)
            except Exception:
                pass
    return out


def fetch_yahoo(ticker: str, period: str, interval: str) -> pd.DataFrame:
    import time as _t
    hit = _BULK.get((ticker, period, interval))
    if hit and _t.time() - hit[0] < BULK_TTL.get(interval, 120):
        return hit[1].copy()
    if yf is None:
        raise RuntimeError("yfinance がインストールされていません")
    df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=False, prepost=False)
    if df is None or df.empty:
        raise RuntimeError(f"{ticker} のデータが取得できませんでした（ティッカー・期間を確認してください）")
    return _clean(df)


def fetch_quote(ticker: str) -> dict | None:
    """直近の値動き（前日比）を取得。失敗時は None。"""
    try:
        df = fetch_yahoo(ticker, "5d", "1d")
        if len(df) < 2:
            return None
        last, prev = df["Close"].iloc[-1], df["Close"].iloc[-2]
        return {"price": last, "change": last - prev, "pct": (last / prev - 1) * 100}
    except Exception:
        return None


def demo_data(ticker: str, interval_code: str = "1d", n: int = 400) -> pd.DataFrame:
    """動作確認用の架空データ（ティッカーごとに同じ値動きを再現）。"""
    seed = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    freq = {"1m": "min", "5m": "5min", "15m": "15min", "60m": "h", "1d": "B", "1wk": "W-FRI"}.get(interval_code, "B")
    idx = pd.date_range(end=pd.Timestamp.today().normalize(), periods=n, freq=freq)
    start = 100 + (seed % 5000)
    vol = 0.02 if interval_code in ("1d", "1wk") else 0.004
    # トレンドが切り替わる値動き
    drift = np.repeat(rng.normal(0, vol / 4, n // 40 + 1), 40)[:n]
    rets = rng.normal(0, vol, n) + drift
    close = start * np.exp(np.cumsum(rets))
    open_ = np.r_[close[0], close[:-1]] * (1 + rng.normal(0, vol / 4, n))
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, vol / 2, n)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, vol / 2, n)))
    volume = rng.lognormal(13, 0.5, n) * (1 + 3 * np.abs(rets) / vol)
    df = pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume.round()}, index=idx)
    df.index.name = "Date"
    return df


def load_csv(file) -> pd.DataFrame:
    """日付・始値・高値・安値・終値・出来高 の CSV を読み込む（日本語/英語の列名に対応）。"""
    raw = file.read() if hasattr(file, "read") else open(file, "rb").read()
    for enc in ("utf-8-sig", "cp932"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    df = pd.read_csv(io.StringIO(text))
    jp = {"日付": "Date", "日時": "Date", "始値": "Open", "高値": "High", "安値": "Low",
          "終値": "Close", "出来高": "Volume", "調整後終値": "Adj Close"}
    df = df.rename(columns={c: jp.get(c.strip(), c.strip()) for c in df.columns})
    date_col = next((c for c in df.columns if c.lower() in ("date", "datetime", "time")), df.columns[0])
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.set_index(date_col)
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ""), errors="coerce")
    return _clean(df)

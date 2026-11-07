"""チャート描画"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import plotly.io as pio

UP, DOWN = "#ff5a6a", "#4c8dff"  # 陽線=赤 / 陰線=青（日本式）
ENTRY_C, STOP_C, TARGET_C = "#fbbf24", "#4c8dff", "#ff5a6a"

# アプリ共通のダークテーマ（背景は透明にしてカードになじませる）
_t = go.layout.Template(pio.templates["plotly_dark"])
_t.layout.update(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, Noto Sans JP, sans-serif", color="#aab2c5", size=12),
    colorway=["#8b5cf6", "#22d3ee", "#fbbf24", "#34d399", "#ff5a6a", "#4c8dff", "#f472b6"],
    xaxis=dict(gridcolor="rgba(255,255,255,.05)", zerolinecolor="rgba(255,255,255,.08)", linecolor="rgba(255,255,255,.1)"),
    yaxis=dict(gridcolor="rgba(255,255,255,.05)", zerolinecolor="rgba(255,255,255,.08)", linecolor="rgba(255,255,255,.1)", side="right"),
    hoverlabel=dict(bgcolor="#121624", bordercolor="#2a3150", font=dict(color="#e9ecf5")),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
)
pio.templates["tradelab"] = _t
pio.templates.default = "tradelab"


def _x(d, intraday):
    return d.index.strftime("%m/%d %H:%M") if intraday else d.index


def _axes(fig, intraday, daily=True):
    if intraday:
        fig.update_xaxes(type="category", nticks=8)
    elif daily:
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])


def plan_chart(df: pd.DataFrame, plan, intraday: bool, bars: int = 90, height: int = 340):
    """ローソク足＋買い・損切り・利確ライン"""
    d = df.tail(bars)
    x = _x(d, intraday)
    fig = go.Figure(go.Candlestick(x=x, open=d["Open"], high=d["High"], low=d["Low"], close=d["Close"],
                                   increasing=dict(line_color=UP, fillcolor=UP),
                                   decreasing=dict(line_color=DOWN, fillcolor=DOWN), name="価格", showlegend=False))
    if not intraday:
        for n, col in ((20, "#17c964"), (50, "#9353d3")):
            fig.add_trace(go.Scatter(x=x, y=df["Close"].rolling(n).mean().tail(bars), name=f"{n}日線",
                                     line=dict(width=1.2, color=col)))
    else:
        from indicators import vwap
        fig.add_trace(go.Scatter(x=x, y=vwap(df).tail(bars), name="VWAP", line=dict(width=1.3, color="#06b7db")))
    for y, col, label in ((plan.target, TARGET_C, "利確"), (plan.entry, ENTRY_C, "買い"), (plan.stop, STOP_C, "損切り")):
        fig.add_hline(y=y, line=dict(color=col, width=2, dash="dash"),
                      annotation_text=f"{label} {y:,.2f}", annotation_position="top right",
                      annotation_font=dict(color=col, size=12))
    lo = min(d["Low"].min(), plan.stop, plan.target) * 0.99
    hi = max(d["High"].max(), plan.stop, plan.target) * 1.01
    fig.update_yaxes(range=[lo, hi])
    fig.update_layout(height=height, margin=dict(l=5, r=5, t=30, b=5), xaxis_rangeslider_visible=False,
                      legend=dict(orientation="h", y=1.1, x=0), hovermode="x unified")
    _axes(fig, intraday)
    return fig


def price_chart(d: pd.DataFrame, p: dict, overlays: list[str], lower: list[str], markers: pd.DataFrame | None,
                intraday: bool, interval_code: str, height=760):
    rows = 2 + len(lower)
    heights = [0.55, 0.12] + [0.33 / max(len(lower), 1)] * len(lower)
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=heights[:rows])
    x = _x(d, intraday)
    fig.add_trace(go.Candlestick(x=x, open=d["Open"], high=d["High"], low=d["Low"], close=d["Close"], name="価格",
                                 increasing=dict(line_color=UP, fillcolor=UP),
                                 decreasing=dict(line_color=DOWN, fillcolor=DOWN)), 1, 1)
    ma_colors = {"MA_S": "#fbbf24", "MA_M": "#22d3ee", "MA_L": "#8b5cf6"}
    labels = {"MA_S": f"MA{p['ma_short']}", "MA_M": f"MA{p['ma_mid']}", "MA_L": f"MA{p['ma_long']}"}
    if "移動平均" in overlays:
        for k in ("MA_S", "MA_M", "MA_L"):
            fig.add_trace(go.Scatter(x=x, y=d[k], name=labels[k], line=dict(width=1.3, color=ma_colors[k])), 1, 1)
    if "ボリンジャー" in overlays:
        for k in ("BB_U", "BB_L"):
            fig.add_trace(go.Scatter(x=x, y=d[k], name=k.replace("BB_", "BB "), line=dict(width=1, color="#889", dash="dot")), 1, 1)
    if "VWAP" in overlays and "VWAP" in d:
        fig.add_trace(go.Scatter(x=x, y=d["VWAP"], name="VWAP", line=dict(width=1.5, color="#06b7db")), 1, 1)
    if markers is not None:
        b, s = markers["buy"].to_numpy(), markers["sell"].to_numpy()
        fig.add_trace(go.Scatter(x=np.asarray(x)[b], y=d["Low"][b] * 0.995, mode="markers", name="買いシグナル",
                                 marker=dict(symbol="triangle-up", size=11, color=UP, line=dict(width=1, color="white"))), 1, 1)
        fig.add_trace(go.Scatter(x=np.asarray(x)[s], y=d["High"][s] * 1.005, mode="markers", name="売りシグナル",
                                 marker=dict(symbol="triangle-down", size=11, color=DOWN, line=dict(width=1, color="white"))), 1, 1)
    colors = np.where(d["Close"] >= d["Open"], UP, DOWN)
    fig.add_trace(go.Bar(x=x, y=d["Volume"], name="出来高", marker_color=colors, opacity=0.6, showlegend=False), 2, 1)
    fig.add_trace(go.Scatter(x=x, y=d["VOL_MA"], name="出来高MA20", line=dict(width=1, color="#999"), showlegend=False), 2, 1)
    r = 3
    for name in lower:
        if name == "RSI":
            fig.add_trace(go.Scatter(x=x, y=d["RSI"], name="RSI", line=dict(color="#f5a524", width=1.4), showlegend=False), r, 1)
            for lv in (30, 70):
                fig.add_hline(y=lv, line=dict(color="#888", dash="dot", width=1), row=r, col=1)
            fig.update_yaxes(range=[0, 100], row=r, col=1)
        elif name == "MACD":
            fig.add_trace(go.Bar(x=x, y=d["MACD_HIST"], name="ヒストグラム", showlegend=False,
                                 marker_color=np.where(d["MACD_HIST"] >= 0, UP, DOWN), opacity=0.6), r, 1)
            fig.add_trace(go.Scatter(x=x, y=d["MACD"], name="MACD", line=dict(color="#06b7db", width=1.3), showlegend=False), r, 1)
            fig.add_trace(go.Scatter(x=x, y=d["MACD_SIG"], name="シグナル", line=dict(color="#f5a524", width=1.3), showlegend=False), r, 1)
        elif name == "ストキャスティクス":
            fig.add_trace(go.Scatter(x=x, y=d["STO_K"], name="%K", line=dict(color="#06b7db", width=1.3), showlegend=False), r, 1)
            fig.add_trace(go.Scatter(x=x, y=d["STO_D"], name="%D", line=dict(color="#f5a524", width=1.3), showlegend=False), r, 1)
            for lv in (20, 80):
                fig.add_hline(y=lv, line=dict(color="#888", dash="dot", width=1), row=r, col=1)
        fig.update_yaxes(title_text=name, row=r, col=1)
        r += 1
    fig.update_yaxes(title_text="出来高", row=2, col=1)
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), xaxis_rangeslider_visible=False,
                      legend=dict(orientation="h", y=1.03, x=0), hovermode="x unified", dragmode="pan")
    _axes(fig, intraday, interval_code == "1d")
    return fig

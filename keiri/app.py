"""経理ラボ『バランスシート』— Streamlit でスマホゲーム版を表示する。

起動:  streamlit run keiri/app.py
本体は keiri/web/balance.html（keiri/web/build.py で生成）。前の学習アプリ版は keiri/web/index.html。
旧版（表形式の学習ツール）は keiri/classic.py。
"""
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="経理ラボ", page_icon="📒", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""<style>
header[data-testid="stHeader"], footer, #MainMenu {display:none !important}
.block-container {padding:0 !important; max-width:520px !important}
.stApp {background:#0E1117}
iframe {display:block; border:0}
</style>""", unsafe_allow_html=True)

body = (Path(__file__).parent / "web" / "balance.html").read_text(encoding="utf-8")
doc = ('<!doctype html><html lang="ja"><head><meta charset="utf-8">'
       '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><style>html,body{height:100%;margin:0}</style></head>'
       f'<body>{body}</body></html>')
components.html(doc, height=860, scrolling=True)

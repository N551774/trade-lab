"""ミラペア（試作品）を Streamlit で表示する。

起動:  streamlit run mirapair/app.py
本体は mirapair/index.html（そのままブラウザで開いても動く）。
"""
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="ミラペア", page_icon="💞", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""<style>
header[data-testid="stHeader"], footer, #MainMenu {display:none !important}
.block-container {padding:0 !important; max-width:520px !important}
iframe {display:block; border:0}
</style>""", unsafe_allow_html=True)

html = (Path(__file__).parent / "index.html").read_text(encoding="utf-8")
components.html(html, height=860, scrolling=True)

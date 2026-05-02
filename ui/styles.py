import streamlit as st

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;500;600&display=swap');

.stApp {
    background: linear-gradient(150deg, #0b1437 0%, #0f2255 45%, #0c2f52 75%, #091e3a 100%);
    background-attachment: fixed;
}
html, body, [data-testid="stAppViewContainer"], .stMarkdown p, div {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    font-family: 'Playfair Display', Georgia, serif !important;
}
section[data-testid="stSidebar"] {
    background: rgba(8, 16, 50, 0.96) !important;
    border-right: 1px solid rgba(96, 165, 250, 0.18);
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
    border: none; border-radius: 8px;
    font-weight: 600; letter-spacing: 0.04em;
    box-shadow: 0 0 18px rgba(37,99,235,0.40);
    transition: all 0.15s ease;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 24px rgba(37,99,235,0.55);
}
.stButton > button[kind="secondary"] { border-radius: 8px; }
[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255,255,255,0.035) !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    border-radius: 14px !important;
    backdrop-filter: blur(6px);
}
"""


def inject_css() -> None:
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)

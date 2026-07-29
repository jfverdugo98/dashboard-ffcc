import streamlit as st

import fx
from cashflow import render_cashflow
from balance import render_balance

st.set_page_config(page_title="Dashboard Financiero", layout="wide", page_icon="⚡")

# ---------- Estilo Neon/Tech ----------
st.markdown("""
    <style>
    :root {
        --neon-blue: #00d4ff;
        --neon-blue-dim: #0080ff;
        --neon-magenta: #ff00aa;
        --bg-deep: #0a0e17;
        --bg-panel: #10141f;
    }
    .stApp {
        background: radial-gradient(circle at 20% 0%, #0d1a2b 0%, var(--bg-deep) 45%);
    }
    h1, h2, h3 {
        color: var(--neon-blue) !important;
        text-shadow: 0 0 12px rgba(0, 212, 255, 0.35);
    }
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(0,212,255,0.08), rgba(255,0,170,0.04));
        border: 1px solid rgba(0, 212, 255, 0.25);
        border-radius: 14px;
        padding: 14px 16px;
        box-shadow: 0 0 18px rgba(0, 212, 255, 0.08);
    }
    [data-testid="stMetricValue"] {
        color: var(--neon-blue);
        font-family: 'SF Mono', 'Courier New', monospace;
        font-size: 1.5rem;
    }
    [data-testid="stMetricLabel"] {
        color: #9fd8ff;
    }
    .stApp [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 14px;
    }
    div[data-testid="column"]:first-of-type {
        border-right: 1px solid rgba(0, 212, 255, 0.25);
        padding-right: 1.5rem;
    }
    .stButton button {
        border: 1px solid var(--neon-blue-dim);
        color: var(--neon-blue);
        background: transparent;
    }
    .stButton button:hover {
        border-color: var(--neon-magenta);
        color: var(--neon-magenta);
    }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ Dashboard Financiero")

# ---------- Tasas en tiempo real (compartidas por ambas columnas) ----------
tasa_cop_auto, tasa_clp_auto, precio_btc_auto = fx.tickers()

st.sidebar.header("⚙️ Tasas (automáticas, editables)")
tasa_cop = st.sidebar.number_input("Tasa USD/COP", value=float(tasa_cop_auto))
tasa_clp = st.sidebar.number_input("Tasa USD/CLP", value=float(tasa_clp_auto))
precio_btc = st.sidebar.number_input("Precio BTC/USD", value=float(precio_btc_auto))

col_ffcc, col_balance = st.columns(2)

with col_ffcc:
    render_cashflow(tasa_clp)

with col_balance:
    render_balance(tasa_cop, tasa_clp, precio_btc)

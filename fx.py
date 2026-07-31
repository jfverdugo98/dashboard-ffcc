"""Tasas de cambio y precio de BTC en tiempo real.

Reutilizado tal cual desde dash.py (versión ya probada por el usuario).
"""
import streamlit as st
import yfinance as yf
from datetime import date, timedelta


def tickers():
    try:
        data = yf.Tickers("COP=X CLP=X BTC-USD")
        copusd = data.tickers["COP=X"].history(period="1d")["Close"].iloc[-1]
        clpusd = data.tickers["CLP=X"].history(period="1d")["Close"].iloc[-1]
        btcusd = data.tickers["BTC-USD"].history(period="1d")["Close"].iloc[-1]
        return copusd, clpusd, btcusd
    except Exception:
        # Valores por defecto en caso de fallo de internet
        return 3350, 930, 63000


@st.cache_data(ttl=3600, show_spinner=False)
def clp_history(start: date, end: date):
    """Devuelve {fecha: close USD/CLP} para el rango, vía yfinance CLP=X."""
    data = yf.download("CLP=X", start=start, end=end + timedelta(days=1),
                        progress=False)
    if data.empty:
        return {}
    close = data["Close"]
    if hasattr(close, "columns"):
        close = close.iloc[:, 0]
    return {ts.date(): float(v) for ts, v in close.items()}


def rate_on(history: dict, d: date, fallback: float):
    """Close del día d, o el día hábil anterior más cercano disponible."""
    if d in history:
        return history[d]
    anteriores = sorted(k for k in history if k <= d)
    if anteriores:
        return history[anteriores[-1]]
    return fallback

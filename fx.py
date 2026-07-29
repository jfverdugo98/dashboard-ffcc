"""Tasas de cambio y precio de BTC en tiempo real.

Reutilizado tal cual desde dash.py (versión ya probada por el usuario).
"""
import yfinance as yf


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

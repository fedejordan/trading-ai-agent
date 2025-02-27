import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine

# Lista de tickers (Ejemplo con 3, puedes agregar más)
tickers = ["GGAL", "YPF", "MELI"]  # Acciones argentinas y CEDEARs

# Configurar base de datos (PostgreSQL)
DB_URL = "postgresql://postgres:@localhost:5432/stocks_db"
engine = create_engine(DB_URL)

def download_stock_data(ticker, start="2025-01-01", end="2025-02-26"):
    """Descarga datos históricos de un ticker."""
    stock = yf.download(ticker, start=start, end=end)
    
    if stock.empty:
        print(f"No se encontraron datos para {ticker}")
        return None
    
    print("Columnas en el DataFrame antes de procesar:", stock.columns)

    # Si el DataFrame tiene MultiIndex, eliminamos el segundo nivel
    if isinstance(stock.columns, pd.MultiIndex):
        stock.columns = stock.columns.droplevel(1)

    print("Columnas en el DataFrame después de procesar:", stock.columns)

    # Verificar si 'Close' está presente
    if "Close" not in stock.columns:
        print(f"Error: La columna 'Close' no está en el DataFrame para {ticker}")
        print(f"Columnas disponibles: {stock.columns}")
        return None

    # Verificar si hay valores NaN en 'Close'
    if stock["Close"].isna().any():
        print(f"Advertencia: Hay valores NaN en 'Close' para {ticker}")
        stock["Close"].fillna(method="ffill", inplace=True)
    
    stock["close"] = stock["Close"]
    stock.drop(columns=["Close"], inplace=True)


    # Calcular indicadores técnicos
    stock["ema_50"] = ta.ema(stock["close"], length=50)
    stock["rsi_14"] = ta.rsi(stock["close"], length=14)

    # Verificar si MACD devuelve datos válidos
    macd_df = ta.macd(stock["close"])
    if macd_df is None or macd_df.empty:
        print(f"Advertencia: No se pudo calcular MACD para {ticker}")
        return stock  # Devuelve sin MACD

    stock["macd"] = macd_df['MACD_12_26_9']
    stock["macd_signal"] = macd_df['MACDs_12_26_9']

    stock.reset_index(inplace=True)
    stock["ticker"] = ticker  # Agregar el ticker como columna


    stock["date"] = stock["Date"]
    stock.drop(columns=["Date"], inplace=True)

    stock["high"] = stock["High"]
    stock.drop(columns=["High"], inplace=True)
    stock["low"] = stock["Low"]
    stock.drop(columns=["Low"], inplace=True)
    stock["volume"] = stock["Volume"]
    stock.drop(columns=["Volume"], inplace=True)
    stock["open"] = stock["Open"]
    stock.drop(columns=["Open"], inplace=True)

    return stock


# Descargar y guardar datos para cada ticker
dataframes = []
for ticker in tickers:
    df = download_stock_data(ticker)
    if df is not None:
        dataframes.append(df)
        df.to_sql("stock_prices", engine, if_exists="append", index=False)
        print("Datos guardados en stock_prices")

# Guardar en CSV como alternativa
df_combined = pd.concat(dataframes)
df_combined.to_csv("stocks_data.csv", index=False)
print("Datos guardados en stocks_data.csv")

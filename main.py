import yfinance as yf
import pandas as pd
import pandas_ta as ta
from sqlalchemy import create_engine

# Lista de tickers (Ejemplo con 3, puedes agregar más)
tickers = ["GGAL.BA", "YPFD.BA", "MELI"]  # Acciones argentinas y CEDEARs

# Configurar base de datos (PostgreSQL)
DB_URL = "postgresql://postgres:@localhost:5432/stocks_db"
engine = create_engine(DB_URL)

def download_stock_data(ticker, start="2022-01-01", end="2025-01-01"):
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
        stock["Close"].fillna(method="ffill", inplace=True)  # Rellenar NaN con el último valor válido


    # Calcular indicadores técnicos
    stock["EMA_50"] = ta.ema(stock["Close"], length=50)
    stock["RSI_14"] = ta.rsi(stock["Close"], length=14)

    # Verificar si MACD devuelve datos válidos
    macd_df = ta.macd(stock["Close"])
    if macd_df is None or macd_df.empty:
        print(f"Advertencia: No se pudo calcular MACD para {ticker}")
        return stock  # Devuelve sin MACD
    
    stock["MACD"] = ta.macd(stock["Close"])['MACD_12_26_9']
    stock["MACD_Signal"] = ta.macd(stock["Close"])['MACDs_12_26_9']
    
    stock.reset_index(inplace=True)
    stock["Ticker"] = ticker  # Agregar el ticker como columna
    return stock

def save_to_db(df, table_name="stock_prices"):
    # Cargar datos actuales en la base de datos
    existing_df = pd.read_sql(f"SELECT * FROM {table_name}", engine)

    # Filtrar solo los nuevos registros
    new_df = df[~df["Date"].isin(existing_df["Date"])]

    if not new_df.empty:
        new_df.to_sql(table_name, engine, if_exists="append", index=False)
        print("Nuevos datos insertados en la base de datos.")
    else:
        print("No hay nuevos datos para insertar.")

# Descargar y guardar datos para cada ticker
dataframes = []
for ticker in tickers:
    df = download_stock_data(ticker)
    if df is not None:
        dataframes.append(df)
        save_to_db(df)

# Guardar en CSV como alternativa
df_combined = pd.concat(dataframes)
df_combined.to_csv("stocks_data.csv", index=False)
print("Datos guardados en stocks_data.csv")

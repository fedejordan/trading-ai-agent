import pandas as pd
import psycopg2
from sqlalchemy import create_engine

# Configuración de la base de datos
DB_URI = "postgresql://postgres:@localhost:5432/stocks_db"
engine = create_engine(DB_URI)

# Parámetro: cantidad de días previos a considerar en el análisis de sentimiento
N_DAYS = 7  # Puedes ajustar este valor

# Cargar datos de stock_prices
query_prices = """
SELECT "date", "close", "high", "low", "open", "volume", "ema_50", "rsi_14", "macd", "macd_signal", "ticker"
FROM stock_prices;
"""
df_prices = pd.read_sql(query_prices, engine)

# Cargar datos de noticias con sentimiento
query_news = """
SELECT ticker, title, published_at, sentiment
FROM news;
"""
df_news = pd.read_sql(query_news, engine)

# Convertir fechas a formato datetime
df_prices['date'] = pd.to_datetime(df_prices['date'])
df_news['published_at'] = pd.to_datetime(df_news['published_at'])

# Normalizar tickers (todo a mayúsculas)
df_prices['ticker'] = df_prices['ticker'].str.upper()
df_news['ticker'] = df_news['ticker'].str.upper()

results = []
for idx, row in df_prices.iterrows():
    ticker = row['ticker']
    date = row['date']
    
    # Filtrar noticias para el ticker en la ventana [date - N_DAYS, date]
    mask = (
        (df_news['ticker'] == ticker) &
        (df_news['published_at'] <= date) &
        (df_news['published_at'] >= date - pd.Timedelta(days=N_DAYS))
    )
    df_filtered = df_news[mask]
    
    # Depuración: mostrar cuántas noticias se encuentran para cada fecha
    print(f"[DEBUG] Ticker: {ticker}, Fecha: {date.date()}, Noticias encontradas: {len(df_filtered)}")
    
    # Calcular el sentimiento promedio; si no hay noticias, se obtiene NaN y lo reemplazamos por 0.0
    avg_sentiment = df_filtered['sentiment'].mean()
    if pd.isna(avg_sentiment):
        avg_sentiment = 0.0
    
    results.append({
        'date': date,
        'ticker': ticker,
        'close': row['close'],
        'ema_50': row['ema_50'],
        'rsi_14': row['rsi_14'],
        'macd': row['macd'],
        'macd_signal': row['macd_signal'],
        'sentiment_avg': avg_sentiment
    })

df_final = pd.DataFrame(results)

# Opcional: si deseas propagar el último sentimiento conocido para días sin noticias, usa forward-fill
df_final['sentiment_avg'] = df_final.groupby('ticker')['sentiment_avg'].ffill().fillna(0)

# Mostrar algunas filas para validar
print(df_final.head())

# Guardar el DataFrame resultante en la base de datos en la tabla 'stock_analysis'
df_final.to_sql('stock_analysis', engine, if_exists='replace', index=False)

print("✅ Cruce de datos completado y guardado en la BD en 'stock_analysis'.")

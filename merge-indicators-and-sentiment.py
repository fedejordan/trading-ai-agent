import pandas as pd
import psycopg2
from sqlalchemy import create_engine

# Configuración de la base de datos
DB_URI = "postgresql://postgres:@localhost:5432/stocks_db"
engine = create_engine(DB_URI)

# Parámetro: cantidad de días previos a considerar en el análisis de sentimiento
N_DAYS = 5

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

# Merge de precios con sentimiento de noticias
results = []
for index, row in df_prices.iterrows():
    ticker = row['ticker']
    date = row['date']
    
    # Filtrar noticias de los últimos N días antes de la fecha del precio
    mask = (df_news['ticker'] == ticker) & (df_news['published_at'] <= date) & (df_news['published_at'] >= date - pd.Timedelta(days=N_DAYS))
    df_filtered_news = df_news[mask]
    
    # Calcular sentimiento promedio en la ventana de N días
    sentiment_avg = float(df_filtered_news['sentiment'].mean()) if not df_filtered_news.empty else 0.0

    results.append({
        'date': date,
        'ticker': ticker,
        'close': row['close'],
        'ema_50': row['ema_50'],
        'rsi_14': row['rsi_14'],
        'macd': row['macd'],
        'macd_signal': row['macd_signal'],
        'sentiment_avg': sentiment_avg
    })

# Convertir resultados a DataFrame
df_final = pd.DataFrame(results)

# Guardar en la BD en una nueva tabla
with engine.connect() as conn:
    df_final.to_sql('stock_analysis', conn, if_exists='replace', index=False)

print("✅ Cruce de datos completado y guardado en la BD en 'stock_analysis'.")

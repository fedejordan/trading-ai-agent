import psycopg2
import pandas as pd
import matplotlib.pyplot as plt

# Conectar a la base de datos
DB_URL = "postgresql://postgres:@localhost:5432/stocks_db"
conn = psycopg2.connect(DB_URL)

# Cargar datos de noticias con sentimiento
query = "SELECT ticker, published_at, sentiment FROM news WHERE sentiment IS NOT NULL"
df = pd.read_sql(query, conn)

# Cerrar conexión
conn.close()

# Convertir fecha a datetime
df["published_at"] = pd.to_datetime(df["published_at"])

# Agrupar por ticker y fecha, calculando el sentimiento promedio por día
df_grouped = df.groupby(["ticker", "published_at"]).mean().reset_index()

# Crear gráfico para cada ticker
tickers = df_grouped["ticker"].unique()

for ticker in tickers:
    df_ticker = df_grouped[df_grouped["ticker"] == ticker]
    
    plt.figure(figsize=(10, 5))
    plt.plot(df_ticker["published_at"], df_ticker["sentiment"], marker="o", linestyle="-")
    plt.axhline(0, color="black", linestyle="--", linewidth=1)
    plt.title(f"Tendencia del Sentimiento para {ticker}")
    plt.xlabel("Fecha")
    plt.ylabel("Sentimiento Promedio")
    plt.xticks(rotation=45)
    plt.grid()
    plt.show()

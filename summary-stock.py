import yfinance as yf
import pandas as pd
import numpy as np
import psycopg2
from datetime import datetime

def map_score_to_level(score):
    """
    Mapea un puntaje numérico a uno de los niveles:
    -2 -> "strong sell"
    -1 -> "sell"
     0 -> "neutral"
     1 -> "buy"
     2 -> "strong buy"
    """
    if score <= -1.5:
        return "strong sell"
    elif score <= -0.5:
        return "sell"
    elif score < 0.5:
        return "neutral"
    elif score < 1.5:
        return "buy"
    else:
        return "strong buy"

def insert_stock_analysis(total_summary, tech_summary, ma_action, rsi_signal, macd_action, price):
    # Parámetros de conexión (ajusta según tu configuración)
    conn = psycopg2.connect(
        host="localhost",
        database="stocks_db",
        user="postgres",
        password=""
    )

    cur = conn.cursor()

    # Crear la tabla si no existe
    create_table_query = """
    CREATE TABLE IF NOT EXISTS stock_analysis (
        id SERIAL PRIMARY KEY,
        analysis_date TIMESTAMP NOT NULL,
        total_summary VARCHAR(20),
        technical_indicators_summary VARCHAR(20),
        moving_averages_summary VARCHAR(20),
        rsi_action VARCHAR(20),
        macd_action VARCHAR(20),
        price NUMERIC
    );
    """
    cur.execute(create_table_query)
    conn.commit()

    # Fecha del análisis
    analysis_date = datetime.now()

    # Insertar los valores calculados
    insert_query = """
    INSERT INTO stock_analysis (
        analysis_date,
        total_summary,
        technical_indicators_summary,
        moving_averages_summary,
        rsi_action,
        macd_action,
        price
    ) VALUES (%s, %s, %s, %s, %s, %s, %s);
    """
    cur.execute(insert_query, (
        analysis_date,
        total_summary,
        tech_summary,
        ma_action,
        rsi_signal,
        macd_action,
        round(price, 2)
    ))
    conn.commit()

    print("Datos insertados en PostgreSQL")

    cur.close()
    conn.close()

# Descargar datos históricos de Tesla (TSLA) del último año
ticker = "TSLA"
data = yf.download(ticker, period="1y", interval="1d")

# Precio actual (último cierre) convertido a float
price = float(data['Close'].iloc[-1].item())

# --------------------------
# Cálculo del RSI (14)
# --------------------------
delta = data['Close'].diff()
gain = delta.where(delta > 0, 0)
loss = -delta.where(delta < 0, 0)
avg_gain = float(gain.rolling(window=14, min_periods=14).mean().iloc[-1].item())
avg_loss = float(loss.rolling(window=14, min_periods=14).mean().iloc[-1].item())
rs = avg_gain / avg_loss if avg_loss != 0 else np.nan
rsi = 100 - (100 / (1 + rs))

# Asignar puntaje al RSI según umbrales
if rsi <= 20:
    score_rsi = 2
elif rsi <= 30:
    score_rsi = 1
elif rsi < 70:
    score_rsi = 0
elif rsi < 80:
    score_rsi = -1
else:
    score_rsi = -2

rsi_signal = map_score_to_level(score_rsi)

# --------------------------
# Cálculo del MACD
# --------------------------
ema12 = data['Close'].ewm(span=12, adjust=False).mean()
ema26 = data['Close'].ewm(span=26, adjust=False).mean()
macd = ema12 - ema26
macd_signal_line = macd.ewm(span=9, adjust=False).mean()

latest_macd = float(macd.iloc[-1].item())
latest_macd_signal = float(macd_signal_line.iloc[-1].item())
diff = latest_macd - latest_macd_signal

hist = macd - macd_signal_line
std_hist = float(hist.std().item())

if diff >= std_hist:
    score_macd = 2
elif diff > 0:
    score_macd = 1
elif abs(diff) < 0.01:
    score_macd = 0
elif diff > -std_hist:
    score_macd = -1
else:
    score_macd = -2

macd_action = map_score_to_level(score_macd)

# --------------------------
# Cálculo de Moving Averages (MA)
# --------------------------
ma50 = float(data['Close'].rolling(window=50).mean().iloc[-1].item())
ma200 = float(data['Close'].rolling(window=200).mean().iloc[-1].item())

diff50 = (price - ma50) / ma50
diff200 = (price - ma200) / ma200
avg_diff = (diff50 + diff200) / 2.0

if avg_diff >= 0.05:
    score_ma = 2
elif avg_diff > 0:
    score_ma = 1
elif avg_diff >= -0.05:
    score_ma = 0
elif avg_diff > -0.10:
    score_ma = -1
else:
    score_ma = -2

ma_action = map_score_to_level(score_ma)

# --------------------------
# Technical Indicators Summary (RSI y MACD)
# --------------------------
tech_score = (score_rsi + score_macd) / 2.0
tech_summary = map_score_to_level(tech_score)

# --------------------------
# Total Summary (Technical + MA)
# --------------------------
total_score = (tech_score + score_ma) / 2.0
total_summary = map_score_to_level(total_score)

print("Total Summary:", total_summary)
print("Technical Indicators Summary:", tech_summary)
print("Moving Averages Summary:", ma_action)
print("RSI Action:", rsi_signal)
print("MACD Action:", macd_action)
print("Precio:", round(price, 2))

insert_stock_analysis(total_summary, tech_summary, ma_action, rsi_signal, macd_action, price)
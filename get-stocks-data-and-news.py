from datetime import datetime
import requests
from bs4 import BeautifulSoup
import dateparser
import yfinance as yf
import pandas as pd
import numpy as np
import psycopg2

# Configuración de conexión a la DB
DB_PARAMS = {
    "host": "localhost",
    "database": "stocks_db",
    "user": "postgres",
    "password": ""
}

###############################################
# Funciones para análisis de indicadores
###############################################

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

def insert_stock_analysis(total_summary, tech_summary, ma_action, rsi_signal, macd_action, price, ticker):
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    create_table_query = """
    CREATE TABLE IF NOT EXISTS stock_analysis (
        id SERIAL PRIMARY KEY,
        analysis_date TIMESTAMP NOT NULL,
        total_summary VARCHAR(20),
        technical_indicators_summary VARCHAR(20),
        moving_averages_summary VARCHAR(20),
        rsi_action VARCHAR(20),
        macd_action VARCHAR(20),
        price NUMERIC,
        ticker VARCHAR(10)
    );
    """
    cur.execute(create_table_query)
    conn.commit()

    analysis_date = datetime.now()

    # Verificar si ya existe un análisis para este ticker en la fecha actual (comparando solo la fecha)
    check_query = """
    SELECT id FROM stock_analysis 
    WHERE ticker = %s AND analysis_date::date = %s
    """
    cur.execute(check_query, (ticker, analysis_date.date()))
    if cur.fetchone():
        print(f"Ya existe un análisis para {ticker} en la fecha {analysis_date.date()}.")
        cur.close()
        conn.close()
        return

    insert_query = """
    INSERT INTO stock_analysis (
        analysis_date,
        total_summary,
        technical_indicators_summary,
        moving_averages_summary,
        rsi_action,
        macd_action,
        price,
        ticker
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
    """
    cur.execute(insert_query, (
        analysis_date,
        total_summary,
        tech_summary,
        ma_action,
        rsi_signal,
        macd_action,
        round(price, 2),
        ticker
    ))
    conn.commit()
    print(f"Datos insertados en PostgreSQL para {ticker}")
    cur.close()
    conn.close()

def calculate_rsi(data):
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = float(gain.rolling(window=14, min_periods=14).mean().iloc[-1].item())
    avg_loss = float(loss.rolling(window=14, min_periods=14).mean().iloc[-1].item())
    rs = avg_gain / avg_loss if avg_loss != 0 else np.nan
    rsi = 100 - (100 / (1 + rs))
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
    return map_score_to_level(score_rsi), score_rsi

def calculate_macd(data):
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
    return map_score_to_level(score_macd), score_macd

def calculate_moving_averages(data, price):
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
    return map_score_to_level(score_ma), score_ma

def process_ticker(ticker):
    try:
        data = yf.download(ticker, period="1y", interval="1d")
        if data.empty:
            print(f"No se obtuvieron datos para {ticker}")
            return
        price = float(data['Close'].iloc[-1].item())
        rsi_signal, score_rsi = calculate_rsi(data)
        macd_action, score_macd = calculate_macd(data)
        ma_action, score_ma = calculate_moving_averages(data, price)
        tech_score = (score_rsi + score_macd) / 2.0
        tech_summary = map_score_to_level(tech_score)
        total_score = (tech_score + score_ma) / 2.0
        total_summary = map_score_to_level(total_score)
        print(f"Ticker: {ticker}")
        print("  Total Summary:", total_summary)
        print("  Technical Indicators Summary:", tech_summary)
        print("  Moving Averages Summary:", ma_action)
        print("  RSI Action:", rsi_signal)
        print("  MACD Action:", macd_action)
        print("  Precio:", round(price, 2))
        insert_stock_analysis(total_summary, tech_summary, ma_action, rsi_signal, macd_action, price, ticker)
    except Exception as e:
        print(f"Error al procesar {ticker}: {e}")

###############################################
# Funciones para extracción de noticias
###############################################

def parse_published_date(published_text):
    # Se espera un texto tipo "Zacks • 3 months ago"
    parts = published_text.split("•")
    if len(parts) >= 2:
        relative_time = parts[-1].strip()
    else:
        relative_time = published_text.strip()
    parsed_date = dateparser.parse(relative_time)
    return parsed_date

def get_news_yahoo(ticker):
    url = f"https://finance.yahoo.com/quote/{ticker}/news"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"❌ ERROR {response.status_code} al obtener noticias de {ticker}")
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    # Buscamos enlaces con la clase 'subtle-link'
    articles = soup.find_all("a", {"class": "subtle-link"})
    
    news_data = []
    seen_links = set()

    for article in articles[:10]:  # Limitar a 10 noticias
        title = article.get_text(strip=True) or article.get("title", "").strip()
        link = article.get("href")
        
        if not title:
            print("⚠️ Advertencia: Se encontró una noticia sin título, se omitirá.")
            continue
        
        if not link.startswith("https"):
            link = "https://finance.yahoo.com" + link
        
        # Si el link no fue procesado, lo omitimos. Necesitamos que lo inserte al verlo por segunda vez por un tema de parsing de fechas
        if link not in seen_links:
            seen_links.add(link)
            continue
        
        # Intentamos extraer la fecha de publicación
        published_date = None
        footer = article.find_next_sibling("div", class_="footer")
        if footer:
            publishing_div = footer.find("div", class_="publishing")
            if publishing_div:
                published_text = publishing_div.get_text(strip=True)
                published_date = parse_published_date(published_text)
        
        if not published_date:
            published_date = datetime.now()
        
        news_data.append((ticker, title, link, published_date))
        print(f"📌 {title} - {link} (Publicado: {published_date})")
    
    return news_data

def save_news_to_db(news_list):
    if not news_list:
        print("⚠️ No hay noticias para guardar.")
        return
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    # Crear tabla si no existe; se define UNIQUE en link para evitar duplicados.
    create_table_query = """
    CREATE TABLE IF NOT EXISTS news (
        id SERIAL PRIMARY KEY,
        ticker VARCHAR(10),
        title TEXT,
        link TEXT UNIQUE,
        published_at TIMESTAMP
    );
    """
    cursor.execute(create_table_query)
    conn.commit()
    
    insert_query = """
        INSERT INTO news (ticker, title, link, published_at) 
        VALUES (%s, %s, %s, %s::timestamp)
        ON CONFLICT (link) DO NOTHING;
    """
    for news in news_list:
        print(f"Insertando noticia para {news[0]} con published_at = {news[3]}")
        cursor.execute(insert_query, news)
    
    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ {len(news_list)} noticias procesadas en la DB.")

###############################################
# Main: Procesar tickers y noticias
###############################################

def main():
    # Listas de tickers
    usa_tickers = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "JNJ", "V", "WMT"]
    argentina_tickers = ["GGAL.BA", "YPF", "PAMP.BA", "TX", "CEPU.BA", "SUPV.BA", "ALUA.BA", "BMA.BA", "EDN.BA", "COME.BA"]
    crypto_tickers = ["BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "ADA-USD", "SOL-USD", "DOT-USD", "DOGE-USD", "LTC-USD", "MATIC-USD"]

    all_tickers = usa_tickers + argentina_tickers + crypto_tickers

    # Procesar análisis de cada ticker
    print("Procesando análisis de activos...")
    for ticker in all_tickers:
        process_ticker(ticker)
    
    # Extraer e insertar noticias para cada ticker
    print("\nExtrayendo e insertando noticias para cada ticker...")
    for ticker in all_tickers:
        print(f"🔄 Obteniendo noticias para {ticker}...")
        news = get_news_yahoo(ticker)
        if news:
            save_news_to_db(news)
        else:
            print(f"⚠️ No se encontraron noticias para {ticker}.")

if __name__ == "__main__":
    main()

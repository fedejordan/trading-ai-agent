#!/usr/bin/env python3
from datetime import datetime, date
import os
import re
import requests
import dateparser
import yfinance as yf
import pandas as pd
import numpy as np
import psycopg2
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from fpdf import FPDF
# IMPORTACIÓN OPCIONAL: si se usan gráficos, matplotlib puede ser importado
import matplotlib.pyplot as plt
# IMPORTACIÓN DE CLIENTE DE GROK (asegúrate de tener instalado el paquete correspondiente)
from grok_client import GrokClient

###############################################
# CONFIGURACIÓN DE BASES DE DATOS
###############################################
DB_PARAMS = {
    "host": "localhost",
    "database": "stocks_db",
    "user": "postgres",
    "password": ""
}
DB_URL = "postgresql://postgres:@localhost/stocks_db"
engine = create_engine(DB_URL)

###############################################
# FUNCIONES PARA ANÁLISIS DE INDICADORES
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

def calculate_rsi(data):
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = float(gain.rolling(window=14, min_periods=14).mean().iloc[-1])
    avg_loss = float(loss.rolling(window=14, min_periods=14).mean().iloc[-1])
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
    latest_macd = float(macd.iloc[-1])
    latest_macd_signal = float(macd_signal_line.iloc[-1])
    diff = latest_macd - latest_macd_signal
    hist = macd - macd_signal_line
    std_hist = float(hist.std())
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
    ma50 = float(data['Close'].rolling(window=50).mean().iloc[-1])
    ma200 = float(data['Close'].rolling(window=200).mean().iloc[-1])
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

###############################################
# FUNCIONES PARA GUARDAR EN LA BASE DE DATOS
###############################################
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

###############################################
# FUNCIONES PARA PROCESAR TICKERS Y ANÁLISIS
###############################################
def process_ticker(ticker):
    try:
        data = yf.download(ticker, period="1y", interval="1d")
        if data.empty:
            print(f"No se obtuvieron datos para {ticker}")
            return
        price = float(data['Close'].iloc[-1])
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
# FUNCIONES PARA EXTRACCIÓN Y GUARDADO DE NOTICIAS
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
        
        # Si el link no fue procesado previamente, lo agregamos para marcarlo
        if link not in seen_links:
            seen_links.add(link)
            continue
        
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
# FUNCIONES PARA GENERAR REPORTE DIARIO
###############################################
def fetch_stock_analysis_for_today():
    """
    Extrae de la tabla stock_analysis los registros correspondientes a la fecha actual.
    """
    query = """
    SELECT ticker, analysis_date, total_summary, technical_indicators_summary, 
           moving_averages_summary, rsi_action, macd_action, price
    FROM stock_analysis
    WHERE analysis_date::date = %s
    ORDER BY ticker;
    """
    today = date.today()
    df = pd.read_sql(query, engine, params=(today,))
    return df

def fetch_latest_news(ticker, limit=5):
    """
    Obtiene las últimas 'limit' noticias para un ticker dado desde la tabla news.
    """
    query = """
    SELECT title, link, published_at
    FROM news
    WHERE ticker = %s
    ORDER BY published_at DESC
    LIMIT %s;
    """
    with engine.connect() as conn:
        news_df = pd.read_sql(query, conn, params=(ticker, limit))
    return news_df

def generate_daily_report_text(df):
    """
    Genera el texto base del reporte diario, incluyendo el resumen de análisis y las últimas noticias.
    """
    report = "Reporte Diario de Mercados\n"
    report += f"Fecha: {datetime.now().strftime('%Y-%m-%d')}\n\n"
    report += "Resumen de Análisis:\n"
    
    # Para cada ticker se agregan sus datos y noticias
    for _, row in df.iterrows():
        ticker = row['ticker']
        report += f"- {ticker}:\n"
        report += f"   Recomendación Global: {row['total_summary']} " \
                  f"(Técnico: {row['technical_indicators_summary']}, " \
                  f"Medias: {row['moving_averages_summary']}).\n"
        report += f"   RSI: {row['rsi_action']}, MACD: {row['macd_action']}. Precio: {row['price']}\n"
        
        # Obtener últimas 5 noticias
        news_df = fetch_latest_news(ticker, limit=5)
        if not news_df.empty:
            report += "   Últimas Noticias:\n"
            for _, news in news_df.iterrows():
                published = pd.to_datetime(news['published_at']).strftime('%Y-%m-%d')
                report += f"      * {news['title']} - {news['link']} (Publicado: {published})\n"
        else:
            report += "   No se encontraron noticias recientes.\n"
        report += "\n"
    return report

def generate_final_report(df):
    """
    Genera un reporte diario combinando el análisis obtenido y utiliza la API de Grok3
    para generar un análisis adicional y recomendaciones de inversión.
    """
    base_report = generate_daily_report_text(df)
    
    # Preparar prompt para la API de Grok3
    prompt = (
        "Eres un analista financiero experimentado. Con base en los siguientes datos diarios, "
        "genera un reporte que incluya:\n"
        " - El estado general del mercado.\n"
        " - Recomendaciones claras de compra y venta para el día.\n"
        " - Análisis de tendencias y factores técnicos (incluyendo indicadores, medias móviles, RSI, MACD, etc.).\n"
        "Datos:\n" + base_report +
        "\nEl reporte debe ser conciso, claro y útil para tomar decisiones de inversión diaria."
    )

    # Valores de cookies (ajusta según corresponda)
    cookies = {
        "x-anonuserid": "b4507c57-a948-482e-8136-780c5c84a0b1",
        "x-challenge": "DihL68ZFtBXalCC%2BULwZ%2BmrOQUb7AsS9zTGaDRAv3JpysrX3QnBbllKCCP741TacDN09kDe61LdxQSKeTQahXPTMCuCnRCXE6hB62DzHaaN4yXRiYNeo4jwHqpux7Qzj4i93uDtacIOXO8BUFeI2ATSGFqhmrJM%2Bm8O5uYkhDY%2BwM%2Bq%2Fnbc%3D",
        "x-signature": "Pn6TTqRTbqXG62zgbNvdS96GPeeZZU%2Fbi98NTNif5IISJVrtdmkirXD%2FugJntQ13YPori3lrt8TOPiB7fKEitQ%3D%3D",
        "sso": "eyJhbGciOiJIUzI1NiJ9.eyJzZXNzaW9uX2lkIjoiMjRmZDc5YzQtZGFjNi00MGI0LWFjZGMtNzJiMGNhMWFlNGE4In0.oitDPbuVQHr8dfcH7zW-VFRLPMMlafpMxLpx1G49Xes",
        "sso-rw": "eyJhbGciOiJIUzI1NiJ9.eyJzZXNzaW9uX2lkIjoiMjRmZDc5YzQtZGFjNi00MGI0LWFjZGMtNzJiMGNhMWFlNGE4In0.oitDPbuVQHr8dfcH7zW-VFRLPMMlafpMxLpx1G49Xes"
    }

    # Inicializar el cliente de Grok3
    client = GrokClient(cookies)
    response = client.send_message(prompt)
    print(f"Reporte generado por Grok3: {response}")
    final_report = response
    return final_report

###############################################
# FUNCIONES PARA GENERAR PDF CON REPORTE
###############################################
def write_formatted_line(pdf, line, font_size=12, line_height=8):
    """
    Escribe una línea de texto en el PDF procesando los segmentos en negrita.
    Los textos entre ** se escribirán en negrita y el resto en fuente normal.
    """
    segments = re.split(r'(\*\*.*?\*\*)', line)
    for seg in segments:
        if seg.startswith('**') and seg.endswith('**'):
            pdf.set_font("DejaVu", "B", font_size)
            pdf.write(line_height, seg[2:-2])
        else:
            pdf.set_font("DejaVu", "", font_size)
            pdf.write(line_height, seg)
    pdf.ln(line_height)

def create_pdf_report(report_text, output_filename="reporte_diario.pdf"):
    """
    Crea un PDF con el reporte, incluyendo el texto formateado.
    Se procesa Markdown básico para títulos y negrita.
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Registrar las fuentes DejaVu (asegúrate de tener los archivos en la ruta indicada)
    pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
    pdf.add_font('DejaVu', 'B', 'DejaVuSans-Bold.ttf', uni=True)

    # Portada
    pdf.add_page()
    pdf.set_font("DejaVu", "B", 16)
    pdf.cell(0, 10, "Reporte Diario de Mercados", ln=True, align="C")
    pdf.set_font("DejaVu", "", 12)
    pdf.cell(0, 10, f"Fecha: {datetime.now().strftime('%Y-%m-%d')}", ln=True, align="C")
    pdf.ln(10)

    for raw_line in report_text.splitlines():
        line = raw_line.strip()
        if not line:
            pdf.ln(4)
            continue

        if line.startswith("### "):
            header = line[4:].strip()
            pdf.set_font("DejaVu", "B", 16)
            pdf.cell(0, 10, header, ln=True)
        elif line.startswith("#### "):
            header = line[5:].strip()
            pdf.set_font("DejaVu", "B", 14)
            pdf.cell(0, 10, header, ln=True)
        elif line.startswith("- ") or line.startswith("• "):
            bullet = "• "
            content = line[2:].strip()
            pdf.set_font("DejaVu", "", 12)
            pdf.cell(10, 8, bullet, ln=0)
            write_formatted_line(pdf, content, font_size=12, line_height=8)
        else:
            write_formatted_line(pdf, line, font_size=12, line_height=8)
        pdf.ln(2)

    pdf.ln(5)
    pdf.output(output_filename)
    print(f"Reporte guardado en '{output_filename}'.")

###############################################
# FUNCIÓN PRINCIPAL UNIFICADA
###############################################
def main():
    # Listas de tickers
    usa_tickers = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "JNJ", "V", "WMT", "BABA", "NVDA", "GOLD", "MELI", "NFLX", "PYPL", "GM", "AAL", "ABNB"]
    argentina_tickers = ["GGAL.BA", "YPFD.BA", "PAMP.BA", "TX", "CEPU.BA", "SUPV.BA", "ALUA.BA", "BMA.BA", "EDN.BA", "COME.BA", "LOMA.BA", "MIRG.BA", "TRAN.BA"]
    crypto_tickers = ["BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "ADA-USD", "SOL-USD", "DOT-USD", "DOGE-USD", "LTC-USD", "MATIC-USD"]
    all_tickers = usa_tickers + argentina_tickers + crypto_tickers

    # Procesar análisis y noticias para cada ticker
    print("Procesando análisis de activos y extracción de noticias...")
    for ticker in all_tickers:
        process_ticker(ticker)
        print(f"🔄 Obteniendo noticias para {ticker}...")
        news = get_news_yahoo(ticker)
        if news:
            save_news_to_db(news)
        else:
            print(f"⚠️ No se encontraron noticias para {ticker}.")

    # Generar reporte diario (para la fecha actual)
    print("\nGenerando reporte diario...")
    df = fetch_stock_analysis_for_today()
    if df.empty:
        print("No hay datos de análisis para la fecha de hoy.")
        return

    # Se genera un reporte base y se envía a la API de Grok3 para obtener un análisis adicional
    final_report = generate_final_report(df)
    create_pdf_report(final_report)

if __name__ == "__main__":
    main()

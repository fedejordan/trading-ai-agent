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
import matplotlib.pyplot as plt
import openai
from openai import OpenAI
from dotenv import load_dotenv

# Nuevas importaciones para envío de email y scheduling
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import schedule
import time

###############################################
# CONFIGURACIÓN DE BASES DE DATOS
###############################################

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Configuración de conexión a la DB
DB_PARAMS = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "stocks_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "port": os.getenv("DB_PORT", "5432")
}
DB_URL = os.getenv("DB_URL")
engine = create_engine(DB_URL)

###############################################
# CONFIGURACIÓN DE EMAIL
###############################################
EMAIL_CONFIG = {
    "smtp_server": os.getenv("SMTP_SERVER"),
    "smtp_port": int(os.getenv("SMTP_PORT")),
    "username": os.getenv("EMAIL_USERNAME"),
    "password": os.getenv("EMAIL_PASSWORD"),
    "sender": os.getenv("EMAIL_SENDER"),
    "recipients": os.getenv("EMAIL_RECIPIENTS").split(",")  # Convertir la cadena en una lista
}

###############################################
# FUNCIONES PARA ANÁLISIS DE INDICADORES
###############################################
def map_score_to_level(score):
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
    articles = soup.find_all("a", {"class": "subtle-link"})
    news_data = []
    seen_links = set()

    for article in articles[:10]:
        title = article.get_text(strip=True) or article.get("title", "").strip()
        link = article.get("href")
        if not title:
            print("⚠️ Advertencia: Se encontró una noticia sin título, se omitirá.")
            continue
        if not link.startswith("https"):
            link = "https://finance.yahoo.com" + link
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
    report = "Reporte Diario de Mercados\n"
    report += f"Fecha: {datetime.now().strftime('%Y-%m-%d')}\n\n"
    report += "Resumen de Análisis:\n"
    for _, row in df.iterrows():
        ticker = row['ticker']
        report += f"- {ticker}:\n"
        report += f"   Recomendación Global: {row['total_summary']} " \
                  f"(Técnico: {row['technical_indicators_summary']}, " \
                  f"Medias: {row['moving_averages_summary']}).\n"
        report += f"   RSI: {row['rsi_action']}, MACD: {row['macd_action']}. Precio: {row['price']}\n"
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
    base_report = generate_daily_report_text(df)
    prompt = (
        "Con base en los siguientes datos diarios, "
        "genera un reporte que incluya:\n"
        " - El estado general del mercado.\n"
        " - Recomendaciones claras de compra y venta para el día.\n"
        " - Análisis de tendencias y factores técnicos (incluyendo indicadores, medias móviles, RSI, MACD, etc.).\n"
        " - Para estos items, hacer una seccion del mercado de USA, otra seccion para el mercado de Argentina y otra para cripto. Si no hay buenas señales de compra o de venta para ese dia, aclararlo.\n"
        "Datos:\n" + base_report +
        "\nEl reporte debe ser conciso, claro y útil para tomar decisiones de inversión diaria."
    )

    # Guardar el contenido de prompt en un archivo de texto
    with open("prompt.txt", "w") as file:
        file.write(prompt)

    api_key = os.getenv("DEEPSEEK_API_KEY")
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "Eres un analista financiero experimentado. "},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )

        if not response:
            raise ValueError("Respuesta de OpenAI vacía o None")
        
        print(f"response: {response}")
        final_report = response.choices[0].message.content
        return final_report
    except openai.APIConnectionError as e:
        print("The server could not be reached")
        print(e.__cause__)  # an underlying Exception, likely raised within httpx.
    except openai.RateLimitError as e:
        print("A 429 status code was received; we should back off a bit.")
    except openai.APIStatusError as e:
        print("Another non-200-range status code was received")
        print(e.status_code)
        print(e.response)
    except ValueError as e:
        print(f"Error de validación: {e}")
    except Exception as e:
        print(f"Error inesperado: {e}")


###############################################
# FUNCIONES PARA GENERAR PDF CON REPORTE
###############################################
def write_formatted_line(pdf, line, font_size=12, line_height=8):
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
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
    pdf.add_font('DejaVu', 'B', 'DejaVuSans-Bold.ttf', uni=True)
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
    return output_filename

###############################################
# NUEVA FUNCIÓN: ENVÍO DE CORREO CON EL REPORTE
###############################################
def send_email(report_file, subject="Reporte Diario de Mercados"):
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = EMAIL_CONFIG["sender"]
    msg['To'] = ", ".join(EMAIL_CONFIG["recipients"])
    
    # Cuerpo del mensaje
    body = MIMEText("Adjunto se encuentra el reporte diario de mercados.", "plain")
    msg.attach(body)
    
    # Adjuntar el PDF
    with open(report_file, "rb") as f:
        part = MIMEApplication(f.read(), Name=os.path.basename(report_file))
    part['Content-Disposition'] = f'attachment; filename="{os.path.basename(report_file)}"'
    msg.attach(part)
    
    try:
        with smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"]) as server:
            server.starttls()
            server.login(EMAIL_CONFIG["username"], EMAIL_CONFIG["password"])
            server.sendmail(msg['From'], EMAIL_CONFIG["recipients"], msg.as_string())
        print("Correo enviado exitosamente.")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")

###############################################
# CONFIGURACIÓN DE TWITTER
###############################################
TWITTER_CONFIG = {
    "api_key": os.getenv("TWITTER_API_KEY"),
    "api_secret_key": os.getenv("TWITTER_API_SECRET_KEY"),
    "access_token": os.getenv("TWITTER_ACCESS_TOKEN"),
    "access_token_secret": os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
}

###############################################
# FUNCIONES PARA PUBLICAR TWEETS
###############################################
def post_tweet(message):
    auth = tweepy.OAuthHandler(TWITTER_CONFIG["api_key"], TWITTER_CONFIG["api_secret_key"])
    auth.set_access_token(TWITTER_CONFIG["access_token"], TWITTER_CONFIG["access_token_secret"])
    api = tweepy.API(auth)
    try:
        api.update_status(message)
        print("Tweet publicado exitosamente.")
    except Exception as e:
        print(f"Error al publicar el tweet: {e}")


###############################################
# FUNCIÓN PRINCIPAL QUE REALIZA TODO EL PROCESO
###############################################
def main_job():
    # Listas de tickers
    usa_tickers = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "JNJ", "V", "WMT", "BABA", "NVDA", "GOLD", "MELI", "NFLX", "PYPL", "GM", "AAL", "ABNB"]
    argentina_tickers = ["GGAL.BA", "YPFD.BA", "PAMP.BA", "TX", "CEPU.BA", "SUPV.BA", "ALUA.BA", "BMA.BA", "EDN.BA", "COME.BA", "LOMA.BA", "MIRG.BA", "TRAN.BA"]
    crypto_tickers = ["BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "ADA-USD", "SOL-USD", "DOT-USD", "DOGE-USD", "LTC-USD", "MATIC-USD"]
    all_tickers = usa_tickers + argentina_tickers + crypto_tickers

    print("Procesando análisis de activos y extracción de noticias...")
    for ticker in all_tickers:
        process_ticker(ticker)
        print(f"🔄 Obteniendo noticias para {ticker}...")
        news = get_news_yahoo(ticker)
        if news:
            save_news_to_db(news)
        else:
            print(f"⚠️ No se encontraron noticias para {ticker}.")

    print("\nGenerando reporte diario...")
    df = fetch_stock_analysis_for_today()
    if df.empty:
        print("No hay datos de análisis para la fecha de hoy.")
        return

    final_report = generate_final_report(df)
    pdf_filename = create_pdf_report(final_report)
    send_email(pdf_filename)

    # Publicar tweet tras completar el proceso
    tweet_message = f"Reporte Diario de Mercados generado para {datetime.now().strftime('%Y-%m-%d')}. Revisa tu correo para más detalles."
    # post_tweet(tweet_message)

###############################################
# PROGRAMACIÓN DE LA TAREA: EJECUCIÓN A LAS 11:00 AM DE LUNES A VIERNES
###############################################
if __name__ == "__main__":
    main_job()
    # Programar la tarea para cada día hábil a las 11:00 AM
    # schedule.every().monday.at("11:00").do(main_job)
    # schedule.every().tuesday.at("11:00").do(main_job)
    # schedule.every().wednesday.at("11:00").do(main_job)
    # schedule.every().thursday.at("11:00").do(main_job)
    # schedule.every().friday.at("11:00").do(main_job)

    # print("Scheduler iniciado. Esperando la hora programada...")
    # while True:
    #     schedule.run_pending()
    #     time.sleep(60)  # Espera 60 segundos entre chequeos

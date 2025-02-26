from datetime import datetime
import requests
from bs4 import BeautifulSoup
import psycopg2  # O usa DuckDB si prefieres

# Configuración de la base de datos
DB_URL = "postgresql://postgres:@localhost:5432/stocks_db"

# Función para obtener noticias de Yahoo Finance
def get_news_yahoo(ticker):
    url = f"https://finance.yahoo.com/quote/{ticker}/news"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"❌ ERROR {response.status_code} al obtener noticias de {ticker}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    articles = soup.find_all("a", {"class": "subtle-link"})  # Buscar artículos con la clase correcta
    
    news_data = []
    
    for article in articles[:10]:  # Limitar a 10 noticias
        title = article.get_text(strip=True) or article.get("title", "").strip()
        link = article.get("href")

        if not title:
            print("⚠️ Advertencia: Se encontró una noticia sin título, se omitirá.")
            continue
        
        # Corregir links que ya contienen 'https'
        if not link.startswith("https"):
            link = "https://finance.yahoo.com" + link

        news_data.append((ticker, title, link, datetime.now()))

        print(f"📌 {title} - {link}")

    return news_data

# Guardar en la base de datos
def save_news_to_db(news_list):
    if not news_list:
        print("⚠️ No hay noticias para guardar.")
        return
    
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    query = """
        INSERT INTO news (ticker, title, link, published_at) 
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (link) DO NOTHING;  -- Evita duplicados
    """
    
    for news in news_list:
        cursor.execute(query, news)
    
    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ {len(news_list)} noticias guardadas en la DB.")

# Lista de tickers a buscar
tickers = ["GGAL", "YPF", "MELI"]

for ticker in tickers:
    print(f"🔄 Obteniendo noticias para {ticker}...")
    news = get_news_yahoo(ticker)
    if news:
        save_news_to_db(news)
    else:
        print(f"⚠️ No se encontraron noticias para {ticker}.")

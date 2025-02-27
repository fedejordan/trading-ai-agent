from datetime import datetime
import requests
from bs4 import BeautifulSoup
import psycopg2  # O usa DuckDB si prefieres
import dateparser  # Asegúrate de instalarlo con: pip install dateparser

# Configuración de la base de datos
DB_URL = "postgresql://postgres:@localhost:5432/stocks_db"

# Función para obtener la fecha de publicación a partir de un texto relativo
def parse_published_date(published_text):
    # En el ejemplo, el texto es algo similar a: "Zacks • 3 months ago"
    # Separamos por el símbolo • y tomamos la última parte
    parts = published_text.split("•")
    if len(parts) >= 2:
        relative_time = parts[-1].strip()
    else:
        relative_time = published_text.strip()
    # Usamos dateparser para convertirlo en un objeto datetime
    parsed_date = dateparser.parse(relative_time)
    return parsed_date

# Función para obtener noticias de Yahoo Finance
def get_news_yahoo(ticker):
    url = f"https://finance.yahoo.com/quote/{ticker}/news"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"❌ ERROR {response.status_code} al obtener noticias de {ticker}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    # Buscamos artículos con la clase 'subtle-link'
    articles = soup.find_all("a", {"class": "subtle-link"})
    
    news_data = []
    seen_links = set()  # Conjunto para almacenar enlaces ya procesados

    for article in articles[:10]:  # Limitar a 10 noticias
        # Obtener título del enlace (se intenta usar el texto del <h3> o el atributo title)
        title = article.get_text(strip=True) or article.get("title", "").strip()
        link = article.get("href")
        
        if not title:
            print("⚠️ Advertencia: Se encontró una noticia sin título, se omitirá.")
            continue
        
        # Corregir links que no sean absolutos
        if not link.startswith("https"):
            link = "https://finance.yahoo.com" + link
        
        # # Si ya procesamos este enlace, saltarlo
        if link not in seen_links:
            seen_links.add(link)
            continue

        # Intentar extraer la fecha de publicación desde el siguiente bloque 'footer'
        published_date = None
        footer = article.find_next_sibling("div", class_="footer")
        if footer:
            publishing_div = footer.find("div", class_="publishing")
            print(f"🔍 publishing_div: {publishing_div}")
            if publishing_div:
                published_text = publishing_div.get_text(strip=True)
                print(f"🔍 published_text: {published_text}")
                published_date = parse_published_date(published_text)
                print(f"🔍 published_date: {published_date}")
        
        if not published_date:
            # Si no se pudo extraer, usar la fecha actual
            published_date = datetime.now()
            print(f"🔍 published_date - now: {published_date}")
        
        news_data.append((ticker, title, link, published_date))
        print(f"📌 {title} - {link} (Publicado: {published_date})")
    
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
        VALUES (%s, %s, %s, %s::timestamp)
        ON CONFLICT (link) DO NOTHING;  -- Evita duplicados
    """
    
    for news in news_list:
        print("Insertando noticia con published_at =", news[3])
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
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import pandas as pd

# Configuración del navegador indetectable
options = uc.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")  
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--headless")  # Cambiar a False si quieres ver el navegador
options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(100,133)}.0.0.0 Safari/537.36")

driver = uc.Chrome(options=options, use_subprocess=True)

stocks = {
    "GGAL": "https://www.investing.com/equities/grupo-financiero-galicia-sa-adr-news",
    "YPF": "https://www.investing.com/equities/ypf-sa-news",
    "MELI": "https://www.investing.com/equities/mercadolibre-news"
}

def get_news(stock_name, url):
    print(f"🔄 Cargando página para {stock_name}... {url}")
    driver.get(url)
    time.sleep(random.uniform(4, 7))

    page_html = driver.page_source
    if "Just a moment" in page_html or "captcha" in page_html.lower():
        print(f"🚨 CAPTCHA detectado en {stock_name}. Posible bloqueo de scraping.")
        return []

    attempts = 2
    news_data = []

    for attempt in range(attempts):
        try:
            print(f"🔍 Intento {attempt+1} para {stock_name}...")

            articles = WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[data-test='article-title-link']"))
            )

            if not articles:
                print(f"⚠️ No se encontraron noticias en intento {attempt+1}. Refrescando...")
                driver.refresh()
                time.sleep(5)
                continue

            print(f"✅ Se encontraron {len(articles)} noticias para {stock_name}")

            for i, article in enumerate(articles[:10]):
                try:
                    title = article.text.strip() if article.text else "Sin título"
                    link = article.get_attribute("href") if article.get_attribute("href") else "Sin enlace"
                    news_data.append({"Stock": stock_name, "Title": title, "Link": link})
                    print(f"📌 ({i+1}) {title}")

                except Exception as e:
                    print(f"⚠️ Error extrayendo una noticia: {e}")

            return news_data

        except Exception as e:
            print(f"❌ ERROR en {stock_name} en intento {attempt+1}: {e}")

    print(f"⚠️ No se encontraron noticias para {stock_name} después de {attempts} intentos.")
    return []

all_news = []
for stock, url in stocks.items():
    all_news.extend(get_news(stock, url))

if all_news:
    df = pd.DataFrame(all_news)
    df.to_csv("investing_news.csv", index=False, encoding="utf-8")
    print("✅ Noticias guardadas en 'investing_news.csv'")
else:
    print("⚠️ No se encontraron noticias para guardar.")

driver.quit()

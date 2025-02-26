import logging
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from urllib3.exceptions import ReadTimeoutError
from bs4 import BeautifulSoup

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logging.info("Iniciando el script de scrapping para Investing.com")

# URL de la página a scrapear
url = "https://www.investing.com/equities/tesla-motors-technical"
logging.info(f"URL a scrapear: {url}")

# Configurar opciones para Chrome
options = Options()
options.add_argument("--headless")  # Modo headless
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
logging.info("Opciones de Chrome configuradas (page_load_strategy='normal').")

# Inicializar el driver
logging.info("Inicializando el driver de Chrome...")
driver = webdriver.Chrome(options=options)
driver.set_page_load_timeout(240)
logging.info("Driver iniciado.")

# Cargar la página con manejo de timeout
logging.info("Cargando la página...")
try:
    driver.get(url)
except (TimeoutException, ReadTimeoutError, Exception) as e:
    logging.error("Error al cargar la página, se continuará con el HTML parcial: " + str(e))

# Esperar y aceptar el popup de cookies si está presente (usualmente con id "onetrust-accept-btn-handler")
try:
    logging.info("Buscando popup de cookies...")
    accept_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
    )
    accept_button.click()
    logging.info("Cookie consent aceptado.")
    time.sleep(2)  # Esperar un poco para que se procese la aceptación
except TimeoutException:
    logging.info("No se encontró popup de cookies.")

# Espera explícita para asegurarnos de que se cargue el elemento clave (precio)
try:
    logging.info("Esperando a que aparezca el elemento clave (precio)...")
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test='instrument-price-last']"))
    )
    logging.info("Elemento clave encontrado. La página se cargó correctamente.")
except TimeoutException:
    logging.error("Timeout esperando el elemento clave. Se continuará con el HTML parcial.")

# Obtener el HTML renderizado
logging.info("Obteniendo el HTML renderizado...")
html = driver.page_source
logging.info("HTML obtenido.")

# (Opcional) Guardar el HTML en un archivo para inspeccionarlo
with open("investing.html", "w", encoding="utf-8") as f:
    f.write(html)
logging.info("HTML guardado en 'investing.html'.")

# Cerrar el driver
driver.quit()
logging.info("Driver cerrado.")

# Parsear el HTML con BeautifulSoup
logging.info("Parseando el HTML con BeautifulSoup...")
soup = BeautifulSoup(html, "html.parser")
logging.info("HTML parseado.")

# Extraer Total Summary y Technical Indicators Summary (usando las clases correspondientes)
logging.info("Extrayendo Total Summary y Technical Indicators Summary...")
elements_conclusion = soup.find_all(attrs={"class": re.compile("Table_conclusion-0__")})
total_summary = elements_conclusion[0].get_text(strip=True) if len(elements_conclusion) > 0 else "No encontrado"
technical_summary = elements_conclusion[1].get_text(strip=True) if len(elements_conclusion) > 1 else "No encontrado"
logging.info(f"Total Summary: {total_summary}")
logging.info(f"Technical Indicators Summary: {technical_summary}")

# Extraer Moving Averages usando el label "Moving Averages" y luego el siguiente <td>
logging.info("Extrayendo Moving Averages (valor)...")
moving_label = soup.find("span", string=re.compile("Moving Averages"))
moving_averages_summary = "No encontrado"
if moving_label:
    parent_td = moving_label.find_parent("td")
    if parent_td:
        tds = parent_td.find_next_siblings("td")
        if tds:
            moving_averages_summary = tds[0].get_text(strip=True)
logging.info(f"Moving Averages Summary: {moving_averages_summary}")

# Extraer RSI (valor y acción) usando el label "RSI(14)"
logging.info("Extrayendo RSI (valor y acción)...")
rsi_label = soup.find("span", string=re.compile("RSI\\(14\\)"))
rsi_value, rsi_action = ("No encontrado", "No encontrado")
if rsi_label:
    parent_td = rsi_label.find_parent("td")
    if parent_td:
        tds = parent_td.find_next_siblings("td")
        if len(tds) >= 2:
            rsi_value = tds[0].get_text(strip=True)
            rsi_action = tds[1].get_text(strip=True)
logging.info(f"RSI Value: {rsi_value}")
logging.info(f"RSI Action: {rsi_action}")

# Extraer MACD (valor y acción) usando el label "MACD(12,26)"
logging.info("Extrayendo MACD (valor y acción)...")
macd_label = soup.find("span", string=re.compile("MACD\\(12,26\\)"))
macd_value, macd_action = ("No encontrado", "No encontrado")
if macd_label:
    parent_td = macd_label.find_parent("td")
    if parent_td:
        tds = parent_td.find_next_siblings("td")
        if len(tds) >= 2:
            macd_value = tds[0].get_text(strip=True)
            macd_action = tds[1].get_text(strip=True)
logging.info(f"MACD Value: {macd_value}")
logging.info(f"MACD Action: {macd_action}")

# Extraer el precio actual
logging.info("Extrayendo el precio actual...")
price_div = soup.find("div", attrs={"data-test": "instrument-price-last"})
price = price_div.get_text(strip=True) if price_div else "No encontrado"
logging.info(f"Precio: {price}")

# Imprimir los resultados finales
print("Total Summary:", total_summary)
print("Technical Indicators Summary:", technical_summary)
print("Moving Averages Summary:", moving_averages_summary)
print("RSI Value:", rsi_value)
print("RSI Action:", rsi_action)
print("MACD Value:", macd_value)
print("MACD Action:", macd_action)
print("Precio:", price)

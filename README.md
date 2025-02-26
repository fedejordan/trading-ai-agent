# 📈 Trading AI Agent

Este proyecto es un agente de inteligencia artificial para el análisis de acciones argentinas y CEDEARs. Realiza la recopilación de datos históricos, cálculo de indicadores técnicos, monitoreo de noticias y generación de recomendaciones de compra/venta.

## 🚀 Características
- 📊 **Obtención de Datos:** Descarga datos históricos de acciones y CEDEARs desde Yahoo Finance.
- 📈 **Análisis Técnico:** Calcula indicadores como RSI, MACD, EMA, y Bollinger Bands.
- 📰 **Monitoreo de Noticias:** Extrae titulares de Investing.com para cada ticker.
- 🤖 **Señales de Trading:** Genera señales de compra/venta basadas en análisis técnico y sentimiento de noticias.
- 🛠️ **Almacenamiento:** Guarda los datos en PostgreSQL y CSV.

## 📂 Estructura del Proyecto
```
trading-ai-agent/
│── env/                   # Entorno virtual de Python
│── main.py                # Script principal
│── requirements.txt       # Dependencias del proyecto
│── config.py              # Configuración de la base de datos y API keys
│── data/                  # Archivos CSV de respaldo
│── README.md              # Documentación del proyecto
```

## 🔧 Instalación y Configuración
### 1️⃣ Clonar el repositorio
```bash
git clone https://github.com/tu_usuario/trading-ai-agent.git
cd trading-ai-agent
```

### 2️⃣ Crear y activar un entorno virtual
```bash
python3 -m venv env
source env/bin/activate   # En macOS/Linux
env\Scripts\activate      # En Windows
```

### 3️⃣ Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4️⃣ Configurar la base de datos PostgreSQL
Modifica `config.py` con tus credenciales de base de datos.

### 5️⃣ Ejecutar el script principal
```bash
python main.py
```

## 📊 Uso del Proyecto
- Se ejecutará la descarga de datos históricos.
- Se calcularán los indicadores técnicos.
- Se monitorearán las noticias.
- Se generarán señales de trading y se almacenarán en la base de datos.

## 📌 Próximos Pasos
- 🔍 Mejorar el scraping de noticias para obtener más datos relevantes.
- 📬 Implementar notificaciones en Telegram para alertas de trading.
- 🤖 Integrar Machine Learning para mejorar predicciones de compra/venta.

## 🛠 Tecnologías Usadas
- **Python** (pandas, yfinance, pandas-ta, SQLAlchemy, BeautifulSoup)
- **PostgreSQL** (Almacenamiento de datos históricos)
- **Yahoo Finance API** (Fuente de datos financieros)
- **Investing.com Scraper** (Noticias relevantes del mercado)

---

📧 Para soporte o consultas, contáctame en [tu_email@example.com](mailto:tu_email@example.com).


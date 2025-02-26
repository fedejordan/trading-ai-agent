# 🛣️ Roadmap - Trading AI Agent

Este roadmap detalla las fases de desarrollo del **Trading AI Agent**, desde la obtención de datos hasta la implementación de Machine Learning para optimizar las recomendaciones de trading.

---

## 📌 **Fase 1: Obtención de Datos**

### 🔹 1.1. Recolección de Datos Históricos
- ✅ Definir la lista de tickers de acciones argentinas y CEDEARs.
- ✅ Implementar un script en Python que descargue los datos históricos desde:
  - Yahoo Finance (`yfinance`)
  - Alpha Vantage (requiere API key)
  - BCRA (para datos de referencia en ARS)
  - Bolsa de Comercio de Buenos Aires (opcional)
- ✅ Almacenar los datos en **PostgreSQL** o **DuckDB**.
- 🔄 Automatizar la actualización diaria.

### 🔹 1.2. Monitoreo de Últimas Noticias
- ✅ Scraping de Investing.com para obtener titulares de cada acción.
- 🔄 Alternativa: API de Google News o Bing Search.
- ✅ Implementar scraping de titulares con **BeautifulSoup** o **Scrapy**.
- ✅ Guardar titulares en la base de datos con **timestamp**.
- 🔄 Implementar análisis de sentimiento con **TextBlob** o **VADER**.

---

## 📌 **Fase 2: Cálculo de Indicadores Técnicos**

### 🔹 Indicadores Clave a Implementar
- ✅ **Tendencia:** EMA, SMA
- ✅ **Momento:** RSI, MACD
- ✅ **Volatilidad:** Bollinger Bands, ATR
- ✅ **Volumen:** OBV, VWAP
- ✅ Implementar cálculos de indicadores con **pandas_ta** o **TA-Lib**.
- 🔄 Crear un pipeline de procesamiento diario para mantener los indicadores actualizados.

---

## 📌 **Fase 3: Generación de Recomendaciones**

### 🔹 Estrategia Inicial (Reglas Heurísticas)
- ✅ Comprar cuando **RSI < 30** y el precio cruza **SMA 50** al alza.
- ✅ Vender cuando **RSI > 70** o hay cruce bajista en **MACD**.
- ✅ Evitar operar cuando **ATR** está en niveles altos (alta volatilidad).
- 🔄 Incorporar un filtro de sentimiento (si muchas noticias negativas → no comprar).
- ✅ Implementar reglas básicas de trading basadas en indicadores.
- 🔄 Ajustar umbrales y condiciones según **backtesting**.

---

## 📌 **Fase 4: Backtesting y Optimización**

- ✅ Implementar **backtesting** con `backtrader` o `bt`.
- ✅ Probar estrategias en datos históricos.
- 🔄 Ajustar parámetros como períodos de **EMA, RSI, MACD** según resultados.
- ✅ Evaluar métricas como **Win Rate, Sharpe Ratio, Drawdown**.

---

## 📌 **Fase 5: Automatización y Notificaciones**

### 🔹 Infraestructura y Alertas
- ✅ Enviar **notificaciones por Telegram o email** cuando se detecte una oportunidad.
- 🔄 Crear un **dashboard en Next.js** con gráficos interactivos para visualizar datos.
- 🔄 Hospedar el bot en **AWS Lambda, Railway, o Fly.io**.
- ✅ Implementar un **endpoint API en Flask** para consultar recomendaciones en tiempo real.

---

## 📌 **Fase 6: Expansión con Machine Learning (Opcional)**

### 🔹 Optimización de Recomendaciones con ML
- 🔄 Usar **XGBoost** o **Random Forest** para mejorar predicciones de compra/venta.
- 🔄 Entrenar el modelo con datos históricos combinando **indicadores técnicos y noticias**.
- 🔄 Ajustar hiperparámetros y evaluar el rendimiento del modelo.

---

## 🚀 **Siguientes Pasos**
- 🛠️ **Optimizar scraping de noticias** para obtener más información relevante.
- 📬 **Mejorar alertas en Telegram/email** con reportes más detallados.
- 🤖 **Implementar Machine Learning** para optimizar la estrategia de trading.

📢 **Este roadmap será actualizado a medida que avancemos en el desarrollo.**


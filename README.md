# 📈 Trading AI Agent

This project is an artificial intelligence agent for analyzing Argentine stocks and CEDEARs. It collects historical data, calculates technical indicators, monitors news, and generates buy/sell recommendations.

## 🚀 Features

* 📈 **Data Collection:** Downloads historical stock and CEDEAR data from Yahoo Finance.
* 📈 **Technical Analysis:** Calculates indicators such as RSI, MACD, EMA, and Bollinger Bands.
* 📰 **News Monitoring:** Extracts headlines from Investing.com for each ticker.
* 🤖 **Trading Signals:** Generates buy/sell signals based on technical analysis and news sentiment.
* 🛠️ **Storage:** Saves data in PostgreSQL and CSV.

## 📂 Project Structure

```
trading-ai-agent/
│── env/                   # Python virtual environment
│── main.py                # Main script
│── requirements.txt       # Project dependencies
│── config.py              # Database and API key configuration
│── data/                  # Backup CSV files
│── README.md              # Project documentation
```

## 🔧 Installation and Setup

### 1️⃣ Clone the repository

```bash
git clone https://github.com/your_username/trading-ai-agent.git
cd trading-ai-agent
```

### 2️⃣ Create and activate a virtual environment

```bash
python3 -m venv env
source env/bin/activate   # On macOS/Linux
env\Scripts\activate      # On Windows
```

### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Configure the PostgreSQL database

Edit `config.py` with your database credentials.

### 5️⃣ Run the main script

```bash
python main.py
```

## 📊 Using the Project

* Historical data will be downloaded.
* Technical indicators will be calculated.
* News will be monitored.
* Trading signals will be generated and stored in the database.

## 📌 Next Steps

* 🔍 Improve news scraping for more relevant data.
* 📬 Implement Telegram notifications for trading alerts.
* 🤖 Integrate Machine Learning to improve buy/sell predictions.

## 🛠 Technologies Used

* **Python** (pandas, yfinance, pandas-ta, SQLAlchemy, BeautifulSoup)
* **PostgreSQL** (Storage of historical data)
* **Yahoo Finance API** (Source of financial data)
* **Investing.com Scraper** (Relevant market news)

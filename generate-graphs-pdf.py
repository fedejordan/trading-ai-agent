import matplotlib.pyplot as plt
import yfinance as yf
from fpdf import FPDF
import tempfile
import os
import numpy as np

def plot_stock_analysis(data, ticker, pdf):
    fig, axes = plt.subplots(3, 1, figsize=(12, 12), sharex=True)
    
    # Gráfico de precios y medias móviles
    axes[0].plot(data.index, data['Close'], label='Close Price', linewidth=2)
    axes[0].plot(data.index, data['Close'].rolling(window=50).mean(), label='MA 50', linestyle='dashed')
    axes[0].plot(data.index, data['Close'].rolling(window=200).mean(), label='MA 200', linestyle='dotted')
    axes[0].set_title(f'Precio y Medias Móviles - {ticker}')
    axes[0].legend()
    
    # RSI
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14, min_periods=14).mean()
    avg_loss = loss.rolling(window=14, min_periods=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    axes[1].plot(data.index, rsi, label='RSI', color='purple')
    axes[1].axhline(70, linestyle='dashed', color='red', alpha=0.5)
    axes[1].axhline(30, linestyle='dashed', color='green', alpha=0.5)
    axes[1].set_title(f'RSI - {ticker}')
    axes[1].legend()
    
    # MACD
    ema12 = data['Close'].ewm(span=12, adjust=False).mean()
    ema26 = data['Close'].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = (macd - signal).fillna(0).squeeze().tolist()  # Asegurar que sea una serie antes de convertir a lista
    
    axes[2].plot(data.index, macd, label='MACD', color='blue')
    axes[2].plot(data.index, signal, label='Signal', color='orange', linestyle='dashed')
    axes[2].bar(data.index, hist, label='Histogram', color='gray', alpha=0.5, width=1.0)
    axes[2].set_title(f'MACD - {ticker}')
    axes[2].legend()
    
    # Guardar gráfico en archivo temporal
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    plt.savefig(temp_file.name)
    plt.close(fig)
    
    # Agregar imagen al PDF
    pdf.add_page()
    pdf.set_font("Arial", size=16)
    pdf.cell(200, 10, f'Análisis Técnico - {ticker}', ln=True, align='C')
    pdf.image(temp_file.name, x=10, y=30, w=190)
    os.unlink(temp_file.name)

def generate_pdf(tickers, filename="stock_analysis.pdf"):
    pdf = FPDF()
    for ticker in tickers:
        data = yf.download(ticker, period='1y', interval='1d')
        if not data.empty:
            plot_stock_analysis(data, ticker, pdf)
    pdf.output(filename)
    print(f"PDF guardado como {filename}")

# Lista de tickers a analizar
tickers = ['AAPL', 'MSFT', 'GOOGL', 'YPF', 'TSLA', 'BRK-B']
generate_pdf(tickers)

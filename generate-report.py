import os
from datetime import datetime, date
import matplotlib.pyplot as plt
import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine
import psycopg2
from fpdf import FPDF
from grok_client import GrokClient
import re

# Configuración de conexión a la DB mediante SQLAlchemy
DB_URL = "postgresql://postgres:@localhost/stocks_db"
engine = create_engine(DB_URL)

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
    
    # Para cada ticker, se agregan sus datos y las últimas noticias
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

    # Enviar el prompt y obtener la respuesta
    response = client.send_message(prompt)
    print(f"Reporte generado por Grok3: {response}")
    
    # Se incorpora el análisis adicional al reporte
    final_report = response
    return final_report

import re
from fpdf import FPDF
from datetime import datetime

def write_formatted_line(pdf, line, font_size=12, line_height=8):
    """
    Escribe una línea de texto en el PDF procesando los segmentos en negrita.
    Los textos entre ** se escribirán en negrita y el resto en fuente normal.
    """
    # Dividir la línea en segmentos: los que estén entre ** y los que no.
    segments = re.split(r'(\*\*.*?\*\*)', line)
    for seg in segments:
        if seg.startswith('**') and seg.endswith('**'):
            # Establecer fuente en negrita y escribir el texto sin los asteriscos
            pdf.set_font("DejaVu", "B", font_size)
            pdf.write(line_height, seg[2:-2])
        else:
            # Fuente normal
            pdf.set_font("DejaVu", "", font_size)
            pdf.write(line_height, seg)
    pdf.ln(line_height)

def create_pdf_report(report_text, output_filename="reporte_diario.pdf"):
    """
    Crea un PDF con el reporte, incluyendo el texto formateado y los gráficos,
    procesando el Markdown básico para títulos y negrita.
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

    # Procesar y agregar el texto del reporte línea por línea
    for raw_line in report_text.splitlines():
        line = raw_line.strip()
        if not line:
            pdf.ln(4)
            continue

        # Encabezados de nivel 3 (###)
        if line.startswith("### "):
            header = line[4:].strip()
            pdf.set_font("DejaVu", "B", 16)
            pdf.cell(0, 10, header, ln=True)
        # Encabezados de nivel 4 (####)
        elif line.startswith("#### "):
            header = line[5:].strip()
            pdf.set_font("DejaVu", "B", 14)
            pdf.cell(0, 10, header, ln=True)
        # Líneas con viñetas
        elif line.startswith("- ") or line.startswith("• "):
            # Si la línea empieza con viñeta, la mantenemos y luego procesamos el contenido
            bullet = "• "
            content = line[2:].strip() if line.startswith("- ") else line[2:].strip()
            pdf.set_font("DejaVu", "", 12)
            pdf.cell(10, 8, bullet, ln=0)
            # Escribir el contenido con formato en la misma línea
            # Usamos write_formatted_line para el resto del texto
            write_formatted_line(pdf, content, font_size=12, line_height=8)
        else:
            # Para el resto de líneas, utilizar la función de formato en línea
            write_formatted_line(pdf, line, font_size=12, line_height=8)
        pdf.ln(2)

    pdf.ln(5)
    
    # Guardar el PDF
    pdf.output(output_filename)
    print(f"Reporte guardado en '{output_filename}'.")

def main():
    # Extraer datos de análisis de la fecha actual
    df = fetch_stock_analysis_for_today()
    if df.empty:
        print("No hay datos de análisis para la fecha de hoy.")
        return

    # Generar reporte diario con análisis adicional
    daily_report = generate_final_report(df)
    
    # Crear PDF con el reporte y los gráficos
    create_pdf_report(daily_report)

if __name__ == "__main__":
    main()

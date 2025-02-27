import os
from datetime import datetime, date
import matplotlib.pyplot as plt
import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine
import psycopg2
from fpdf import FPDF
from grok_client import GrokClient

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

def generate_recommendation_chart(df):
    """
    Genera un gráfico de barras que muestra la distribución de recomendaciones globales.
    """
    categories = ["strong sell", "sell", "neutral", "buy", "strong buy"]
    recommendation_counts = df['total_summary'].value_counts().reindex(categories, fill_value=0)
    
    plt.figure(figsize=(8,6))
    recommendation_counts.plot(kind='bar', color='skyblue')
    plt.title("Distribución de Recomendaciones de Mercado")
    plt.xlabel("Recomendación")
    plt.ylabel("Cantidad de Activos")
    plt.xticks(rotation=45)
    plt.tight_layout()
    chart_filename = "recomendaciones.png"
    plt.savefig(chart_filename)
    plt.close()
    return chart_filename

def generate_price_chart(df):
    """
    Genera un gráfico de barras que muestra el precio de cierre de cada activo.
    """
    plt.figure(figsize=(10,6))
    df_sorted = df.sort_values(by='price', ascending=False)
    plt.bar(df_sorted['ticker'], df_sorted['price'], color='green')
    plt.title("Precio de Cierre de Activos Analizados")
    plt.xlabel("Ticker")
    plt.ylabel("Precio")
    plt.xticks(rotation=45)
    plt.tight_layout()
    chart_filename = "precios.png"
    plt.savefig(chart_filename)
    plt.close()
    return chart_filename

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

def generate_final_report(df, charts):
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
        " - Comentarios sobre los gráficos adjuntos (distribución de recomendaciones y precios de cierre).\n\n"
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

def create_pdf_report(report_text, charts, output_filename="reporte_diario.pdf"):
    """
    Crea un PDF con el reporte, incluyendo el texto formateado y los gráficos.
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Registra la fuente DejaVu Sans (asegúrate de tener el archivo DejaVuSans.ttf en el mismo directorio o indica la ruta correcta)
    pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
    pdf.add_font('DejaVu', 'B', 'DejaVuSans-Bold.ttf', uni=True)

    # Portada
    pdf.add_page()
    pdf.set_font("DejaVu", "B", 16)
    pdf.cell(0, 10, "Reporte Diario de Mercados", ln=True, align="C")
    pdf.set_font("DejaVu", "", 12)
    pdf.cell(0, 10, f"Fecha: {datetime.now().strftime('%Y-%m-%d')}", ln=True, align="C")
    pdf.ln(10)
    
    # Agregar el texto del reporte
    pdf.set_font("DejaVu", "", 12)
    for line in report_text.split('\n'):
        pdf.multi_cell(0, 8, line)
    pdf.ln(5)
    
    # Agregar gráficos
    for chart in charts:
        pdf.add_page()
        pdf.set_font("DejaVu", "B", 14)
        # Mostrar el nombre del gráfico como título
        title = "Distribución de Recomendaciones" if "recomendaciones" in chart else "Precio de Cierre de Activos"
        pdf.cell(0, 10, title, ln=True, align="C")
        pdf.ln(5)
        # Insertar imagen
        pdf.image(chart, w=pdf.w - 40)
    
    # Guardar el PDF
    pdf.output(output_filename)
    print(f"Reporte guardado en '{output_filename}'.")

def main():
    # Extraer datos de análisis de la fecha actual
    df = fetch_stock_analysis_for_today()
    if df.empty:
        print("No hay datos de análisis para la fecha de hoy.")
        return

    # Generar gráficos y guardar los archivos
    chart1 = generate_recommendation_chart(df)
    chart2 = generate_price_chart(df)
    charts = [chart1, chart2]

    # Generar reporte diario con análisis adicional
    daily_report = generate_final_report(df, charts)
    
    # Crear PDF con el reporte y los gráficos
    create_pdf_report(daily_report, charts)

if __name__ == "__main__":
    main()

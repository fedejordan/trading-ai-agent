import os
from datetime import datetime, date
import matplotlib.pyplot as plt
import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine
import psycopg2
# Importar la librería deepseek (asegúrate de tenerla instalada)
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

def generate_daily_report(df, charts):
    """
    Genera un reporte diario combinando los datos obtenidos y utiliza la API de Deepseek r1
    para incluir un análisis adicional y recomendaciones de inversión.
    """
    # Resumen básico a partir de la DB
    report = "Reporte Diario de Mercados\n"
    report += f"Fecha: {datetime.now().strftime('%Y-%m-%d')}\n\n"
    report += "Resumen de Análisis:\n"
    for _, row in df.iterrows():
        report += (f"- {row['ticker']}: Recomendación Global: {row['total_summary']} "
                   f"(Técnico: {row['technical_indicators_summary']}, Medias: {row['moving_averages_summary']}). "
                   f"Precio: {row['price']}\n")
    report += "\nSe adjuntan gráficos de distribución de recomendaciones y precios de activos.\n\n"

    # Preparar prompt para la API de Deepseek r1
    prompt = (
        "Eres un analista financiero experimentado. Con base en los siguientes datos diarios, "
        "genera un reporte que incluya:\n"
        " - El estado general del mercado.\n"
        " - Recomendaciones claras de compra y venta para el día.\n"
        " - Análisis de tendencias y factores técnicos (considerando indicadores, medias móviles, RSI, MACD, etc.).\n"
        " - Comentarios sobre los gráficos adjuntos (distribución de recomendaciones y precios de cierre).\n\n"
        "Datos:\n" + report +
        "\nEl reporte debe ser conciso, claro y útil para tomar decisiones de inversión diaria."
    )

    # Your cookie values
    cookies = {
        "x-anonuserid": "b4507c57-a948-482e-8136-780c5c84a0b1",
        "x-challenge": "DihL68ZFtBXalCC%2BULwZ%2BmrOQUb7AsS9zTGaDRAv3JpysrX3QnBbllKCCP741TacDN09kDe61LdxQSKeTQahXPTMCuCnRCXE6hB62DzHaaN4yXRiYNeo4jwHqpux7Qzj4i93uDtacIOXO8BUFeI2ATSGFqhmrJM%2Bm8O5uYkhDY%2BwM%2Bq%2Fnbc%3D",
        "x-signature": "Pn6TTqRTbqXG62zgbNvdS96GPeeZZU%2Fbi98NTNif5IISJVrtdmkirXD%2FugJntQ13YPori3lrt8TOPiB7fKEitQ%3D%3D",
        "sso": "eyJhbGciOiJIUzI1NiJ9.eyJzZXNzaW9uX2lkIjoiMjRmZDc5YzQtZGFjNi00MGI0LWFjZGMtNzJiMGNhMWFlNGE4In0.oitDPbuVQHr8dfcH7zW-VFRLPMMlafpMxLpx1G49Xes",
        "sso-rw": "eyJhbGciOiJIUzI1NiJ9.eyJzZXNzaW9uX2lkIjoiMjRmZDc5YzQtZGFjNi00MGI0LWFjZGMtNzJiMGNhMWFlNGE4In0.oitDPbuVQHr8dfcH7zW-VFRLPMMlafpMxLpx1G49Xes"
    }

    # Initialize the client
    client = GrokClient(cookies)

    # Send a message and get response
    response = client.send_message(prompt)
    print(f"Reporte: {response}")
    
    final_report = response
    return final_report

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
    daily_report = generate_daily_report(df, charts)

    # Mostrar y guardar el reporte
    print(daily_report)
    with open("reporte_diario.txt", "w", encoding="utf-8") as f:
        f.write(daily_report)
    print("Reporte guardado en 'reporte_diario.txt'.")

if __name__ == "__main__":
    main()

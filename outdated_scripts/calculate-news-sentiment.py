import psycopg2
from nltk.sentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
import nltk

# Descargar diccionario de VADER (solo la primera vez)
nltk.download("vader_lexicon")

# Conectar a la base de datos
DB_URL = "postgresql://postgres:@localhost:5432/stocks_db"
conn = psycopg2.connect(DB_URL)
cursor = conn.cursor()

# Inicializar el analizador de sentimiento de VADER
sia = SentimentIntensityAnalyzer()

# Obtener noticias desde la base de datos
cursor.execute("SELECT id, title, link FROM news WHERE sentiment IS NULL")
noticias = cursor.fetchall()

for noticia in noticias:
    noticia_id, titulo, enlace = noticia
    
    if titulo:
        # Obtener puntaje de sentimiento con VADER
        vader_score = sia.polarity_scores(titulo)["compound"]
        
        # Obtener polaridad con TextBlob
        textblob_score = TextBlob(titulo).sentiment.polarity

        # Guardar el promedio de ambos métodos
        sentiment = (vader_score + textblob_score) / 2

        # Actualizar la noticia con el sentimiento calculado
        cursor.execute("UPDATE news SET sentiment = %s WHERE id = %s", (sentiment, noticia_id))
        conn.commit()
        print(f"📌 {titulo} -> Sentimiento: {sentiment:.2f}")

# Cerrar conexión
cursor.close()
conn.close()

print("✅ Análisis de sentimiento completado y guardado en la base de datos.")

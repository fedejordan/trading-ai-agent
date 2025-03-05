#!/usr/bin/env python3
from datetime import datetime, date
import os
import tweepy

# Cargar variables de entorno desde el archivo .env
from dotenv import load_dotenv
load_dotenv()


TWITTER_CONFIG = {
    "api_key": os.getenv("TWITTER_API_KEY"),
    "api_secret_key": os.getenv("TWITTER_API_SECRET_KEY"),
    "access_token": os.getenv("TWITTER_ACCESS_TOKEN"),
    "access_token_secret": os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
}

###############################################
# FUNCIONES PARA PUBLICAR TWEETS
###############################################
def post_tweet(message):
    auth = tweepy.OAuthHandler(TWITTER_CONFIG["api_key"], TWITTER_CONFIG["api_secret_key"])
    auth.set_access_token(TWITTER_CONFIG["access_token"], TWITTER_CONFIG["access_token_secret"])
    api = tweepy.API(auth)
    try:
        api.update_status(message)
        print("Tweet publicado exitosamente.")
    except Exception as e:
        print(f"Error al publicar el tweet: {e}")
        
if __name__ == "__main__":
    # Publicar tweet tras completar el proceso
    tweet_message = f"Reporte Diario de Mercados generado para {datetime.now().strftime('%Y-%m-%d')}. Revisa tu correo para más detalles."
    post_tweet(tweet_message)
import os
import mysql.connector
from dotenv import load_dotenv

#Carico le variabili d'ambiente dal file .env
load_dotenv()


def creaConnessione():
    connessione = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

    return connessione
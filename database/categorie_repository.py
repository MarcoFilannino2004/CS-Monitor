import mysql.connector
from database.connessione import creaConnessione


def visualizzaCategorie():
    connessione = None
    cursore = None

    try:
        connessione = creaConnessione()
        cursore = connessione.cursor(dictionary=True)

        query = "SELECT id_categoria, nome FROM categorie ORDER BY nome"

        cursore.execute(query)
        return cursore.fetchall()

    except mysql.connector.Error as errore:
        print(f"Errore durante la lettura delle categorie: {errore}")
        raise

    finally:
        if cursore is not None:
            cursore.close()
        if connessione is not None and connessione.is_connected():
            connessione.close()
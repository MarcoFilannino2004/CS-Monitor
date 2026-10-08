from database.connessione import creaConnessione
import mysql.connector

connessione = None
cursore = None

try:
    connessione = creaConnessione()
    cursore = connessione.cursor(dictionary=True)

    print("Connessione a MySQL riuscita!")

    query = """
        SELECT e.id_evento, c.nome AS categoria, e.indirizzo_ip,
               e.descrizione, e.gravita, e.stato, e.data_evento
        FROM eventi e
        JOIN categorie c ON e.id_categoria = c.id_categoria
        ORDER BY e.id_evento
    """

    cursore.execute(query)
    eventi = cursore.fetchall()

    for evento in eventi:
        print(f"{evento['id_evento']} | {evento['categoria']} | {evento['indirizzo_ip']} | {evento['gravita']} | {evento['stato']}")

except mysql.connector.Error as errore:
    print(f"Errore MySQL: {errore}")

finally:
    if cursore is not None:
        cursore.close()

    if connessione is not None and connessione.is_connected():
        connessione.close()
        print("Connessione chiusa.")
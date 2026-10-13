
import mysql.connector
from database.connessione import creaConnessione
from models.evento_sicurezza import EventoSicurezza


# CREATE
def inserisciEvento(evento: EventoSicurezza, id_utente=None):
    connessione = None
    cursore = None

    try:
        connessione = creaConnessione()
        cursore = connessione.cursor()

        query = """
            INSERT INTO eventi (id_categoria, indirizzo_ip, descrizione, gravita, stato, data_evento, id_utente)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        valori = (evento.id_categoria, evento.indirizzo_ip, evento.descrizione, evento.gravita, evento.stato, evento.data_evento, id_utente)

        cursore.execute(query, valori)
        connessione.commit()

        evento.id_evento = cursore.lastrowid
        return evento.id_evento

    except mysql.connector.Error as errore:
        if connessione is not None:
            connessione.rollback()
        print(f"Errore durante l'inserimento: {errore}")
        raise

    finally:
        if cursore is not None:
            cursore.close()
        if connessione is not None and connessione.is_connected():
            connessione.close()


def inserisciEventi(eventi):
    """Salva l'intera importazione in una transazione."""
    connessione = None
    cursore = None
    try:
        connessione = creaConnessione()
        cursore = connessione.cursor()
        cursore.executemany(
            """INSERT INTO eventi
               (id_categoria, indirizzo_ip, descrizione, gravita, stato, data_evento)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            [(e.id_categoria, e.indirizzo_ip, e.descrizione, e.gravita, e.stato, e.data_evento)
             for e in eventi],
        )
        connessione.commit()
    except mysql.connector.Error:
        if connessione is not None:
            connessione.rollback()
        raise
    finally:
        if cursore is not None:
            cursore.close()
        if connessione is not None and connessione.is_connected():
            connessione.close()


# READ - Tutti gli eventi
def visualizzaEventi(gravita=None, stato=None, ordine="recenti", testo=None, id_utente=None, amministratore=False, id_importazione=None):
    connessione = None
    cursore = None

    try:
        connessione = creaConnessione()
        cursore = connessione.cursor(dictionary=True)

        query = """
            SELECT e.id_evento, e.id_categoria, c.nome AS categoria,
                   e.indirizzo_ip, e.descrizione, e.gravita, e.stato, e.data_evento, e.id_utente, e.id_importazione, u.username AS autore
            FROM eventi e
            JOIN categorie c ON e.id_categoria = c.id_categoria
            LEFT JOIN utenti u ON e.id_utente = u.id_utente
            WHERE 1=1
        """

        valori = []
        if not amministratore:
            query += " AND e.id_utente = %s"
            valori.append(id_utente)
        if id_importazione is not None:
            query += " AND e.id_importazione = %s"
            valori.append(id_importazione)

        if testo:
            if testo.isascii() and testo.isdecimal():
                cifre = testo.lstrip("0") or "0"
                if len(cifre) <= 20 and int(cifre) <= 18446744073709551615:
                    query += " AND e.id_evento = %s"
                    valori.append(int(cifre))
                else:
                    query += " AND 1=0"
            else:
                query += " AND (e.indirizzo_ip LIKE %s OR e.descrizione LIKE %s)"
                valori.extend([f"%{testo}%", f"%{testo}%"])

        if gravita:
            query += " AND e.gravita = %s"
            valori.append(gravita)

        if stato:
            query += " AND e.stato = %s"
            valori.append(stato)

        if ordine == "vecchi":
            query += " ORDER BY e.data_evento ASC, e.id_evento ASC"
        else:
            query += " ORDER BY e.data_evento DESC, e.id_evento DESC"

        cursore.execute(query, tuple(valori))
        return cursore.fetchall()

    except mysql.connector.Error as errore:
        print(f"Errore durante la lettura: {errore}")
        raise

    finally:
        if cursore is not None:
            cursore.close()
        if connessione is not None and connessione.is_connected():
            connessione.close()


# READ - Singolo evento
def cercaEvento(id_evento: int, id_utente=None, amministratore=False):
    connessione = None
    cursore = None

    try:
        connessione = creaConnessione()
        cursore = connessione.cursor(dictionary=True)

        query = """
            SELECT e.id_evento, e.id_categoria, c.nome AS categoria,
                   e.indirizzo_ip, e.descrizione, e.gravita, e.stato, e.data_evento, e.id_utente, e.id_importazione, u.username AS autore
            FROM eventi e
            JOIN categorie c ON e.id_categoria = c.id_categoria
            LEFT JOIN utenti u ON e.id_utente = u.id_utente
            WHERE e.id_evento = %s
        """

        valori = (id_evento,)
        if not amministratore:
            query += " AND e.id_utente = %s"
            valori += (id_utente,)
        cursore.execute(query, valori)
        return cursore.fetchone()

    except mysql.connector.Error as errore:
        print(f"Errore durante la ricerca: {errore}")
        raise

    finally:
        if cursore is not None:
            cursore.close()
        if connessione is not None and connessione.is_connected():
            connessione.close()


# UPDATE
def modificaEvento(evento: EventoSicurezza, id_utente=None, amministratore=False):
    if evento.id_evento is None:
        raise ValueError("Impossibile modificare un evento senza ID.")

    connessione = None
    cursore = None

    try:
        connessione = creaConnessione()
        cursore = connessione.cursor()

        query = """
            UPDATE eventi
            SET id_categoria = %s, indirizzo_ip = %s, descrizione = %s,
                gravita = %s, stato = %s
            WHERE id_evento = %s
        """

        valori = (evento.id_categoria, evento.indirizzo_ip, evento.descrizione, evento.gravita, evento.stato, evento.id_evento)

        if not amministratore:
            query += " AND id_utente = %s"
            valori += (id_utente,)
        cursore.execute(query, valori)
        righe_modificate = cursore.rowcount
        connessione.commit()

        return righe_modificate > 0

    except mysql.connector.Error as errore:
        if connessione is not None:
            connessione.rollback()
        print(f"Errore durante la modifica: {errore}")
        raise

    finally:
        if cursore is not None:
            cursore.close()
        if connessione is not None and connessione.is_connected():
            connessione.close()


# DELETE
def eliminaEvento(id_evento: int, id_utente=None, amministratore=False):
    if type(id_evento) is not int or id_evento <= 0:
        raise ValueError("L'ID dell'evento deve essere un intero positivo.")

    connessione = None
    cursore = None

    try:
        connessione = creaConnessione()
        cursore = connessione.cursor()

        query = "DELETE FROM eventi WHERE id_evento = %s"

        valori = (id_evento,)
        if not amministratore:
            query += " AND id_utente = %s"
            valori += (id_utente,)
        cursore.execute(query, valori)
        righe_eliminate = cursore.rowcount
        connessione.commit()

        return righe_eliminate > 0

    except mysql.connector.Error as errore:
        if connessione is not None:
            connessione.rollback()
        print(f"Errore durante l'eliminazione: {errore}")
        raise

    finally:
        if cursore is not None:
            cursore.close()
        if connessione is not None and connessione.is_connected():
            connessione.close()

def statisticheEventi(id_utente=None, amministratore=False):
    connessione = creaConnessione()
    cursore = connessione.cursor(dictionary=True)

    try:
        query = """
            SELECT
                COUNT(*) AS totale,
                SUM(CASE WHEN gravita = 'Critica' THEN 1 ELSE 0 END) AS critici,
                SUM(CASE WHEN stato = 'Nuovo' THEN 1 ELSE 0 END) AS nuovi,
                SUM(CASE WHEN stato = 'Risolto' THEN 1 ELSE 0 END) AS risolti
            FROM eventi
        """

        valori = ()
        if not amministratore:
            query += " WHERE id_utente = %s"
            valori = (id_utente,)
        cursore.execute(query, valori)
        statistiche = cursore.fetchone()

        return statistiche

    finally:
        cursore.close()
        connessione.close()


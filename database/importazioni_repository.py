import mysql.connector
from database.strumenti import apriCursore


def salvaImportazione(eventi, id_utente, nome_file, contenuto, righe_valide, righe_errate, token):
    """Registra file e tutti gli eventi nella stessa transazione; token evita doppi invii."""
    try:
        with apriCursore() as (connessione, cursore):
            cursore.execute(
                '''INSERT INTO importazioni (id_utente, token_importazione, nome_file,
                contenuto, dimensione, righe_valide, righe_errate, eventi_importati)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)''',
                (
                    id_utente,
                    token,
                    nome_file,
                    contenuto,
                    len(contenuto),
                    righe_valide,
                    righe_errate,
                    len(eventi),
                ),
            )
            id_importazione = cursore.lastrowid
            cursore.executemany(
                '''INSERT INTO eventi (id_categoria, indirizzo_ip, descrizione,
                gravita, stato, data_evento, id_utente, id_importazione) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)''',
                [
                    (
                        e.id_categoria,
                        e.indirizzo_ip,
                        e.descrizione,
                        e.gravita,
                        e.stato,
                        e.data_evento,
                        id_utente,
                        id_importazione,
                    )
                    for e in eventi
                ],
            )
            connessione.commit()
            return id_importazione
    except mysql.connector.IntegrityError as errore:
        if errore.errno == 1062:
            raise ValueError(
                'Questo file è già stato importato da questa anteprima. Consulta lo storico.'
            ) from None
        raise


def visualizzaImportazioni(id_utente, amministratore=False):
    with apriCursore(True) as (_, cursore):
        query = '''SELECT i.id_importazione, i.id_utente, i.nome_file, i.dimensione,
            i.righe_valide, i.righe_errate, i.eventi_importati, i.data_importazione,
            u.username, (SELECT COUNT(*) FROM eventi e WHERE e.id_importazione=i.id_importazione) AS eventi_attuali
            FROM importazioni i JOIN utenti u ON i.id_utente=u.id_utente'''
        if not amministratore:
            query += ' WHERE i.id_utente=%s'
        cursore.execute(
            query + ' ORDER BY i.data_importazione DESC, i.id_importazione DESC',
            () if amministratore else (id_utente,),
        )
        return cursore.fetchall()


def cercaImportazione(id_importazione, id_utente, amministratore=False):
    with apriCursore(True) as (_, cursore):
        query = '''SELECT i.*, u.username FROM importazioni i JOIN utenti u ON i.id_utente=u.id_utente
            WHERE i.id_importazione=%s'''
        valori = [id_importazione]
        if not amministratore:
            query += ' AND i.id_utente=%s'
            valori.append(id_utente)
        cursore.execute(query, tuple(valori))
        return cursore.fetchone()

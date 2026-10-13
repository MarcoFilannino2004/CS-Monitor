from contextlib import contextmanager
from database.connessione import creaConnessione


@contextmanager
def apriCursore(dizionario=False):
    connessione = creaConnessione()
    cursore = None
    try:
        cursore = connessione.cursor(dictionary=dizionario)
        yield connessione, cursore
    except Exception:
        connessione.rollback()
        raise
    finally:
        if cursore is not None:
            cursore.close()
        connessione.close()

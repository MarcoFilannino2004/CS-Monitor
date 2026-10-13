from datetime import datetime, timedelta
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from database.strumenti import apriCursore
from services.account import validaAccount, validaPassword

# Un hash fittizio rende simile il controllo quando l'account non esiste.
HASH_FITTIZIO = generate_password_hash('account-inesistente-non-usare')


def cercaUtente(id_utente):
    with apriCursore(True) as (_, cursore):
        cursore.execute('SELECT * FROM utenti WHERE id_utente=%s', (id_utente,))
        return cursore.fetchone()


def creaUtente(
    username, email, password, ruolo='utente', assegna_precedenti=False, cambio_password=False
):
    validaPassword(password)
    username, email = validaAccount(username, email, password)
    if ruolo not in ('utente', 'admin'):
        raise ValueError('Ruolo non valido.')
    try:
        with apriCursore() as (connessione, cursore):
            cursore.execute(
                'INSERT INTO utenti (username, email, password_hash, ruolo, password_da_cambiare) VALUES (%s,%s,%s,%s,%s)',
                (username, email, generate_password_hash(password), ruolo, cambio_password),
            )
            id_utente = cursore.lastrowid
            if assegna_precedenti and ruolo == 'admin':
                cursore.execute(
                    'UPDATE eventi SET id_utente=%s WHERE id_utente IS NULL', (id_utente,)
                )
            connessione.commit()
            return id_utente
    except mysql.connector.IntegrityError as errore:
        if errore.errno == 1062:
            raise ValueError('Nome utente o email già utilizzati.') from None
        raise


def autenticaUtente(identificativo, password):
    identificativo = (identificativo or '').strip()
    if len(identificativo) > 254 or not isinstance(password, str) or len(password) > 128:
        return None
    with apriCursore(True) as (connessione, cursore):
        cursore.execute(
            'SELECT * FROM utenti WHERE username=%s OR email=%s FOR UPDATE',
            (identificativo, identificativo.lower()),
        )
        utente = cursore.fetchone()
        corretta = check_password_hash(
            utente['password_hash'] if utente else HASH_FITTIZIO, password
        )
        adesso = datetime.now()
        if (
            not utente
            or not utente['attivo']
            or (utente['bloccato_fino'] and utente['bloccato_fino'] > adesso)
        ):
            return None
        if not corretta:
            tentativi = (utente['tentativi_login'] if utente['bloccato_fino'] is None else 0) + 1
            blocco = adesso + timedelta(minutes=15) if tentativi >= 5 else None
            cursore.execute(
                'UPDATE utenti SET tentativi_login=%s, bloccato_fino=%s WHERE id_utente=%s',
                (tentativi, blocco, utente['id_utente']),
            )
            connessione.commit()
            return None
        cursore.execute(
            'UPDATE utenti SET tentativi_login=0, bloccato_fino=NULL, ultimo_accesso=%s WHERE id_utente=%s',
            (adesso, utente['id_utente']),
        )
        connessione.commit()
        return utente


def aggiornaProfilo(id_utente, username, email):
    username, email = validaAccount(username, email)
    try:
        with apriCursore() as (connessione, cursore):
            cursore.execute(
                'UPDATE utenti SET username=%s, email=%s WHERE id_utente=%s',
                (username, email, id_utente),
            )
            connessione.commit()
    except mysql.connector.IntegrityError as errore:
        if errore.errno == 1062:
            raise ValueError('Nome utente o email già utilizzati.') from None
        raise


def cambiaPassword(id_utente, attuale, nuova):
    from services.account import validaPassword

    validaPassword(nuova)
    with apriCursore(True) as (connessione, cursore):
        cursore.execute(
            'SELECT password_hash FROM utenti WHERE id_utente=%s FOR UPDATE', (id_utente,)
        )
        utente = cursore.fetchone()
        if not utente or not check_password_hash(utente['password_hash'], attuale):
            raise ValueError('La password attuale non è corretta.')
        cursore.execute(
            'UPDATE utenti SET password_hash=%s, password_da_cambiare=0, versione_sessione=versione_sessione+1 WHERE id_utente=%s',
            (generate_password_hash(nuova), id_utente),
        )
        connessione.commit()


def reimpostaPassword(id_utente, amministratore, nuova):
    from services.account import validaPassword

    validaPassword(nuova)
    if id_utente == amministratore:
        raise ValueError('Per la tua password usa la pagina Il mio account.')
    with apriCursore(True) as (connessione, cursore):
        cursore.execute('SELECT id_utente FROM utenti WHERE id_utente=%s FOR UPDATE', (id_utente,))
        if not cursore.fetchone():
            raise ValueError('Account non trovato.')
        cursore.execute(
            '''UPDATE utenti SET password_hash=%s, password_da_cambiare=1,
            versione_sessione=versione_sessione+1, tentativi_login=0, bloccato_fino=NULL
            WHERE id_utente=%s''',
            (generate_password_hash(nuova), id_utente),
        )
        connessione.commit()


def visualizzaUtenti():
    with apriCursore(True) as (_, cursore):
        cursore.execute('''SELECT u.id_utente, u.username, u.email, u.ruolo, u.attivo,
            u.data_creazione, u.ultimo_accesso,
            (SELECT COUNT(*) FROM eventi e WHERE e.id_utente=u.id_utente) AS eventi,
            (SELECT COUNT(*) FROM importazioni i WHERE i.id_utente=u.id_utente) AS importazioni
            FROM utenti u ORDER BY u.data_creazione DESC, u.id_utente DESC''')
        return cursore.fetchall()


def gestisciUtente(id_utente, amministratore, ruolo, attivo):
    if ruolo not in ('utente', 'admin'):
        raise ValueError('Ruolo non valido.')
    with apriCursore(True) as (connessione, cursore):
        # Blocca gli amministratori nello stesso ordine per proteggere l'ultimo attivo.
        cursore.execute(
            "SELECT id_utente FROM utenti WHERE ruolo='admin' AND attivo=1 ORDER BY id_utente FOR UPDATE"
        )
        admin_attivi = {u['id_utente'] for u in cursore.fetchall()}
        cursore.execute('SELECT * FROM utenti WHERE id_utente=%s FOR UPDATE', (id_utente,))
        utente = cursore.fetchone()
        if not utente:
            raise ValueError('Account non trovato.')
        if id_utente == amministratore and (not attivo or ruolo != 'admin'):
            raise ValueError(
                'Non puoi disattivare il tuo account o rimuovere il tuo ruolo amministratore.'
            )
        if (
            id_utente in admin_attivi
            and len(admin_attivi) == 1
            and (not attivo or ruolo != 'admin')
        ):
            raise ValueError('Deve restare almeno un amministratore attivo.')
        cursore.execute(
            'UPDATE utenti SET ruolo=%s, attivo=%s, versione_sessione=versione_sessione+1, tentativi_login=0, bloccato_fino=NULL WHERE id_utente=%s',
            (ruolo, bool(attivo), id_utente),
        )
        connessione.commit()

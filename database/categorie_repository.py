import mysql.connector
from database.connessione import creaConnessione
from database.strumenti import apriCursore


CATEGORIE_PREDEFINITE = (
    'Autenticazione e accessi', 'Tentativi di forza bruta', 'Account bloccati',
    'Accessi non autorizzati', 'Permessi e privilegi', 'Gestione delle sessioni',
    'Firewall e traffico bloccato', 'Scansione delle porte', 'Traffico di rete anomalo',
    'Attacchi DoS e DDoS', 'Connessioni VPN', 'Errori DNS', 'Certificati e connessioni TLS',
    'Malware e antivirus', 'Ransomware', 'Phishing e posta sospetta',
    'File sospetti e quarantena', 'Integrità dei file', 'Esfiltrazione dei dati',
    'Errori applicativi', 'Errori del database', 'Servizi non disponibili',
    'Errori del sistema operativo', 'Spazio disco e archiviazione',
    'Prestazioni e risorse', 'Backup e ripristino', 'Aggiornamenti di sicurezza',
    'Configurazioni non autorizzate', 'Dispositivi e hardware', 'Monitoraggio e audit',
)


def aggiungiCategoriePredefinite():
    """Aggiunge soltanto i nomi mancanti, mantenendo categorie e ID esistenti."""
    with apriCursore() as (connessione, cursore):
        cursore.execute('SELECT nome FROM categorie FOR UPDATE')
        esistenti = {riga[0].strip().casefold() for riga in cursore.fetchall()}
        nuove = [(nome,) for nome in CATEGORIE_PREDEFINITE if nome.casefold() not in esistenti]
        if nuove:
            cursore.executemany('INSERT INTO categorie (nome) VALUES (%s)', nuove)
        connessione.commit()
        return len(nuove)


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

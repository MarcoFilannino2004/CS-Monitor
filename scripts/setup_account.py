"""Migrazione esplicita: preserva gli eventi e crea il primo amministratore."""
import sys
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / '.env')
from database.migrazioni import preparaAccount
from database.strumenti import apriCursore
from database.utenti_repository import creaUtente
from database.categorie_repository import aggiungiCategoriePredefinite


def main():
    import argparse
    import os
    parser = argparse.ArgumentParser(description='Prepara gli account di CS Monitor.')
    parser.add_argument('--username', default='admin')
    parser.add_argument('--email', required=True)
    args = parser.parse_args()
    preparaAccount()
    aggiunte = aggiungiCategoriePredefinite()
    print(f'Categorie di sicurezza aggiornate: {aggiunte} nuove categorie.')
    # Una chiave stabile evita di scollegare tutti a ogni riavvio.
    if not os.getenv('SECRET_KEY'):
        with (ROOT / '.env').open('a', encoding='utf-8') as file:
            file.write('\nSECRET_KEY=' + secrets.token_hex(32) + '\n')
    with apriCursore(True) as (_, cursore):
        cursore.execute("SELECT id_utente FROM utenti WHERE ruolo='admin' AND attivo=1")
        if cursore.fetchall():
            print('Database aggiornato. Un amministratore attivo esiste già: nessuna credenziale modificata.')
            return
    password = secrets.token_urlsafe(24)
    # Scrive le credenziali prima della creazione, senza sovrascrivere credenziali precedenti.
    destinazione = ROOT / 'instance' / 'credenziali-admin.txt'
    destinazione.parent.mkdir(exist_ok=True)
    with destinazione.open('x', encoding='utf-8') as file:
        file.write(f'CS Monitor - primo amministratore\nUsername: {args.username}\nEmail: {args.email}\nPassword: {password}\n\nCambia la password dopo il primo accesso dalla pagina del tuo account.\n')
    creaUtente(args.username, args.email, password, ruolo='admin', assegna_precedenti=True, cambio_password=True)
    print('Database aggiornato. Amministratore creato. Credenziali in instance/credenziali-admin.txt (escluso da Git).')


if __name__ == '__main__':
    main()

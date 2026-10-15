from database.strumenti import apriCursore


def preparaAccount():
    """Aggiunge tabelle e collegamenti, conservando gli eventi preesistenti."""
    with apriCursore() as (connessione, cursore):
        cursore.execute("""CREATE TABLE IF NOT EXISTS utenti (
            id_utente INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(40) NOT NULL UNIQUE,
            email VARCHAR(254) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            ruolo ENUM('utente', 'admin') NOT NULL DEFAULT 'utente',
            attivo BOOLEAN NOT NULL DEFAULT TRUE,
            versione_sessione INT NOT NULL DEFAULT 0,
            tentativi_login INT NOT NULL DEFAULT 0,
            bloccato_fino DATETIME NULL,
            data_creazione DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ultimo_accesso DATETIME NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        cursore.execute('SHOW COLUMNS FROM utenti')
        colonne_utenti = {c[0] for c in cursore.fetchall()}
        if 'password_da_cambiare' not in colonne_utenti:
            cursore.execute(
                'ALTER TABLE utenti ADD COLUMN password_da_cambiare BOOLEAN NOT NULL DEFAULT FALSE'
            )
        cursore.execute("""CREATE TABLE IF NOT EXISTS importazioni (
            id_importazione INT AUTO_INCREMENT PRIMARY KEY,
            id_utente INT NOT NULL,
            token_importazione VARCHAR(64) NOT NULL UNIQUE,
            nome_file VARCHAR(255) NOT NULL,
            contenuto MEDIUMBLOB NOT NULL,
            dimensione INT NOT NULL,
            righe_valide INT NOT NULL,
            righe_errate INT NOT NULL,
            eventi_importati INT NOT NULL,
            data_importazione DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_utente) REFERENCES utenti(id_utente),
            INDEX (id_utente, data_importazione)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        cursore.execute("SHOW COLUMNS FROM eventi")
        colonne = {c[0] for c in cursore.fetchall()}
        if 'id_utente' not in colonne:
            cursore.execute(
                "ALTER TABLE eventi ADD COLUMN id_utente INT NULL, ADD CONSTRAINT fk_eventi_utente FOREIGN KEY (id_utente) REFERENCES utenti(id_utente), ADD INDEX idx_eventi_utente (id_utente)"
            )
        if 'id_importazione' not in colonne:
            cursore.execute(
                "ALTER TABLE eventi ADD COLUMN id_importazione INT NULL, ADD CONSTRAINT fk_eventi_importazione FOREIGN KEY (id_importazione) REFERENCES importazioni(id_importazione), ADD INDEX idx_eventi_importazione (id_importazione)"
            )
        connessione.commit()
    preparaRegistroAttivita()


def preparaRegistroAttivita():
    """Crea il registro indipendente dagli eventi, conservando la cronologia."""
    with apriCursore() as (connessione, cursore):
        cursore.execute("""CREATE TABLE IF NOT EXISTS registro_attivita (
            id_attivita BIGINT AUTO_INCREMENT PRIMARY KEY,
            data_attivita DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            id_utente INT NULL,
            username VARCHAR(40) NOT NULL,
            indirizzo_ip VARCHAR(45) NULL,
            azione VARCHAR(64) NOT NULL,
            esito ENUM('Riuscito', 'Fallito', 'Negato') NOT NULL,
            risorsa VARCHAR(100) NOT NULL,
            dettagli VARCHAR(500) NOT NULL,
            metodo VARCHAR(10) NOT NULL,
            percorso VARCHAR(255) NOT NULL,
            codice_http SMALLINT NOT NULL,
            INDEX idx_registro_data (data_attivita, id_attivita),
            INDEX idx_registro_utente (id_utente),
            INDEX idx_registro_azione (azione, esito)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        connessione.commit()

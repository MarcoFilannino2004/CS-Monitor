# CS Monitor

**Gestione degli eventi di sicurezza informatica con Python, Flask e MySQL.**

CS Monitor è un'applicazione web che permette di registrare eventi di sicurezza, consultarli in una dashboard e seguirne lo stato di analisi. Gli eventi possono essere inseriti manualmente oppure importati da un file di log.

Il progetto nasce come lavoro finale del corso di sviluppo Python ed è ispirato alle attività di un **Security Operations Center (SOC)**: un gruppo che si occupa di monitorare e gestire gli eventi di sicurezza informatica.

**Autore:** Marco Filannino — Studente di Ingegneria Informatica e dell'Automazione presso il Politecnico di Bari.

## Indice

- [Funzionalità](#funzionalità)
- [Come funziona](#come-funziona)
- [Tecnologie](#tecnologie)
- [Installazione e avvio](#installazione-e-avvio)
- [Guida all'utilizzo](#guida-allutilizzo)
- [Importazione dei log](#importazione-dei-log)
- [Struttura del progetto](#struttura-del-progetto)
- [Database](#database)
- [Test e verifiche](#test-e-verifiche)
- [Come presentare il progetto](#come-presentare-il-progetto)
- [Limiti e sviluppi futuri](#limiti-e-sviluppi-futuri)
- [Contatti](#contatti)

## Funzionalità

| Funzione | Cosa permette di fare |
|---|---|
| Inserimento manuale | Registrare un evento indicando categoria, IP, descrizione e gravità. |
| Dashboard | Consultare gli eventi e il riepilogo di totali, critici, nuovi e risolti. |
| Ricerca | Cercare per ID oppure per testo nell'IP e nella descrizione. |
| Filtri e ordinamento | Filtrare per gravità e stato, ordinando dal più recente o dal più vecchio. |
| Dettagli e modifica | Consultare un evento e aggiornare i suoi dati o il suo stato. |
| Eliminazione | Rimuovere un evento dal database. |
| Importazione dei log | Analizzare un file e assegnare una categoria a ogni evento selezionato nell'anteprima. |
| Esportazione CSV | Scaricare gli eventi rispettando i filtri e l'ordinamento applicati. |

L'interfaccia si adatta alle dimensioni dello schermo e include una pagina di informazioni sul progetto e sullo sviluppatore.

## Come funziona

Il percorso di un evento inserito manualmente è questo:

```text
L'utente compila il modulo nel browser
                  ↓
Flask riceve i dati
                  ↓
EventoSicurezza controlla che siano validi
                  ↓
Il repository esegue l'inserimento SQL
                  ↓
MySQL conserva l'evento
                  ↓
La dashboard mostra l'evento e la conferma di salvataggio
```

Il codice separa le responsabilità in quattro parti:

- **Interfaccia:** le pagine HTML mostrano i dati e raccolgono le scelte dell'utente.
- **Applicazione:** Flask decide cosa fare quando viene aperta una pagina o inviato un modulo.
- **Modelli e servizi:** le classi controllano i dati; il servizio di importazione interpreta i log.
- **Accesso ai dati:** i repository eseguono le query e gestiscono le connessioni a MySQL.

Questa divisione rende più semplice capire dove intervenire: per cambiare l'aspetto si modificano HTML e CSS; per cambiare una query si interviene nel repository.

## Tecnologie

| Tecnologia | Ruolo nel progetto |
|---|---|
| Python | Logica applicativa, classi, validazione e analisi dei log. |
| Flask | Gestione delle pagine e delle richieste web. |
| MySQL e SQL | Memorizzazione dei dati e operazioni sul database. |
| HTML e CSS | Struttura e stile delle pagine. |
| JavaScript | Nome del file scelto e gestione dei menu categoria nell'anteprima. |
| Bootstrap 5 e Bootstrap Icons | Layout adattabile, componenti grafici e icone. |
| Jinja2 | Generazione delle pagine HTML con i dati ricevuti da Flask. |
| Git | Gestione delle versioni del progetto. |

Le dipendenze Python sono elencate in [`requirements.txt`](requirements.txt). `mysql-connector-python` collega Python a MySQL, `python-dotenv` legge il file `.env` e `ItsDangerous` firma i dati dell'anteprima dei log.

Sono utilizzati anche moduli inclusi in Python: `ipaddress` per verificare gli IP, `datetime` per le date, `re` per interpretare i log, `csv` per l'esportazione e `unittest` per i test automatici.

## Installazione e avvio

### 1. Prerequisiti

- Python 3.10 o successivo; i test dell'importazione sono stati eseguiti con Python 3.12.
- Un server MySQL avviato e un utente con accesso al database del progetto.
- Connessione Internet per installare le dipendenze e caricare Bootstrap e le icone dai CDN.

I comandi seguenti sono pensati per **Windows PowerShell**, eseguiti dalla cartella del progetto.

### 2. Prepara l'ambiente Python

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Se `.venv` esiste già, basta attivarlo e installare le dipendenze mancanti. Quando è attivo, nel terminale compare `(.venv)`.

Se PowerShell impedisce l'attivazione, puoi utilizzare direttamente l'interprete dell'ambiente:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Prepara MySQL

L'applicazione richiede le tabelle `categorie` ed `eventi` e almeno una categoria disponibile. Non le crea automaticamente all'avvio.

Se hai già il database configurato, usa quello esistente. Per un'installazione nuova, trovi uno schema SQL compatibile nella [sezione Database](#database).

### 4. Configura il file `.env`

Crea un file `.env` nella cartella principale e inserisci i tuoi valori:

```dotenv
DB_HOST=localhost
DB_PORT=3306
DB_USER=tuo_utente_mysql
DB_PASSWORD=tua_password_mysql
DB_NAME=cybersec_monitor
SECRET_KEY=incolla_qui_una_chiave_casuale
```

Per generare la chiave da copiare in `SECRET_KEY`:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

`SECRET_KEY` viene utilizzata per i messaggi di conferma e la firma delle anteprime. Senza una chiave configurata, l'app ne genera una nuova a ogni avvio: le anteprime precedenti diventano quindi non valide.

Il file `.env` è escluso da Git tramite `.gitignore`, perché contiene credenziali personali.

### 5. Avvia l'applicazione

```powershell
python app.py
```

Oppure, senza attivare l'ambiente:

```powershell
.\.venv\Scripts\python.exe app.py
```

Apri [http://127.0.0.1:5000](http://127.0.0.1:5000) nel browser. Per fermare l'applicazione, premi `Ctrl+C` nel terminale.

L'avvio tramite `app.py` utilizza la modalità debug di Flask, adatta allo sviluppo locale.

## Guida all'utilizzo

### Registra e gestisci un evento

1. Apri **Nuovo evento** dal menu.
2. Seleziona una categoria e inserisci IP, descrizione e gravità.
3. Invia il modulo: l'evento viene creato con stato **Nuovo** e con la data e l'ora correnti dell'applicazione.
4. Nella dashboard compare **Evento aggiunto correttamente.**
5. Apri **Dettagli** per consultare l'evento, modificarlo o eliminarlo.

La gravità può essere **Bassa**, **Media**, **Alta** o **Critica**. Lo stato può essere **Nuovo**, **In analisi** o **Risolto**.

Gli stati descrivono l'avanzamento del lavoro; il programma non impone un ordine obbligatorio tra loro.

### Cerca ed esporta gli eventi

Nella dashboard puoi combinare ricerca, gravità, stato e ordinamento. Una ricerca composta soltanto dalle cifre 0–9 viene interpretata come ID esatto; gli altri testi vengono cercati nell'IP e nella descrizione.

Le statistiche in alto riguardano **tutti gli eventi del database**, anche quando la tabella è filtrata.

**Esporta CSV** scarica gli eventi della selezione corrente. Il file usa il punto e virgola come separatore e la codifica UTF-8 con BOM, utile per visualizzare le lettere accentate nei programmi di foglio di calcolo.

Ogni esportazione viene generata in memoria per la singola richiesta, senza sovrascrivere un file condiviso. In caso di errore nei moduli di inserimento e modifica, i valori digitati vengono conservati. Se il database non è disponibile, l'app mostra un messaggio comprensibile.

## Importazione dei log

### Formato accettato

Ogni riga contiene quattro campi separati da `|`:

```text
data e ora | indirizzo IP | livello | descrizione
```

Esempio:

```text
2026-10-12 09:15:32 | 192.168.1.10 | WARNING | Login fallito per utente admin
2026-10-12 09:17:05 | 192.168.1.20 | ERROR | Connessione bloccata dal firewall
```

La data deve seguire il formato `AAAA-MM-GG HH:MM:SS`. Sono accettati IP sia IPv4 sia IPv6. I livelli devono essere scritti in maiuscolo:

| Livello nel log | Gravità assegnata |
|---|---|
| `INFO` | Bassa |
| `WARNING` | Media |
| `ERROR` | Alta |
| `CRITICAL` | Critica |

### Procedura

1. Apri **Importa log** e premi **Scegli file**.
2. Seleziona un file `.log` o `.txt` in UTF-8 e premi **Analizza file**.
3. Controlla l'anteprima e le segnalazioni delle righe non valide.
4. Lascia selezionati gli eventi desiderati e scegli **una categoria per ogni evento**.
5. Premi **Importa eventi selezionati** e consulta la dashboard.

Puoi provare il flusso con [`esempi/eventi.log`](esempi/eventi.log).

### Controlli applicati

- File di massimo **256 KB** e **1000 righe**; le righe vuote vengono ignorate.
- Verifica di formato, data, IP, livello e descrizione.
- Errori accompagnati dal numero di riga, senza impedire l'analisi delle altre righe.
- Categoria obbligatoria soltanto per gli eventi selezionati.
- Anteprima firmata, valida per **30 minuti**; l'analisi non inserisce dati nel database.
- Salvataggio degli eventi selezionati in una singola transazione, con data originale e stato **Nuovo**.

La firma permette di verificare che l'anteprima non sia stata alterata; non cifra i dati. Il salvataggio viene annullato in caso di errore del database se la tabella usa un motore transazionale, come InnoDB.

## Struttura del progetto

```text
CS Monitor/
├── app.py                       # Pagine e coordinamento dell'app
├── requirements.txt             # Dipendenze Python
├── database/
│   ├── connessione.py            # Connessione a MySQL
│   ├── categorie_repository.py   # Lettura delle categorie
│   └── eventi_repository.py      # Operazioni e statistiche sugli eventi
├── models/
│   ├── categoria.py              # Classe Categoria e validazione
│   └── evento_sicurezza.py       # Classe EventoSicurezza e validazione
├── services/
│   └── log_importer.py           # Analisi dei log
├── templates/                   # Pagine HTML e componenti comuni
├── static/
│   ├── css/stile.css             # Stile dell'interfaccia
│   └── img/                     # Logo e foto profilo
├── esempi/eventi.log             # File per provare l'importazione
├── instance/                    # Eventuali file locali dell'applicazione
├── test_modelli.py              # Esempi di controllo dei modelli
├── test_database.py             # Verifica della connessione e della lettura
├── test_repository.py           # Verifica CRUD sul database reale
├── test_importazione_log.py      # Test dell'importazione con database simulato
└── test_correzioni.py            # Test su moduli, ricerca, errori e CSV
```

Le operazioni **CRUD** sono le quattro azioni fondamentali sui dati: **Create** (creare), **Read** (leggere), **Update** (modificare) e **Delete** (eliminare).

## Database

Il database contiene due tabelle collegate da una relazione **uno a molti**: una categoria può essere associata a più eventi; ogni evento appartiene a una sola categoria.

| Tabella | Campi |
|---|---|
| `categorie` | `id_categoria`, `nome` |
| `eventi` | `id_evento`, `id_categoria`, `indirizzo_ip`, `descrizione`, `gravita`, `stato`, `data_evento` |

`id_evento` identifica ogni evento. `id_categoria` nella tabella `eventi` è una **chiave esterna**: collega l'evento a una categoria esistente.

### Schema per una nuova installazione

Nel repository non è presente un file SQL di inizializzazione. Il seguente schema è compatibile con i campi usati dal codice; non rappresenta un'esportazione del database locale. Eseguilo in un client MySQL su un'installazione nuova:

```sql
CREATE DATABASE cybersec_monitor CHARACTER SET utf8mb4;
USE cybersec_monitor;

CREATE TABLE categorie (
    id_categoria INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE eventi (
    id_evento INT AUTO_INCREMENT PRIMARY KEY,
    id_categoria INT NOT NULL,
    indirizzo_ip VARCHAR(45) NOT NULL,
    descrizione TEXT NOT NULL,
    gravita ENUM('Bassa', 'Media', 'Alta', 'Critica') NOT NULL,
    stato ENUM('Nuovo', 'In analisi', 'Risolto') NOT NULL DEFAULT 'Nuovo',
    data_evento DATETIME NOT NULL,
    FOREIGN KEY (id_categoria) REFERENCES categorie(id_categoria)
) ENGINE=InnoDB;

INSERT INTO categorie (nome) VALUES
    ('Accessi sospetti'),
    ('Firewall'),
    ('Malware');
```

Le query utilizzano parametri separati dal testo SQL. Le classi verificano gli ID positivi, gli IP, le descrizioni non vuote e i valori ammessi per gravità e stato.

## Test e verifiche

### Test automatici dell'importazione

Con l'ambiente attivo:

```powershell
python -m unittest test_importazione_log -v
```

La suite comprende **12 test** su analisi delle righe, livelli, date, IPv6, limiti dei file, categorie per evento, selezioni, anteprime non valide o scadute e gestione degli errori di salvataggio.

Questi test usano un database simulato e **non scrivono nel MySQL reale**. Il loro superamento non sostituisce una verifica dell'applicazione collegata al database.

Per eseguire anche gli 8 test sulle correzioni funzionali (20 test complessivi):

```powershell
python -m unittest test_importazione_log test_correzioni -v
```

### Controlli sul database reale

```powershell
python test_modelli.py
python test_database.py
python test_repository.py
```

`test_modelli.py` mostra esempi delle classi e delle validazioni. `test_database.py` verifica la connessione e legge gli eventi. `test_repository.py` inserisce, cerca, modifica ed elimina un evento temporaneo: richiede una categoria con **ID 1** e va eseguito su un database di prova.

### Problemi comuni

| Problema | Cosa controllare |
|---|---|
| `ModuleNotFoundError` | Usa l'interprete di `.venv` e installa `requirements.txt`. |
| Errore di connessione a MySQL | Controlla il servizio MySQL e host, porta e credenziali nel `.env`. |
| Database o tabella non trovati | Prepara lo schema e verifica il valore di `DB_NAME`. |
| Menu categorie vuoto | Inserisci almeno una categoria nella tabella `categorie`. |
| Anteprima scaduta o non valida | Ricarica il file; usa una `SECRET_KEY` stabile per mantenere le anteprime tra riavvii. |
| Stile o icone mancanti | Verifica la connessione ai CDN di Bootstrap e Bootstrap Icons. |



## Limiti e sviluppi futuri

La versione attuale è pensata per uso didattico e dimostrazioni locali. Gli eventi vengono inseriti dall'utente o ricavati dai file caricati: non è presente un monitoraggio automatico della rete.

Non sono ancora implementati autenticazione e ruoli, gestione delle categorie dall'interfaccia, paginazione degli eventi e riconoscimento dei duplicati. Importare nuovamente lo stesso file crea nuovi eventi. Il parser accetta soltanto il formato documentato.

Possibili evoluzioni sono grafici nella dashboard, filtri per data e categoria, cronologia delle modifiche e supporto per altri formati di log.

## Contatti

**Marco Filannino**

- [GitHub](https://github.com/MarcoFilannino2004)
- [LinkedIn](https://www.linkedin.com/in/marco-filannino/)
- [Email](mailto:marcofilannino04@gmail.com)

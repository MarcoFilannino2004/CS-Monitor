# CyberSec Monitor

**Progetto finale del corso di sviluppo Python**  
**Autore:** Marco Filannino  


## Descrizione

CyberSec Monitor è un'applicazione web per la gestione di eventi di sicurezza informatica, ispirata alle attività di un Security Operations Center (SOC).

L'obiettivo è registrare, consultare, modificare ed eliminare eventi di sicurezza attraverso un'interfaccia Flask e un database MySQL. Il progetto integra programmazione orientata agli oggetti, SQL e sviluppo web.

## Tecnologie

* **Python:** logica applicativa e classi OOP.
* **MySQL:** memorizzazione degli eventi.
* **mysql-connector-python:** collegamento tra Python e MySQL.
* **python-dotenv:** gestione delle credenziali tramite file `.env`.
* **Flask:** backend web (da sviluppare).
* **HTML, CSS, Bootstrap e JavaScript:** interfaccia web (da sviluppare).

## Funzionalità

### Realizzate e verificate

* \[x] Creazione del database `cybersec\_monitor`.
* \[x] Creazione delle tabelle `categorie` ed `eventi`, collegate tramite chiave esterna.
* \[x] Inserimento di categorie ed eventi di prova.
* \[x] Creazione delle classi `Categoria` ed `EventoSicurezza`.
* \[x] Getter, setter e validazione degli attributi, inclusi gli indirizzi IP.
* \[x] Connessione Python-MySQL tramite `mysql-connector-python`.
* \[x] Lettura dell'elenco degli eventi dal database.
* \[x] Inserimento di un nuovo evento tramite un oggetto Python.

### Implementate, da verificare con il test completo

* \[ ] Ricerca di un evento tramite ID.
* \[ ] Modifica di un evento esistente.
* \[ ] Eliminazione di un evento.
* \[ ] Esecuzione del test CRUD completo.

### Da sviluppare

* \[ ] Pagine Flask per visualizzare, aggiungere, modificare ed eliminare eventi.
* \[ ] Dashboard con riepilogo degli eventi.
* \[ ] Ricerca e filtri nell'interfaccia.
* \[ ] Validazione dei form e gestione dei messaggi di errore.
* \[ ] Testing finale e documentazione di utilizzo.

**Possibili funzionalità aggiuntive:** analisi di file di log con regex, statistiche con pandas, grafici con matplotlib ed esportazione CSV.

## Importazione dei log

Dal menu **Importa log** puoi caricare un file `.log` o `.txt` in UTF-8
(massimo 256 KB e 1000 righe), usando questo formato:

```text
2026-10-12 09:15:32 | 192.168.1.10 | WARNING | Login fallito per utente admin
2026-10-12 09:17:05 | 192.168.1.20 | ERROR | Connessione bloccata dal firewall
```

Il file `esempi/eventi.log` contiene quattro eventi pronti da provare.
I livelli INFO, WARNING, ERROR e CRITICAL corrispondono rispettivamente a
Bassa, Media, Alta e Critica. Sono supportati indirizzi IPv4 e IPv6.

Dopo l'analisi, la pagina mostra gli eventi validi e gli errori con il numero
di riga. Seleziona gli eventi desiderati, scegli una categoria per ogni evento e premi
**Importa eventi selezionati**. L'analisi non salva nulla nel database.
L'importazione conserva la data del log, assegna lo stato **Nuovo** e salva
tutti gli eventi selezionati in una singola transazione.

L'anteprima è firmata e scade dopo 30 minuti. Per conservarne la validità
tra riavvii o più processi dell'app, configura una `SECRET_KEY` stabile nel `.env`.
Questa versione non elimina i duplicati: importare nuovamente lo stesso file
crea altri eventi.

Test senza scrivere nel database, usando l'ambiente del progetto:
`.\.venv\Scripts\python.exe -m unittest test_importazione_log -v`.

## Struttura del database

Il database `cybersec\_monitor` contiene due tabelle:

* **`categorie`:** `id\_categoria`, `nome`.
* **`eventi`:** `id\_evento`, `id\_categoria`, `indirizzo\_ip`, `descrizione`, `gravita`, `stato`, `data\_evento`.

La relazione è **uno-a-molti**: una categoria può essere associata a più eventi, mentre ogni evento appartiene a una sola categoria.

## Organizzazione del codice

* **`models/categoria.py`:** classe che rappresenta una categoria.
* **`models/evento\_sicurezza.py`:** classe che rappresenta un evento e valida i suoi attributi.
* **`database/connessione.py`:** funzione `creaConnessione()` per collegarsi a MySQL.
* **`database/eventi\_repository.py`:** funzioni per eseguire le operazioni CRUD sugli eventi.
* **File di test:** verificano classi, connessione al database e operazioni CRUD.

Il repository permette di riutilizzare le query SQL senza riscriverle nelle future route Flask. Le query utilizzano parametri per evitare di inserire direttamente i valori nelle istruzioni SQL.

## Stato del progetto

**Backend MySQL e modelli Python realizzati.** Inserimento e lettura degli eventi verificati; test completo di ricerca, modifica ed eliminazione in attesa di conferma. Interfaccia web ancora da sviluppare.


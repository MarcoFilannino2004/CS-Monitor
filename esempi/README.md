# Log di esempio

I file contengono eventi inventati per provare CS Monitor. Gli indirizzi IPv4 `192.0.2.x` e IPv6 `2001:db8::` sono usati per gli esempi; non rappresentano dispositivi reali.

| File | Eventi validi | Contenuto |
|---|---:|---|
| `eventi.log` | 4 | Esempio breve per iniziare. |
| `accessi.log` | 200 | Accessi riusciti, password errate, account bloccati e accessi sospetti. |
| `firewall.log` | 200 | Connessioni consentite, traffico bloccato e scansioni delle porte. |
| `malware.log` | 200 | Scansioni antivirus, file sospetti, quarantena e minacce simulate. |
| `sistema.log` | 200 | Backup, aggiornamenti, errori dei servizi e modifiche alla configurazione. |
| `eventi_misti.log` | 500 | Eventi di tutti gli scenari e di tutte le gravità. |
| `eventi_ipv6.log` | 100 | Eventi con indirizzi IPv6. |
| `volume_1000_eventi.log` | 1000 | Il massimo numero di righe consentito, per provare un'importazione grande. |
| `righe_errate.log` | 20 | Include anche 6 righe intenzionalmente errate per verificare i messaggi di errore. |

## Come usarli

1. Accedi e apri **Importa log**.
2. Scegli uno dei file e premi **Analizza file**.
3. Controlla l'anteprima e seleziona gli eventi desiderati. Usa **Seleziona tutti** per un file della stessa categoria.
4. Scegli la **Categoria da applicare** e premi **Applica ai selezionati**. Puoi ancora modificare la categoria di singoli eventi.
5. Conferma l'importazione e consulta la dashboard o lo storico dei log.

Tutti i file sono in UTF-8 e inferiori a 256 KB. Per iniziare con pochi eventi usa `eventi.log`. Per `firewall.log`, ad esempio, puoi assegnare **Firewall e traffico bloccato** a tutte le righe in un solo passaggio.

In `righe_errate.log`, le prime 20 righe sono valide. Le righe dalla 21 alla 26 provano rispettivamente: formato errato, IP non valido, data inesistente, ora non valida, livello non supportato e descrizione vuota. Il risultato atteso è **20 eventi validi e 6 errori**.

Il formato usato è:

```text
2026-10-13 08:00:00 | 192.0.2.1 | INFO | Accesso riuscito al portale aziendale
```

Livelli: `INFO`, `WARNING`, `ERROR`, `CRITICAL`. Le categorie si scelgono durante l'importazione. Caricare di nuovo un file già importato crea una nuova importazione e nuovi eventi.

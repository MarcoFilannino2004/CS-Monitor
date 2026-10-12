import re
from datetime import datetime
from models.evento_sicurezza import EventoSicurezza

MAX_BYTES = 256 * 1024
MAX_RIGHE = 1000
GRAVITA = {"INFO": "Bassa", "WARNING": "Media", "ERROR": "Alta", "CRITICAL": "Critica"}
FORMATO = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(.*)$")


def analizzaLog(contenuto):
    """Restituisce righe valide ed errori con i numeri di riga originali."""
    if len(contenuto) > MAX_BYTES:
        raise ValueError("Il file non può superare 256 KB.")
    try:
        righe = contenuto.decode("utf-8-sig").splitlines()
    except UnicodeDecodeError:
        raise ValueError("Il file deve avere codifica UTF-8.") from None
    if len(righe) > MAX_RIGHE:
        raise ValueError("Il file non può contenere più di 1000 righe.")
    eventi, errori = [], []
    for numero, riga in enumerate(righe, 1):
        if not riga.strip():
            continue
        try:
            campi = FORMATO.fullmatch(riga.strip())
            if campi is None:
                raise ValueError("Formato non valido: usa data | IP | livello | messaggio.")
            data_testo, ip, livello, descrizione = campi.groups()
            if livello not in GRAVITA:
                raise ValueError("Livello non valido: usa INFO, WARNING, ERROR o CRITICAL.")
            try:
                data = datetime.strptime(data_testo, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                raise ValueError("Data o ora non valida.") from None
            evento = EventoSicurezza(None, 1, ip.strip(), descrizione, GRAVITA[livello], data_evento=data)
            eventi.append({"riga": numero, "data_evento": data_testo,
                           "indirizzo_ip": evento.indirizzo_ip, "descrizione": evento.descrizione,
                           "gravita": evento.gravita})
        except ValueError as errore:
            errori.append({"riga": numero, "messaggio": str(errore)})
    if not eventi and not errori:
        raise ValueError("Il file è vuoto o contiene soltanto righe vuote.")
    return eventi, errori

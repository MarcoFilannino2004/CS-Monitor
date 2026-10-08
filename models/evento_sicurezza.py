from datetime import datetime
from ipaddress import ip_address


class EventoSicurezza:

    GRAVITA_CONSENTITE = ("Bassa", "Media", "Alta", "Critica")
    STATI_CONSENTITI = ("Nuovo", "In analisi", "Risolto")

    def __init__(self, id_evento: int | None, id_categoria: int, indirizzo_ip: str, descrizione: str, gravita: str, stato: str = "Nuovo", data_evento: datetime | None = None):
        self.id_evento = id_evento
        self.id_categoria = id_categoria
        self.indirizzo_ip = indirizzo_ip
        self.descrizione = descrizione
        self.gravita = gravita
        self.stato = stato
        self.data_evento = data_evento if data_evento is not None else datetime.now()

    @property
    def id_evento(self):
        return self._id_evento

    @id_evento.setter
    def id_evento(self, valore):
        if valore is not None and (type(valore) is not int or valore <= 0):
            raise ValueError("L'ID dell'evento deve essere un intero positivo.")
        self._id_evento = valore

    @property
    def id_categoria(self):
        return self._id_categoria

    @id_categoria.setter
    def id_categoria(self, valore):
        if type(valore) is not int or valore <= 0:
            raise ValueError("L'ID della categoria deve essere un intero positivo.")
        self._id_categoria = valore

    @property
    def indirizzo_ip(self):
        return self._indirizzo_ip

    @indirizzo_ip.setter
    def indirizzo_ip(self, valore):
        try:
            ip_address(valore)
        except (ValueError, TypeError):
            raise ValueError("Indirizzo IP non valido.")
        self._indirizzo_ip = valore

    @property
    def descrizione(self):
        return self._descrizione

    @descrizione.setter
    def descrizione(self, valore):
        if not isinstance(valore, str) or not valore.strip():
            raise ValueError("La descrizione non può essere vuota.")
        self._descrizione = valore.strip()

    @property
    def gravita(self):
        return self._gravita

    @gravita.setter
    def gravita(self, valore):
        if valore not in self.GRAVITA_CONSENTITE:
            raise ValueError("Gravità non valida.")
        self._gravita = valore

    @property
    def stato(self):
        return self._stato

    @stato.setter
    def stato(self, valore):
        if valore not in self.STATI_CONSENTITI:
            raise ValueError("Stato non valido.")
        self._stato = valore

    @property
    def data_evento(self):
        return self._data_evento

    @data_evento.setter
    def data_evento(self, valore):
        if not isinstance(valore, datetime):
            raise ValueError("La data deve essere un oggetto datetime.")
        self._data_evento = valore

    def __str__(self):
        return f"Evento {self.id_evento} | Categoria: {self.id_categoria} | IP: {self.indirizzo_ip} | Gravità: {self.gravita} | Stato: {self.stato}"
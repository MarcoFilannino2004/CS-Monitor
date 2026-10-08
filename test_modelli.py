from models.categoria import Categoria
from models.evento_sicurezza import EventoSicurezza

categoria = Categoria(1, "Login fallito")
print(categoria)

evento = EventoSicurezza(None, 1, "192.168.1.15", "Tentativi di accesso falliti", "Alta")
print(evento)

evento.stato = "In analisi"
print(evento)

try:
    evento = EventoSicurezza(None, 1, "999.999.999.999", "Tentativo di accesso", "Alta")
except ValueError as errore:
    print(f"Errore rilevato correttamente: {errore}")
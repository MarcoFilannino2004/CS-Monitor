from database.eventi_repository import (
    inserisciEvento,
    visualizzaEventi,
    cercaEvento,
    modificaEvento,
    eliminaEvento,
)
from models.evento_sicurezza import EventoSicurezza


def stampaEventi():
    print("\n========== ELENCO EVENTI ==========")

    for evento in visualizzaEventi(amministratore=True):
        print(
            f"{evento['id_evento']} | {evento['categoria']} | {evento['indirizzo_ip']} | {evento['gravita']} | {evento['stato']}"
        )


def testCRUD():
    id_test = None

    try:
        # READ
        stampaEventi()

        # CREATE
        print("\n========== CREATE ==========")

        nuovo_evento = EventoSicurezza(
            None, 1, "192.168.1.200", "Evento temporaneo per test CRUD", "Media"
        )
        id_test = inserisciEvento(nuovo_evento)

        print(f"Evento creato con ID: {id_test}")

        # READ - Singolo evento
        print("\n========== READ ==========")

        evento_trovato = cercaEvento(id_test, amministratore=True)
        assert evento_trovato is not None, "Evento non trovato dopo l'inserimento."

        print(evento_trovato)

        # UPDATE
        print("\n========== UPDATE ==========")

        nuovo_evento.descrizione = "Evento modificato durante il test CRUD"
        nuovo_evento.gravita = "Alta"
        nuovo_evento.stato = "In analisi"

        modificato = modificaEvento(nuovo_evento, amministratore=True)
        assert modificato, "La modifica non Ã¨ stata eseguita."

        evento_aggiornato = cercaEvento(id_test, amministratore=True)
        assert evento_aggiornato["descrizione"] == "Evento modificato durante il test CRUD"
        assert evento_aggiornato["gravita"] == "Alta"
        assert evento_aggiornato["stato"] == "In analisi"

        print("Evento modificato correttamente!")
        print(evento_aggiornato)

        # DELETE
        print("\n========== DELETE ==========")

        eliminato = eliminaEvento(id_test, amministratore=True)
        assert eliminato, "L'eliminazione non Ã¨ stata eseguita."

        assert (
            cercaEvento(id_test, amministratore=True) is None
        ), "L'evento risulta ancora presente."

        id_test = None
        print("Evento eliminato correttamente!")

        # READ finale
        stampaEventi()

        print("\nTUTTI I TEST CRUD SUPERATI!")

    finally:
        if id_test is not None and cercaEvento(id_test, amministratore=True) is not None:
            eliminaEvento(id_test, amministratore=True)
            print("\nPulizia: evento temporaneo eliminato.")


if __name__ == "__main__":
    testCRUD()

import io
import base64
from test_support import preparaClient
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
import mysql.connector

from app import app
from services.log_importer import analizzaLog, MAX_BYTES
from database.eventi_repository import inserisciEventi
from models.evento_sicurezza import EventoSicurezza

RIGA = "2026-10-12 09:15:32 | 192.168.1.10 | WARNING | Login fallito per utente admin"


class ParserTests(unittest.TestCase):
    def test_livelli_date_e_ipv6(self):
        testo = "\n".join(
            RIGA.replace("WARNING", livello).replace("192.168.1.10", "2001:db8::1")
            for livello in ("INFO", "WARNING", "ERROR", "CRITICAL")
        )
        eventi, errori = analizzaLog(testo.encode("utf-8-sig"))
        self.assertEqual(errori, [])
        self.assertEqual([e["gravita"] for e in eventi], ["Bassa", "Media", "Alta", "Critica"])
        self.assertEqual(eventi[0]["data_evento"], "2026-10-12 09:15:32")

    def test_errori_e_numeri_riga(self):
        righe = [
            RIGA,
            "",
            "riga errata",
            RIGA.replace("192.168.1.10", "999.1.1.1"),
            RIGA.replace("2026-10-12", "2026-02-30"),
            RIGA.replace("WARNING", "DEBUG"),
            RIGA.rsplit("|", 1)[0] + "|   ",
        ]
        eventi, errori = analizzaLog("\n".join(righe).encode())
        self.assertEqual(len(eventi), 1)
        self.assertEqual([e["riga"] for e in errori], [3, 4, 5, 6, 7])

    def test_limiti_e_codifica(self):
        for contenuto in (b"", b"\xff", b"a" * (MAX_BYTES + 1), b"\n" * 1001):
            with self.subTest(contenuto=contenuto[:20]), self.assertRaises(ValueError):
                analizzaLog(contenuto)


class RouteTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY="chiave-test")
        self.client = preparaClient(self, app)
        self.eventi, _ = analizzaLog((RIGA + "\n" + RIGA.replace("WARNING", "ERROR")).encode())
        self.token = URLSafeTimedSerializer(
            app.config["SECRET_KEY"], salt="importazione-log"
        ).dumps(
            dict(
                eventi=self.eventi,
                id_utente=1,
                nome_file='eventi.log',
                contenuto=base64.b64encode(
                    (RIGA + "\n" + RIGA.replace('WARNING', 'ERROR')).encode()
                ).decode(),
                righe_errate=0,
                identificativo='test-anteprima',
            )
        )

    @patch("app.salvaImportazione", return_value=1)
    @patch("app.visualizzaCategorie", return_value=[{"id_categoria": 2, "nome": "Accessi"}])
    def test_anteprima_non_salva(self, categorie, salva):
        risposta = self.client.post(
            "/eventi/importa", data={"file_log": (io.BytesIO(RIGA.encode()), "eventi.log")}
        )
        self.assertEqual(risposta.status_code, 200)
        self.assertIn(b"anteprima", risposta.data)
        salva.assert_not_called()

    @patch("app.salvaImportazione", return_value=1)
    @patch("app.visualizzaCategorie", return_value=[{"id_categoria": 2, "nome": "Accessi"}])
    def test_importa_solo_selezionati(self, categorie, salva):
        risposta = self.client.post(
            "/eventi/importa",
            data={
                "azione": "conferma",
                "anteprima": self.token,
                "selezionati": "2",
                "categoria_2": "2",
            },
        )
        self.assertEqual(risposta.status_code, 303)
        eventi = salva.call_args.args[0]
        self.assertEqual(len(eventi), 1)
        self.assertEqual(eventi[0].id_categoria, 2)
        self.assertEqual(eventi[0].gravita, "Alta")
        self.assertEqual(eventi[0].stato, "Nuovo")
        self.assertEqual(eventi[0].data_evento, datetime(2026, 10, 12, 9, 15, 32))
        self.assertIn("/importazioni/1", risposta.location)

    @patch("app.salvaImportazione", return_value=1)
    @patch("app.visualizzaCategorie", return_value=[{"id_categoria": 2, "nome": "Accessi"}])
    def test_conferme_non_valide(self, categorie, salva):
        casi = [
            ("alterato", "1", "2"),
            (self.token, "999", "2"),
            (self.token, "1", "999"),
            (self.token, "", "2"),
        ]
        for token, riga, categoria in casi:
            with self.subTest(riga=riga, categoria=categoria):
                risposta = self.client.post(
                    "/eventi/importa",
                    data={
                        "azione": "conferma",
                        "anteprima": token,
                        "selezionati": riga,
                        "categoria_1": categoria,
                    },
                )
                self.assertEqual(risposta.status_code, 200)
                self.assertIn(b"alert-danger", risposta.data)
        salva.assert_not_called()

    @patch("app.salvaImportazione", return_value=1)
    @patch(
        "app.visualizzaCategorie",
        return_value=[
            {"id_categoria": 2, "nome": "Accessi"},
            {"id_categoria": 3, "nome": "Firewall"},
        ],
    )
    def test_categorie_diverse_per_evento(self, categorie, salva):
        risposta = self.client.post(
            "/eventi/importa",
            data={
                "azione": "conferma",
                "anteprima": self.token,
                "selezionati": ["1", "2"],
                "categoria_1": "2",
                "categoria_2": "3",
            },
        )
        self.assertEqual(risposta.status_code, 303)
        self.assertEqual([e.id_categoria for e in salva.call_args.args[0]], [2, 3])

    @patch("app.salvaImportazione", return_value=1)
    @patch("app.visualizzaCategorie", return_value=[{"id_categoria": 2, "nome": "Accessi"}])
    def test_categoria_mancante_blocca_intera_importazione(self, categorie, salva):
        risposta = self.client.post(
            "/eventi/importa",
            data={
                "azione": "conferma",
                "anteprima": self.token,
                "selezionati": ["1", "2"],
                "categoria_1": "2",
            },
        )
        self.assertIn(b"categoria valida per la riga 2", risposta.data)
        self.assertIn(b'value="2" selected', risposta.data)
        salva.assert_not_called()

    @patch("app.URLSafeTimedSerializer")
    def test_anteprima_scaduta(self, firma):
        firma.return_value.loads.side_effect = SignatureExpired("scaduta")
        risposta = self.client.post(
            "/eventi/importa", data={"azione": "conferma", "anteprima": self.token}
        )
        self.assertIn(b"scaduta", risposta.data)

    def test_vecchia_anteprima_chiede_nuovo_caricamento(self):
        token = URLSafeTimedSerializer(app.config['SECRET_KEY'], salt='importazione-log').dumps(
            self.eventi
        )
        r = self.client.post('/eventi/importa', data=dict(azione='conferma', anteprima=token))
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Carica nuovamente', r.data)

    def test_upload_non_valido(self):
        self.assertEqual(self.client.get("/eventi/importa").status_code, 200)
        for data in (
            {},
            {"file_log": (io.BytesIO(b"test"), "file.csv")},
            {"file_log": (io.BytesIO(b"x" * (MAX_BYTES + 1)), "file.log")},
        ):
            risposta = self.client.post("/eventi/importa", data=data)
            self.assertIn(b"alert-danger", risposta.data)

    @patch("app.visualizzaCategorie", return_value=[{"id_categoria": 2, "nome": "Accessi"}])
    @patch("app.salvaImportazione", side_effect=mysql.connector.Error("errore interno"))
    def test_errore_database(self, salva, categorie):
        risposta = self.client.post(
            "/eventi/importa",
            data={
                "azione": "conferma",
                "anteprima": self.token,
                "selezionati": "1",
                "categoria_1": "2",
            },
        )
        self.assertIn(b"Riprova tra poco", risposta.data)
        self.assertNotIn(b"errore interno", risposta.data)


class RepositoryTests(unittest.TestCase):
    @patch("database.eventi_repository.creaConnessione")
    def test_transazione_e_rollback(self, crea):
        connessione = MagicMock()
        crea.return_value = connessione
        evento = EventoSicurezza(None, 2, "192.168.1.10", "Test", "Media")
        inserisciEventi([evento])
        connessione.commit.assert_called_once()
        connessione.rollback.assert_not_called()
        connessione.reset_mock()
        connessione.cursor.return_value.executemany.side_effect = mysql.connector.Error("errore")
        with self.assertRaises(mysql.connector.Error):
            inserisciEventi([evento])
        connessione.commit.assert_not_called()
        connessione.rollback.assert_called_once()
        connessione.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()

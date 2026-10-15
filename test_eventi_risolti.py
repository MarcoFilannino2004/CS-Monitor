"""Prove delle pagine dei risolti e della cancellazione protetta."""

import csv
import io
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock
import mysql.connector
from app import app
from services.esportazione import firmaEventi
from database.eventi_repository import eliminaEventiRisolti
from test_support import preparaClient, UTENTE


class EventiRisoltiTests(unittest.TestCase):
    def setUp(self):
        self.config = app.config.copy()
        app.config.update(TESTING=True, SECRET_KEY='risolti-test')
        self.addCleanup(lambda: app.config.update(self.config))
        self.client = preparaClient(self, app)
        self.evento = dict(
            id_evento=10,
            categoria='Firewall',
            indirizzo_ip='192.0.2.1',
            descrizione='Evento concluso',
            gravita='Alta',
            stato='Risolto',
            data_evento=datetime(2026, 10, 15),
            autore='utente_test',
        )

    def esporta(self):
        with patch('app.visualizzaEventi', return_value=[self.evento]):
            return self.client.get('/eventi/risolti/esporta')

    def test_pagina_legge_soltanto_risolti_del_proprietario(self):
        with patch('app.visualizzaEventi', return_value=[self.evento]) as leggi:
            r = self.client.get('/eventi/risolti')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Evento concluso', r.data)
        self.assertIn(b'csrf_token', r.data)
        leggi.assert_called_once_with(stato='Risolto', id_utente=1, amministratore=False)

    def test_csv_e_autorizzazione_alla_cancellazione(self):
        r = self.esporta()
        righe = list(csv.reader(io.StringIO(r.data.decode('utf-8-sig')), delimiter=';'))
        self.assertEqual(righe[1][0], '10')
        self.assertEqual(righe[1][5], 'Risolto')
        self.assertIn('eventi_risolti.csv', r.headers['Content-Disposition'])
        with self.client.session_transaction() as s:
            self.assertEqual(s['esportazione_risolti']['firma'], firmaEventi([self.evento]))

    def test_eliminazione_richiede_download_e_conferma(self):
        with patch('app.eliminaEventiRisolti') as elimina:
            self.assertEqual(
                self.client.post('/eventi/risolti/elimina', data={'conferma': 'si'}).status_code,
                303,
            )
            self.esporta()
            self.client.post('/eventi/risolti/elimina', data={})
            elimina.assert_not_called()

    def test_eliminazione_valida_consuma_autorizzazione(self):
        self.esporta()
        with patch('app.eliminaEventiRisolti', return_value=1) as elimina:
            r = self.client.post('/eventi/risolti/elimina', data={'conferma': 'si'})
            self.assertEqual(r.status_code, 303)
            elimina.assert_called_once_with(
                firmaEventi([self.evento]), id_utente=1, amministratore=False
            )
            self.client.post('/eventi/risolti/elimina', data={'conferma': 'si'})
            self.assertEqual(elimina.call_count, 1)

    def test_download_scaduto_non_autorizza_eliminazione(self):
        self.esporta()
        with self.client.session_transaction() as s:
            dati = dict(s['esportazione_risolti'], scadenza=0)
            s['esportazione_risolti'] = dati
        with patch('app.eliminaEventiRisolti') as elimina:
            self.client.post('/eventi/risolti/elimina', data={'conferma': 'si'})
            elimina.assert_not_called()

    def test_nuovo_ruolo_non_riusa_download_precedente(self):
        self.esporta()
        with patch(
            'database.utenti_repository.cercaUtente', return_value=dict(UTENTE, ruolo='admin')
        ), patch('app.eliminaEventiRisolti') as elimina:
            self.client.post('/eventi/risolti/elimina', data={'conferma': 'si'})
            elimina.assert_not_called()

    def test_nessun_risolto_nessun_download_o_pulsante_elimina(self):
        with patch('app.visualizzaEventi', return_value=[]):
            r = self.client.get('/eventi/risolti')
            self.assertIn(b'Nessun evento risolto', r.data)
            self.assertNotIn(b'conferma-eliminazione', r.data)
            self.assertEqual(self.client.get('/eventi/risolti/esporta').status_code, 303)

    def test_csrf_e_metodo_get_non_consentono_eliminazione(self):
        self.assertEqual(self.client.get('/eventi/risolti/elimina').status_code, 405)
        with patch('app.eliminaEventiRisolti') as elimina:
            self.assertEqual(
                self.client.post(
                    '/eventi/risolti/elimina', data={'csrf_token': 'errato', 'conferma': 'si'}
                ).status_code,
                400,
            )
            elimina.assert_not_called()

    @patch('database.strumenti.creaConnessione')
    def test_errore_database_annulla_la_transazione(self, crea):
        connessione = MagicMock()
        crea.return_value = connessione
        cursore = connessione.cursor.return_value
        cursore.fetchall.return_value = [self.evento]
        cursore.execute.side_effect = [None, mysql.connector.Error('errore simulato')]
        with self.assertRaises(mysql.connector.Error):
            eliminaEventiRisolti(firmaEventi([self.evento]), id_utente=1)
        connessione.commit.assert_not_called()
        connessione.rollback.assert_called_once()
        connessione.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()

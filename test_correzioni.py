import csv
import io
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock
import mysql.connector
from app import app
from test_support import preparaClient
from database.eventi_repository import visualizzaEventi


class CorrezioniTests(unittest.TestCase):
    def setUp(self):
        self.config = app.config.copy()
        app.config.update(TESTING=True, SECRET_KEY="test-correzioni")
        self.client = preparaClient(self, app)
        self.categorie = [{"id_categoria": 1, "nome": "Accessi"}, {"id_categoria": 2, "nome": "Firewall"}]
        self.evento = dict(id_evento=1, id_categoria=1, categoria="Accessi", indirizzo_ip="192.0.2.1",
                           descrizione="Originale", gravita="Media", stato="Nuovo", data_evento=datetime(2026, 10, 12))
        self.dati = dict(id_categoria="2", indirizzo_ip="errato", descrizione="Bozza da conservare", gravita="Alta", stato="In analisi")
        self.cat_patch = patch("app.visualizzaCategorie", return_value=self.categorie)
        self.cat_patch.start()

    def tearDown(self):
        self.cat_patch.stop()
        app.config.clear()
        app.config.update(self.config)

    def verifica_dati(self, risposta):
        html = risposta.get_data(as_text=True)
        self.assertIn('value="errato"', html)
        self.assertIn('Bozza da conservare', html)
        self.assertIn('value="2" selected', html)
        self.assertIn('value="Alta" selected', html)

    @patch("app.inserisciEvento")
    def test_nuovo_conserva_dati_con_errore(self, salva):
        self.verifica_dati(self.client.post('/eventi/nuovo', data=self.dati))
        salva.assert_not_called()

    @patch("app.modificaEvento")
    def test_modifica_conserva_dati_con_errore(self, salva):
        with patch("app.cercaEvento", return_value=self.evento):
            risposta = self.client.post('/eventi/1/modifica', data=self.dati)
        self.verifica_dati(risposta)
        self.assertIn('value="In analisi" selected', risposta.get_data(as_text=True))
        salva.assert_not_called()

    def test_modifica_get_mostra_valori_originali(self):
        with patch("app.cercaEvento", return_value=self.evento):
            html = self.client.get('/eventi/1/modifica').get_data(as_text=True)
        self.assertIn('Originale', html)
        self.assertIn('value="1" selected', html)
        self.assertIn('value="Media" selected', html)

    def test_errori_database_gestiti(self):
        for target, url in [('app.visualizzaEventi', '/dashboard'), ('app.cercaEvento', '/eventi/1'),
                            ('app.visualizzaCategorie', '/eventi/nuovo'), ('app.visualizzaEventi', '/eventi/esporta')]:
            with self.subTest(url=url), patch(target, side_effect=mysql.connector.Error('dettaglio riservato')):
                risposta = self.client.get(url)
                self.assertEqual(risposta.status_code, 503)
                self.assertIn(b'Servizio temporaneamente non disponibile', risposta.data)
                self.assertNotIn(b'dettaglio riservato', risposta.data)

    def test_errore_salvataggio_conserva_modulo(self):
        dati = dict(self.dati, indirizzo_ip='192.0.2.2')
        with patch('app.inserisciEvento', side_effect=mysql.connector.Error('dettaglio riservato')):
            risposta = self.client.post('/eventi/nuovo', data=dati)
        self.assertIn(b'Bozza da conservare', risposta.data)
        self.assertIn(b'Riprova tra poco', risposta.data)
        self.assertNotIn(b'dettaglio riservato', risposta.data)

    @patch('database.eventi_repository.creaConnessione')
    def test_ricerche_numeriche_e_unicode(self, crea):
        cursore = MagicMock()
        cursore.fetchall.return_value = []
        crea.return_value.cursor.return_value = cursore
        for testo, atteso in [('²', ('%²%', '%²%')), ('0012', (12,)), ('9' * 5000, ()), ('0' * 5000 + '12', (12,))]:
            with self.subTest(testo=testo[:20]):
                visualizzaEventi(testo=testo, amministratore=True)
                query, valori = cursore.execute.call_args.args
                self.assertEqual(valori, atteso)
                if testo == '9' * 5000:
                    self.assertIn('AND 1=0', query)

    def test_esportazioni_indipendenti_e_filtrate(self):
        def elenco(gravita, stato, ordine, testo, **ambito):
            return [dict(self.evento, descrizione=testo)]
        with patch('app.visualizzaEventi', side_effect=elenco) as leggi, patch('builtins.open', side_effect=AssertionError('Scrittura su disco non prevista')):
            prima = self.client.get('/eventi/esporta?testo=prima&gravita=Alta', buffered=False)
            seconda = self.client.get('/eventi/esporta?testo=seconda', buffered=False)
            for risposta, atteso in [(prima, 'prima'), (seconda, 'seconda')]:
                righe = list(csv.reader(io.StringIO(risposta.data.decode('utf-8-sig')), delimiter=';'))
                self.assertEqual(righe[1][3], atteso)
                self.assertIn('attachment', risposta.headers['Content-Disposition'])
                risposta.close()
            self.assertEqual(leggi.call_args_list[0].args, ('Alta', None, 'recenti', 'prima'))

    def test_html_unico_e_tabella_vuota(self):
        with patch('app.visualizzaEventi', return_value=[]), patch('app.statisticheEventi', return_value=dict(totale=0)):
            html = self.client.get('/dashboard').get_data(as_text=True)
        self.assertEqual(html.count('<html'), 1)
        self.assertEqual(html.count('<head>'), 1)
        self.assertIn('colspan="7"', html)


if __name__ == '__main__':
    unittest.main()

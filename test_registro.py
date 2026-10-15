"""Controlli di riservatezza, permessi e registrazione automatica."""

import unittest
from datetime import datetime
from unittest.mock import patch
import mysql.connector
from app import app
from test_support import preparaClient, UTENTE


class RegistroTests(unittest.TestCase):
    def setUp(self):
        self.config = app.config.copy()
        app.config.update(TESTING=True, SECRET_KEY='registro-test', REGISTRO_ATTIVITA_NEI_TEST=True)
        self.addCleanup(lambda: (app.config.clear(), app.config.update(self.config)))
        self.client = preparaClient(self, app)
        self.scrittura = patch('services.registro.inserisciAttivita')
        self.salva = self.scrittura.start()
        self.addCleanup(self.scrittura.stop)
        self.voce = dict(
            id_attivita=1,
            data_attivita=datetime(2026, 10, 15, 14, 30),
            id_utente=1,
            username='utente_test',
            indirizzo_ip='192.0.2.1',
            azione='MODIFICA_EVENTO',
            esito='Riuscito',
            risorsa='evento:7',
            dettagli='Campi aggiornati: stato',
            metodo='POST',
            percorso='/eventi/<int:id_evento>/modifica',
            codice_http=302,
        )
        self.dati = dict(attivita=[self.voce], totale=1, pagina=1, pagine=1)

    def admin(self):
        identita = patch(
            'database.utenti_repository.cercaUtente', return_value=dict(UTENTE, ruolo='admin')
        )
        identita.start()
        self.addCleanup(identita.stop)

    def test_utente_non_puo_leggere_o_scaricare_registro(self):
        with patch('routes.registro.leggiRegistro') as leggi:
            for url in ('/amministrazione/registro', '/amministrazione/registro/esporta'):
                self.assertEqual(self.client.get(url).status_code, 403)
            leggi.assert_not_called()
        self.assertEqual(self.salva.call_args.args[0]['azione'], 'ACCESSO_NEGATO')
        self.assertEqual(self.salva.call_args.args[0]['esito'], 'Negato')

    def test_anonimo_deve_accedere_prima(self):
        client = app.test_client()
        with patch('routes.registro.leggiRegistro') as leggi:
            for url in ('/amministrazione/registro', '/amministrazione/registro/esporta'):
                r = client.get(url)
                self.assertEqual(r.status_code, 302)
                self.assertTrue(r.location.endswith('/login'))
            leggi.assert_not_called()
        self.assertEqual(self.salva.call_args.args[0]['azione'], 'ACCESSO_NON_AUTENTICATO')

    def test_menu_visibile_soltanto_admin(self):
        self.assertNotIn(b'/amministrazione/registro', self.client.get('/').data)
        self.admin()
        self.assertIn(b'/amministrazione/registro', self.client.get('/').data)

    def test_admin_pagina_di_sola_lettura_e_testo_escapato(self):
        self.admin()
        self.dati['attivita'] = [dict(self.voce, dettagli='<script>alert(1)</script>')]
        with patch('routes.registro.leggiRegistro', return_value=self.dati):
            r = self.client.get('/amministrazione/registro')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'&lt;script&gt;', r.data)
        self.assertNotIn(b'<script>alert', r.data)
        self.assertNotIn(b'type="submit">Elimina', r.data)
        self.assertEqual(self.client.post('/amministrazione/registro').status_code, 405)
        self.assertEqual(self.client.post('/amministrazione/registro/esporta').status_code, 405)

    def test_download_admin_rispetta_filtri(self):
        self.admin()
        with patch('routes.registro.leggiRegistro', return_value=self.dati) as leggi:
            r = self.client.get(
                '/amministrazione/registro/esporta?azione=MODIFICA_EVENTO&esito=Riuscito'
            )
        self.assertEqual(r.status_code, 200)
        self.assertIn('registro_attivita.log', r.headers['Content-Disposition'])
        self.assertIn(b'azione=MODIFICA_EVENTO', r.data)
        self.assertIn(b'risorsa=evento:7', r.data)
        self.assertEqual(leggi.call_args.kwargs['azione'], 'MODIFICA_EVENTO')
        self.assertIsNone(leggi.call_args.kwargs['limite'])
        self.assertEqual(self.salva.call_args.args[0]['azione'], 'ESPORTAZIONE_REGISTRO')

    def test_filtri_date_e_pagina(self):
        self.admin()
        with patch('routes.registro.leggiRegistro', return_value=self.dati) as leggi:
            self.client.get('/amministrazione/registro?dal=2026-10-01&al=2026-10-15&pagina=2')
        self.assertEqual(leggi.call_args.kwargs['dal'], datetime(2026, 10, 1))
        self.assertEqual(leggi.call_args.kwargs['al'], datetime(2026, 10, 16))
        self.assertEqual(leggi.call_args.kwargs['pagina'], 2)

    def test_filtri_non_validi_non_interrogano_db(self):
        self.admin()
        with patch('routes.registro.leggiRegistro') as leggi:
            for query in (
                'azione=INVENTATA',
                'esito=ALTRO',
                'dal=errato',
                'dal=2026-10-15&al=2026-10-01',
                'al=9999-12-31',
            ):
                self.assertEqual(
                    self.client.get('/amministrazione/registro?' + query).status_code, 200
                )
                self.assertEqual(
                    self.client.get('/amministrazione/registro/esporta?' + query).status_code, 400
                )
            leggi.assert_not_called()

    def test_login_fallito_non_salva_form_password_o_token(self):
        client = app.test_client()
        with client.session_transaction() as s:
            s['csrf_token'] = 'TOKEN-DA-NON-REGISTRARE'
        with patch('routes.account.autenticaUtente', return_value=None):
            client.post(
                '/login',
                data=dict(
                    csrf_token='TOKEN-DA-NON-REGISTRARE',
                    identificativo='account-inserito',
                    password='PASSWORD-DA-NON-REGISTRARE',
                ),
            )
        dati = self.salva.call_args.args[0]
        self.assertEqual(dati['azione'], 'LOGIN')
        self.assertEqual(dati['esito'], 'Fallito')
        self.assertIsNone(dati['id_utente'])
        self.assertNotIn('PASSWORD-DA-NON-REGISTRARE', repr(dati))
        self.assertNotIn('TOKEN-DA-NON-REGISTRARE', repr(dati))
        self.assertNotIn('account-inserito', repr(dati))

    def test_login_riuscito_ricorda_identita(self):
        client = app.test_client()
        with client.session_transaction() as s:
            s['csrf_token'] = 'token'
        with patch('routes.account.autenticaUtente', return_value=dict(UTENTE)):
            client.post(
                '/login',
                data=dict(
                    csrf_token='token', identificativo='utente_test', password='password-test'
                ),
            )
        dati = self.salva.call_args.args[0]
        self.assertEqual(
            (dati['azione'], dati['esito'], dati['id_utente']), ('LOGIN', 'Riuscito', 1)
        )

    def test_logout_conserva_autore_senza_salvare_sessione(self):
        self.client.post('/logout')
        dati = self.salva.call_args.args[0]
        self.assertEqual(
            (dati['azione'], dati['esito'], dati['id_utente']), ('LOGOUT', 'Riuscito', 1)
        )
        self.assertNotIn('csrf_token', dati)

    def test_modifica_evento_registra_campi_non_contenuto(self):
        originale = dict(
            id_evento=7,
            id_categoria=1,
            categoria='Accessi',
            indirizzo_ip='192.0.2.1',
            descrizione='Prima',
            gravita='Media',
            stato='Nuovo',
            data_evento=datetime(2026, 10, 15),
        )
        with patch('app.cercaEvento', return_value=originale), patch(
            'app.visualizzaCategorie', return_value=[]
        ), patch('app.modificaEvento', return_value=True):
            r = self.client.post(
                '/eventi/7/modifica',
                data=dict(
                    id_categoria=1,
                    indirizzo_ip='192.0.2.1',
                    descrizione='DETTAGLIO-PRIVATO',
                    gravita='Media',
                    stato='Risolto',
                ),
            )
        self.assertEqual(r.status_code, 302)
        dati = self.salva.call_args.args[0]
        self.assertEqual(dati['azione'], 'MODIFICA_EVENTO')
        self.assertEqual(dati['risorsa'], 'evento:7')
        self.assertIn('descrizione', dati['dettagli'])
        self.assertIn('stato', dati['dettagli'])
        self.assertNotIn('DETTAGLIO-PRIVATO', repr(dati))

    def test_csrf_rifiutato_viene_registrato(self):
        self.assertEqual(
            self.client.post('/logout', data={'csrf_token': 'SEGRETO-ERRATO'}).status_code, 400
        )
        dati = self.salva.call_args.args[0]
        self.assertEqual((dati['azione'], dati['esito']), ('RICHIESTA_RIFIUTATA', 'Negato'))
        self.assertNotIn('SEGRETO-ERRATO', repr(dati))

    def test_ip_non_si_fida_di_header_e_query_non_salvata(self):
        with patch('app.visualizzaEventi', return_value=[]):
            self.client.get(
                '/eventi/esporta?password=QUERY-SEGRETA', headers={'X-Forwarded-For': '203.0.113.7'}
            )
        dati = self.salva.call_args.args[0]
        self.assertEqual(dati['indirizzo_ip'], '127.0.0.1')
        self.assertEqual(dati['percorso'], '/eventi/esporta')
        self.assertNotIn('QUERY-SEGRETA', repr(dati))

    def test_reset_password_registra_operazione_senza_password_temporanea(self):
        self.admin()
        with patch('routes.account.reimpostaPassword') as reimposta:
            r = self.client.post(
                '/amministrazione/utenti',
                data=dict(
                    azione='password',
                    id_utente='2',
                    nuova_password='PASSWORD-TEMP-PRIVATA',
                ),
            )
        self.assertEqual(r.status_code, 303)
        reimposta.assert_called_once_with(2, 1, 'PASSWORD-TEMP-PRIVATA')
        dati = self.salva.call_args.args[0]
        self.assertEqual(
            (dati['azione'], dati['esito'], dati['risorsa']),
            ('RESET_PASSWORD', 'Riuscito', 'utente:2'),
        )
        self.assertNotIn('PASSWORD-TEMP-PRIVATA', repr(dati))

    def test_errore_registro_non_cambia_operazione_e_non_espone_dettagli(self):
        self.salva.side_effect = mysql.connector.Error('DETTAGLIO-RISERVATO')
        with patch('app.visualizzaEventi', return_value=[]), patch.object(
            app.logger, 'error'
        ) as log:
            r = self.client.get('/eventi/esporta')
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('DETTAGLIO-RISERVATO', repr(log.call_args))


if __name__ == '__main__':
    unittest.main()

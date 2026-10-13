"""Test di accesso e protezione dei moduli, senza scrivere sul database."""
import unittest
from unittest.mock import patch
from app import app
from test_support import UTENTE


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.config = app.config.copy()
        app.config.update(TESTING=True, SECRET_KEY='account-test')
        self.addCleanup(lambda: app.config.update(self.config))
        self.client = app.test_client()
        self.lookup = patch('database.utenti_repository.cercaUtente', return_value=dict(UTENTE))
        self.lookup.start()
        self.addCleanup(self.lookup.stop)

    def accedi(self, ruolo='utente', versione=0):
        self.lookup.stop()
        self.lookup = patch('database.utenti_repository.cercaUtente', return_value=dict(UTENTE, ruolo=ruolo))
        self.lookup.start()
        self.addCleanup(self.lookup.stop)
        with self.client.session_transaction() as s:
            s.update(id_utente=1, versione_sessione=versione, csrf_token='token')

    def test_pagine_pubbliche_e_redirect_private(self):
        for url in ('/', '/info', '/login', '/registrazione'):
            self.assertEqual(self.client.get(url).status_code, 200)
        for url in ('/dashboard', '/eventi/1', '/eventi/esporta', '/importazioni', '/amministrazione/utenti'):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302)
            self.assertTrue(r.location.endswith('/login'))

    def test_csrf_obbligatorio_anche_registrazione(self):
        with patch('routes.account.creaUtente') as crea:
            self.assertEqual(self.client.post('/registrazione', data={'username': 'nuovo'}).status_code, 400)
            crea.assert_not_called()

    def test_csrf_non_ascii_restituisce_errore_comprensibile(self):
        self.client.get('/registrazione')
        self.assertEqual(self.client.post('/registrazione', data={'csrf_token': 'non-valido-é'}).status_code, 400)

    def test_utente_non_puo_amministrare(self):
        self.accedi()
        self.assertEqual(self.client.get('/amministrazione/utenti').status_code, 403)

    def test_registrazione_ignora_ruolo_inviato(self):
        self.client.get('/registrazione')
        with self.client.session_transaction() as s:
            token = s['csrf_token']
        with patch('routes.account.creaUtente') as crea:
            r = self.client.post('/registrazione', data=dict(csrf_token=token, username='nuovo', email='nuovo@example.com', password='una-password-lunga', conferma_password='una-password-lunga', ruolo='admin'))
            self.assertEqual(r.status_code, 303)
            crea.assert_called_once_with('nuovo', 'nuovo@example.com', 'una-password-lunga')

    def test_registrazione_senza_password_non_va_in_errore_interno(self):
        self.client.get('/registrazione')
        with self.client.session_transaction() as s:
            token = s['csrf_token']
        r = self.client.post('/registrazione', data=dict(csrf_token=token, username='nuovo', email='nuovo@example.com'))
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'password deve contenere', r.data)

    def test_versione_sessione_revocata(self):
        self.accedi(versione=99)
        self.assertTrue(self.client.get('/dashboard').location.endswith('/login'))

    def test_account_disattivato_perde_accesso(self):
        self.accedi()
        with patch('database.utenti_repository.cercaUtente', return_value=dict(UTENTE, attivo=False)):
            self.assertEqual(self.client.get('/importazioni').status_code, 302)

    def test_logout_solo_post_protetto(self):
        self.accedi()
        self.assertEqual(self.client.get('/logout').status_code, 405)
        self.assertEqual(self.client.post('/logout').status_code, 400)
        self.assertEqual(self.client.post('/logout', data={'csrf_token': 'token'}).status_code, 303)
        with self.client.session_transaction() as s:
            self.assertNotIn('id_utente', s)

    def test_dashboard_e_csv_passano_proprietario(self):
        self.accedi()
        with patch('app.visualizzaEventi', return_value=[]) as elenco, patch('app.statisticheEventi', return_value={}):
            self.client.get('/dashboard')
            self.client.get('/eventi/esporta')
            for chiamata in elenco.call_args_list:
                self.assertEqual(chiamata.kwargs, dict(id_utente=1, amministratore=False))

    def test_admin_puo_consultare_tutto(self):
        self.accedi('admin')
        with patch('app.visualizzaEventi', return_value=[]) as elenco, patch('app.statisticheEventi', return_value={}):
            self.client.get('/dashboard')
            self.assertEqual(elenco.call_args.kwargs, dict(id_utente=1, amministratore=True))

    def test_risposte_private_non_memorizzate(self):
        self.accedi()
        r = self.client.get('/account')
        self.assertEqual(r.headers['Cache-Control'], 'no-store')
        self.assertEqual(r.headers['X-Content-Type-Options'], 'nosniff')


if __name__ == '__main__':
    unittest.main()

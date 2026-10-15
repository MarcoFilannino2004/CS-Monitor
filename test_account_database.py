"""Prove reali in un database temporaneo; richiedono CS_MONITOR_TEST_DB=1."""

import os
import io
import re
import uuid
import unittest
import mysql.connector
from werkzeug.security import check_password_hash
from app import app
from database.connessione import creaConnessione
from database.migrazioni import preparaAccount
from database.utenti_repository import (
    creaUtente,
    cercaUtente,
    autenticaUtente,
    gestisciUtente,
    reimpostaPassword,
)
from database.eventi_repository import visualizzaEventi
from test_importazione_log import RIGA


@unittest.skipUnless(
    os.getenv('CS_MONITOR_TEST_DB') == '1',
    'Richiede CS_MONITOR_TEST_DB=1 e MySQL con permesso di creare database di prova.',
)
class AccountDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.originale = os.getenv('DB_NAME')
        cls.nome = 'cs_monitor_test_' + uuid.uuid4().hex
        cls.config = app.config.copy()
        app.config.update(TESTING=True, SECRET_KEY='test-database')
        cls.server = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT', '3306')),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
        )
        c = cls.server.cursor()
        c.execute(f'CREATE DATABASE `{cls.nome}` CHARACTER SET utf8mb4')
        c.execute(f'USE `{cls.nome}`')
        c.execute(
            'CREATE TABLE categorie (id_categoria INT AUTO_INCREMENT PRIMARY KEY, nome VARCHAR(100)) ENGINE=InnoDB'
        )
        c.execute(
            "CREATE TABLE eventi (id_evento INT AUTO_INCREMENT PRIMARY KEY, id_categoria INT NOT NULL, indirizzo_ip VARCHAR(45), descrizione TEXT, gravita VARCHAR(20), stato VARCHAR(20), data_evento DATETIME, FOREIGN KEY (id_categoria) REFERENCES categorie(id_categoria)) ENGINE=InnoDB"
        )
        c.execute("INSERT INTO categorie (nome) VALUES ('Accessi')")
        cls.server.commit()
        c.close()
        os.environ['DB_NAME'] = cls.nome
        preparaAccount()
        preparaAccount()  # La migrazione deve poter essere ripetuta.
        cls.admin = creaUtente('admin_test', 'admin@test.example', 'password-admin-test', 'admin')

    @classmethod
    def tearDownClass(cls):
        os.environ['DB_NAME'] = cls.originale
        app.config.update(cls.config)
        # Il nome generato è verificato prima della rimozione del solo database di prova.
        assert re.fullmatch(r'cs_monitor_test_[a-f0-9]{32}', cls.nome)
        c = cls.server.cursor()
        c.execute(f'DROP DATABASE `{cls.nome}`')
        c.close()
        cls.server.close()

    def setUp(self):
        identita = uuid.uuid4().hex[:12]
        self.username = 'u_' + identita
        self.password = 'password-di-prova-123'
        self.id = creaUtente(self.username, identita + '@test.example', self.password)
        self.client = app.test_client()
        self.login(self.client, self.username, self.password)

    def token(self, client=None, url='/account'):
        client = client or self.client
        client.get(url)
        with client.session_transaction() as s:
            return s['csrf_token']

    def login(self, client, username, password):
        return client.post(
            '/login',
            data=dict(
                csrf_token=self.token(client, '/login'), identificativo=username, password=password
            ),
        )

    def post(self, url, data, client=None):
        client = client or self.client
        data['csrf_token'] = self.token(client)
        return client.post(url, data=data)

    def evento(self):
        r = self.post(
            '/eventi/nuovo',
            dict(
                id_categoria='1',
                indirizzo_ip='192.0.2.1',
                descrizione='Evento privato',
                gravita='Alta',
            ),
        )
        self.assertEqual(r.status_code, 302)
        return visualizzaEventi(id_utente=self.id)[0]['id_evento']

    def importazione(self):
        r = self.post('/eventi/importa', {'file_log': (io.BytesIO(RIGA.encode()), 'prova.log')})
        token = re.search(r'name="anteprima" value="([^"]+)"', r.get_data(as_text=True)).group(1)
        dati = dict(azione='conferma', anteprima=token, selezionati='1', categoria_1='1')
        r = self.post('/eventi/importa', dict(dati))
        self.assertEqual(r.status_code, 303)
        return r.location, dati

    def risolvi(self, id_evento):
        from database.strumenti import apriCursore

        with apriCursore() as (connessione, cursore):
            cursore.execute("UPDATE eventi SET stato='Risolto' WHERE id_evento=%s", (id_evento,))
            connessione.commit()

    def test_risolti_esportazione_elimina_solo_propri_e_preserva_originale(self):
        from database.eventi_repository import cercaEvento, inserisciEvento
        from models.evento_sicurezza import EventoSicurezza

        importazione, _ = self.importazione()
        risolto = visualizzaEventi(id_utente=self.id)[0]['id_evento']
        self.risolvi(risolto)
        nuovo = self.evento()
        altro = creaUtente(
            'altro_' + uuid.uuid4().hex[:8], uuid.uuid4().hex + '@test.example', self.password
        )
        estraneo = inserisciEvento(
            EventoSicurezza(None, 1, '192.0.2.3', 'Evento altrui', 'Media', 'Risolto'),
            id_utente=altro,
        )
        self.post('/eventi/risolti/elimina', {'conferma': 'si'})
        self.assertIsNotNone(cercaEvento(risolto, id_utente=self.id))
        csv = self.client.get('/eventi/risolti/esporta')
        self.assertIn(b'Login fallito per utente admin', csv.data)
        self.assertNotIn(b'Evento altrui', csv.data)
        self.assertNotIn(b'Evento privato', csv.data)
        self.assertEqual(self.post('/eventi/risolti/elimina', {'conferma': 'si'}).status_code, 303)
        self.assertIsNone(cercaEvento(risolto, id_utente=self.id))
        self.assertIsNotNone(cercaEvento(nuovo, id_utente=self.id))
        self.assertIsNotNone(cercaEvento(estraneo, id_utente=altro))
        self.assertEqual(self.client.get(importazione + '/file').data, RIGA.encode())

    def test_risolti_modificati_o_aggiunti_richiedono_nuovo_csv(self):
        from database.eventi_repository import cercaEvento
        from database.strumenti import apriCursore

        risolto = self.evento()
        self.risolvi(risolto)
        self.client.get('/eventi/risolti/esporta')
        aggiunto = self.evento()
        self.risolvi(aggiunto)
        self.post('/eventi/risolti/elimina', {'conferma': 'si'})
        self.assertIsNotNone(cercaEvento(risolto, id_utente=self.id))
        self.assertIsNotNone(cercaEvento(aggiunto, id_utente=self.id))
        self.client.get('/eventi/risolti/esporta')
        with apriCursore() as (connessione, cursore):
            cursore.execute("UPDATE eventi SET stato='In analisi' WHERE id_evento=%s", (risolto,))
            connessione.commit()
        self.post('/eventi/risolti/elimina', {'conferma': 'si'})
        self.assertEqual(cercaEvento(risolto, id_utente=self.id)['stato'], 'In analisi')
        self.assertIsNotNone(cercaEvento(aggiunto, id_utente=self.id))
        self.client.get('/eventi/risolti/esporta')
        self.post('/eventi/risolti/elimina', {'conferma': 'si'})
        self.assertIsNone(cercaEvento(aggiunto, id_utente=self.id))
        self.assertIsNotNone(cercaEvento(risolto, id_utente=self.id))

    def test_risolti_amministratore_esporta_ed_elimina_di_tutti(self):
        from database.eventi_repository import cercaEvento

        risolto = self.evento()
        self.risolvi(risolto)
        nuovo = self.evento()
        amministratore = app.test_client()
        self.login(amministratore, 'admin_test', 'password-admin-test')
        csv = amministratore.get('/eventi/risolti/esporta')
        self.assertEqual(csv.status_code, 200)
        self.assertEqual(
            self.post('/eventi/risolti/elimina', {'conferma': 'si'}, amministratore).status_code,
            303,
        )
        self.assertEqual(visualizzaEventi(stato='Risolto', amministratore=True), [])
        self.assertIsNone(cercaEvento(risolto, amministratore=True))
        self.assertIsNotNone(cercaEvento(nuovo, id_utente=self.id))

    def test_registro_operazioni_restano_dopo_eliminazione_evento(self):
        from unittest.mock import patch
        from database.registro_repository import leggiRegistro

        with patch.dict(app.config, {'REGISTRO_ATTIVITA_NEI_TEST': True}):
            evento = self.evento()
            self.post(
                f'/eventi/{evento}/modifica',
                dict(
                    id_categoria=1,
                    indirizzo_ip='192.0.2.1',
                    descrizione='Contenuto privato non da copiare nel registro',
                    gravita='Alta',
                    stato='Risolto',
                ),
            )
            self.client.get('/eventi/risolti/esporta')
            self.post('/eventi/risolti/elimina', {'conferma': 'si'})
        righe = leggiRegistro(testo=self.username, limite=None)['attivita']
        azioni = {r['azione'] for r in righe}
        self.assertTrue(
            {
                'CREAZIONE_EVENTO',
                'MODIFICA_EVENTO',
                'ESPORTAZIONE_RISOLTI',
                'ELIMINAZIONE_RISOLTI',
            }.issubset(azioni)
        )
        self.assertTrue(any(r['risorsa'] == f'evento:{evento}' for r in righe))
        self.assertNotIn('Contenuto privato non da copiare nel registro', repr(righe))
        self.assertEqual(visualizzaEventi(id_utente=self.id), [])

    def test_registro_filtri_paginazione_download_e_permessi_su_db(self):
        from unittest.mock import patch
        from database.registro_repository import leggiRegistro
        from database.strumenti import apriCursore

        with apriCursore() as (connessione, cursore):
            cursore.executemany(
                """INSERT INTO registro_attivita
                (id_utente, username, indirizzo_ip, azione, esito, risorsa, dettagli, metodo, percorso, codice_http)
                VALUES (%s,%s,'192.0.2.20','MODIFICA_EVENTO','Riuscito',%s,'Campi aggiornati: stato','POST','/eventi/<int:id_evento>/modifica',302)""",
                [(self.id, self.username, f'evento:{i}') for i in range(51)],
            )
            connessione.commit()
        prima = leggiRegistro(testo=self.username)
        seconda = leggiRegistro(testo=self.username, pagina=2)
        self.assertEqual((prima['totale'], len(prima['attivita']), prima['pagine']), (51, 50, 2))
        self.assertEqual(len(seconda['attivita']), 1)
        self.assertEqual(leggiRegistro(testo=self.username, esito='Negato')['totale'], 0)
        admin = app.test_client()
        self.login(admin, 'admin_test', 'password-admin-test')
        with patch.dict(app.config, {'REGISTRO_ATTIVITA_NEI_TEST': True}):
            self.assertEqual(self.client.get('/amministrazione/registro').status_code, 403)
            self.assertEqual(self.client.get('/amministrazione/registro/esporta').status_code, 403)
            pagina = admin.get('/amministrazione/registro?testo=' + self.username)
            self.assertEqual(pagina.status_code, 200)
            download = admin.get('/amministrazione/registro/esporta?testo=' + self.username)
        self.assertEqual(download.status_code, 200)
        # I due accessi negati dello stesso utente sono anch'essi nel registro.
        self.assertEqual(len(download.data.decode().splitlines()), 53)
        self.assertIn(b'WARNING', download.data)

    def test_registro_migrazione_non_cancella_la_cronologia(self):
        from database.registro_repository import inserisciAttivita, leggiRegistro

        inserisciAttivita(
            dict(
                id_utente=self.id,
                username=self.username,
                indirizzo_ip='192.0.2.1',
                azione='LOGIN',
                esito='Riuscito',
                risorsa='',
                dettagli='Accesso riuscito.',
                metodo='POST',
                percorso='/login',
                codice_http=303,
            )
        )
        preparaAccount()
        preparaAccount()
        self.assertEqual(leggiRegistro(testo=self.username)['totale'], 1)

    def test_password_hash_e_login_email(self):
        u = cercaUtente(self.id)
        self.assertNotEqual(u['password_hash'], self.password)
        self.assertTrue(check_password_hash(u['password_hash'], self.password))
        self.assertEqual(autenticaUtente(u['email'], self.password)['id_utente'], self.id)

    def test_repository_senza_proprietario_non_espone_eventi(self):
        from database.eventi_repository import cercaEvento, eliminaEvento, statisticheEventi

        evento = self.evento()
        self.assertEqual(visualizzaEventi(), [])
        self.assertIsNone(cercaEvento(evento))
        self.assertFalse(eliminaEvento(evento))
        self.assertEqual(statisticheEventi()['totale'], 0)
        self.assertEqual(self.client.get(f'/eventi/{evento}').status_code, 200)

    def test_categorie_predefinite_conservano_esistenti_e_non_duplicano(self):
        from database.categorie_repository import (
            aggiungiCategoriePredefinite,
            visualizzaCategorie,
            CATEGORIE_PREDEFINITE,
        )

        prima = {c['id_categoria']: c['nome'] for c in visualizzaCategorie()}
        aggiungiCategoriePredefinite()
        dopo = {c['id_categoria']: c['nome'] for c in visualizzaCategorie()}
        for id_categoria, nome in prima.items():
            self.assertEqual(dopo[id_categoria], nome)
        self.assertTrue(set(CATEGORIE_PREDEFINITE).issubset(set(dopo.values())))
        self.assertEqual(aggiungiCategoriePredefinite(), 0)
        self.assertEqual(len(visualizzaCategorie()), len(dopo))

    def test_isolamento_lettura_modifica_elimina_csv_statistiche(self):
        evento = self.evento()
        altro = creaUtente(
            'altro_' + uuid.uuid4().hex[:8], uuid.uuid4().hex + '@test.example', self.password
        )
        client = app.test_client()
        u = cercaUtente(altro)
        self.login(client, u['username'], self.password)
        for suffix in ('', '/modifica'):
            self.assertEqual(client.get(f'/eventi/{evento}{suffix}').status_code, 404)
        self.assertEqual(self.post(f'/eventi/{evento}/elimina', {}, client).status_code, 404)
        self.assertEqual(
            self.post(
                f'/eventi/{evento}/modifica',
                dict(
                    id_categoria=1,
                    indirizzo_ip='192.0.2.2',
                    descrizione='Tentativo',
                    gravita='Bassa',
                    stato='Nuovo',
                ),
                client,
            ).status_code,
            404,
        )
        self.assertNotIn(b'Evento privato', client.get('/eventi/esporta').data)
        self.assertNotIn(b'Evento privato', client.get('/dashboard').data)
        self.assertEqual(len(visualizzaEventi(id_utente=altro)), 0)
        self.assertEqual(self.client.get(f'/eventi/{evento}').status_code, 200)

    def test_importazione_storico_download_e_doppio_invio(self):
        url, dati = self.importazione()
        self.assertIn(b'Importazione completata', self.client.get(url).data)
        self.assertEqual(self.client.get(url + '/file').data, RIGA.encode())
        self.assertIn(b'prova.log', self.client.get('/importazioni').data)
        self.assertIn(b'Login fallito per utente admin', self.client.get(url).data)
        r = self.post('/eventi/importa', dati)
        self.assertIn('già stato importato', r.get_data(as_text=True))
        self.assertEqual(len(visualizzaEventi(id_utente=self.id)), 1)
        estraneo = app.test_client()
        self.login(estraneo, 'admin_test', 'password-admin-test')
        self.assertEqual(estraneo.get(url + '/file').status_code, 200)
        altro = creaUtente(
            'estraneo_' + uuid.uuid4().hex[:8], uuid.uuid4().hex + '@test.example', self.password
        )
        estraneo = app.test_client()
        self.login(estraneo, cercaUtente(altro)['username'], self.password)
        self.assertEqual(estraneo.get(url).status_code, 404)
        self.assertEqual(estraneo.get(url + '/file').status_code, 404)
        r = self.post('/eventi/importa', dict(dati), estraneo)
        self.assertIn(b'altro account', r.data)
        self.assertEqual(len(visualizzaEventi(id_utente=altro)), 0)

    def test_cambio_password_revoca_sessioni(self):
        secondo = app.test_client()
        self.login(secondo, self.username, self.password)
        r = self.post(
            '/account',
            dict(
                azione='password',
                password_attuale=self.password,
                nuova_password='nuova-password-1234',
                conferma_password='nuova-password-1234',
            ),
        )
        self.assertEqual(r.status_code, 303)
        self.assertEqual(secondo.get('/dashboard').status_code, 302)
        self.assertIsNone(autenticaUtente(self.username, self.password))
        self.assertIsNotNone(autenticaUtente(self.username, 'nuova-password-1234'))

    def test_disattivazione_riattivazione_conserva_dati(self):
        evento = self.evento()
        gestisciUtente(self.id, self.admin, 'utente', False)
        self.assertEqual(self.client.get('/dashboard').status_code, 302)
        self.assertIsNone(autenticaUtente(self.username, self.password))
        gestisciUtente(self.id, self.admin, 'utente', True)
        self.login(self.client, self.username, self.password)
        self.assertEqual(self.client.get(f'/eventi/{evento}').status_code, 200)

    def test_blocco_e_sblocco_login(self):
        for _ in range(5):
            self.assertIsNone(autenticaUtente(self.username, 'password-errata'))
        self.assertIsNone(autenticaUtente(self.username, self.password))
        gestisciUtente(self.id, self.admin, 'utente', True)
        self.assertIsNotNone(autenticaUtente(self.username, self.password))

    def test_reset_password_richiede_cambio_e_revoca_sessioni(self):
        reimpostaPassword(self.id, self.admin, 'password-temporanea-123')
        self.assertEqual(self.client.get('/dashboard').status_code, 302)
        self.assertEqual(
            self.login(self.client, self.username, 'password-temporanea-123').status_code, 303
        )
        self.assertTrue(self.client.get('/dashboard').location.endswith('/account'))
        self.assertIn(b'password temporanea', self.client.get('/account').data)
        r = self.post(
            '/account',
            dict(
                azione='password',
                password_attuale='password-temporanea-123',
                nuova_password='password-scelta-utente-123',
                conferma_password='password-scelta-utente-123',
            ),
        )
        self.assertEqual(r.status_code, 303)
        self.login(self.client, self.username, 'password-scelta-utente-123')
        self.assertEqual(self.client.get('/dashboard').status_code, 200)

    def test_importazione_fallita_annulla_file_ed_eventi(self):
        from database.importazioni_repository import salvaImportazione, visualizzaImportazioni
        from models.evento_sicurezza import EventoSicurezza

        e = EventoSicurezza(None, 99999, '192.0.2.1', 'Categoria inesistente', 'Alta')
        with self.assertRaises(mysql.connector.IntegrityError):
            salvaImportazione([e], self.id, 'prova.log', RIGA.encode(), 1, 0, uuid.uuid4().hex)
        self.assertEqual(visualizzaImportazioni(self.id), [])
        self.assertEqual(visualizzaEventi(id_utente=self.id), [])

    def test_admin_protetto_e_modifica_ruolo(self):
        with self.assertRaises(ValueError):
            gestisciUtente(self.admin, self.admin, 'utente', False)
        gestisciUtente(self.id, self.admin, 'admin', True)
        self.login(self.client, self.username, self.password)
        self.assertEqual(self.client.get('/amministrazione/utenti').status_code, 200)
        gestisciUtente(self.id, self.admin, 'utente', True)
        self.login(self.client, self.username, self.password)
        self.assertEqual(self.client.get('/amministrazione/utenti').status_code, 403)

    def test_registrazione_pubblica_duplicati_e_profilo(self):
        client = app.test_client()
        nome = 'registrato_' + uuid.uuid4().hex[:8]
        dati = dict(
            username=nome,
            email=nome + '@test.example',
            password=self.password,
            conferma_password=self.password,
            ruolo='admin',
        )
        dati['csrf_token'] = self.token(client, '/registrazione')
        self.assertEqual(client.post('/registrazione', data=dati).status_code, 303)
        self.assertEqual(autenticaUtente(nome, self.password)['ruolo'], 'utente')
        self.assertIn(
            'già utilizzati', client.post('/registrazione', data=dati).get_data(as_text=True)
        )
        r = self.post(
            '/account',
            dict(
                azione='profilo',
                username=self.username + '_edit',
                email='edit_' + uuid.uuid4().hex + '@test.example',
            ),
        )
        self.assertEqual(r.status_code, 303)
        self.assertEqual(cercaUtente(self.id)['username'], self.username + '_edit')


if __name__ == '__main__':
    unittest.main()

from unittest.mock import patch

UTENTE = dict(id_utente=1, username='utente_test', email='test@example.com', ruolo='utente', attivo=True, versione_sessione=0)


def preparaClient(test, app):
    test.utente_patch = patch('database.utenti_repository.cercaUtente', return_value=UTENTE)
    test.utente_patch.start()
    test.addCleanup(test.utente_patch.stop)
    client = app.test_client()
    with client.session_transaction() as session:
        session.update(id_utente=1, versione_sessione=0, csrf_token='csrf-test')
    originale = client.post
    def post(url, **kwargs):
        dati = dict(kwargs.pop('data', {}))
        dati.setdefault('csrf_token', 'csrf-test')
        return originale(url, data=dati, **kwargs)
    client.post = post
    return client

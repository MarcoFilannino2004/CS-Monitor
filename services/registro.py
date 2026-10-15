"""Registra azioni significative senza copiare password, form, cookie o token."""

import re
from ipaddress import ip_address
from flask import g, request, current_app
import mysql.connector
from database.registro_repository import inserisciAttivita

AZIONI_POST = {
    'account.login': 'LOGIN',
    'account.logout': 'LOGOUT',
    'account.registrazione': 'REGISTRAZIONE',
    'account.profilo': 'MODIFICA_PROFILO',
    'account.amministrazione': 'GESTIONE_ACCOUNT',
    'nuovoEvento': 'CREAZIONE_EVENTO',
    'modificaEventoPagina': 'MODIFICA_EVENTO',
    'eliminaEventoPagina': 'ELIMINAZIONE_EVENTO',
    'importaLog': 'ANALISI_LOG',
    'eliminaRisolti': 'ELIMINAZIONE_RISOLTI',
}
AZIONI_GET = {
    'dashboard': 'CONSULTAZIONE_DASHBOARD',
    'dettagliEvento': 'CONSULTAZIONE_EVENTO',
    'eventiRisolti': 'CONSULTAZIONE_RISOLTI',
    'storicoImportazioni': 'CONSULTAZIONE_STORICO',
    'dettagliImportazione': 'CONSULTAZIONE_IMPORTAZIONE',
    'scaricaLog': 'DOWNLOAD_LOG',
    'esportaEventi': 'ESPORTAZIONE_CSV',
    'esportaRisolti': 'ESPORTAZIONE_RISOLTI',
    'account.profilo': 'CONSULTAZIONE_PROFILO',
    'account.amministrazione': 'CONSULTAZIONE_ACCOUNT',
    'registro.pagina': 'CONSULTAZIONE_REGISTRO',
    'registro.esporta': 'ESPORTAZIONE_REGISTRO',
}
AZIONI = sorted(
    set(AZIONI_POST.values())
    | set(AZIONI_GET.values())
    | {
        'CAMBIO_PASSWORD',
        'CREAZIONE_ACCOUNT',
        'RESET_PASSWORD',
        'IMPORTAZIONE_LOG',
        'ACCESSO_NEGATO',
        'ACCESSO_NON_AUTENTICATO',
        'RICHIESTA_RIFIUTATA',
    }
)
ESITI = ('Riuscito', 'Fallito', 'Negato')


def testoSicuro(valore, lunghezza):
    # Una sola riga per voce, anche nel file scaricabile.
    return re.sub(r'[\x00-\x1f\x7f\u2028\u2029]', ' ', str(valore or '')).strip()[:lunghezza]


def segnaAttivita(azione, esito='Riuscito', risorsa='', dettagli='', utente=None):
    g.attivita_registro = dict(
        azione=azione, esito=esito, risorsa=risorsa, dettagli=dettagli, utente=utente
    )


def azioneRichiesta(codice):
    azione = (AZIONI_POST if request.method == 'POST' else AZIONI_GET).get(request.endpoint)
    if request.method == 'POST' and codice < 400:
        if request.endpoint == 'account.profilo' and request.form.get('azione') == 'password':
            return 'CAMBIO_PASSWORD'
        if request.endpoint == 'account.amministrazione':
            return {'crea': 'CREAZIONE_ACCOUNT', 'password': 'RESET_PASSWORD'}.get(
                request.form.get('azione'), 'GESTIONE_ACCOUNT'
            )
        if request.endpoint == 'importaLog' and request.form.get('azione') == 'conferma':
            return 'IMPORTAZIONE_LOG'
    return azione


def configuraRegistro(app):
    @app.after_request
    def registraRichiesta(risposta):
        # Le suite simulate non devono scrivere accidentalmente nel DB reale.
        if request.endpoint == 'static':
            return risposta
        if app.testing and not app.config.get('REGISTRO_ATTIVITA_NEI_TEST', False):
            return risposta
        if (
            request.endpoint == 'account.login'
            and getattr(g, 'utente', None)
            and risposta.status_code == 302
        ):
            return risposta
        dati = getattr(g, 'attivita_registro', None)
        if dati is None:
            azione = azioneRichiesta(risposta.status_code)
            if risposta.status_code == 403:
                azione = 'ACCESSO_NEGATO'
            if azione is None and risposta.status_code >= 400:
                azione = 'RICHIESTA_RIFIUTATA'
            if azione is None:
                return risposta
            esito = (
                'Riuscito' if request.method == 'GET' and risposta.status_code == 200 else 'Fallito'
            )
            if request.endpoint == 'account.logout' and risposta.status_code == 303:
                esito = 'Riuscito'
            dettagli = 'Operazione non completata.' if esito == 'Fallito' else ''
            if azione == 'LOGIN' and esito == 'Fallito':
                dettagli = (
                    'Accesso non riuscito: credenziali non valide, account inattivo o bloccato.'
                )
            dati = dict(azione=azione, esito=esito, risorsa='', dettagli=dettagli, utente=None)
        utente = dati.get('utente') or getattr(g, 'utente', None) or {}
        identificativo = utente.get('id_utente')
        if type(identificativo) is not int:
            identificativo = None
        risorsa = dati.get('risorsa')
        if not risorsa:
            argomenti = request.view_args or {}
            for campo, nome in [('id_evento', 'evento'), ('id_importazione', 'importazione')]:
                if type(argomenti.get(campo)) is int:
                    risorsa = f'{nome}:{argomenti[campo]}'
                    break
        try:
            indirizzo = str(ip_address(request.remote_addr))
        except ValueError:
            indirizzo = None
        try:
            inserisciAttivita(
                dict(
                    id_utente=identificativo,
                    username=testoSicuro(utente.get('username', 'Non autenticato'), 40),
                    indirizzo_ip=indirizzo,
                    azione=testoSicuro(dati['azione'], 64),
                    esito=dati['esito'],
                    risorsa=testoSicuro(risorsa, 100),
                    dettagli=testoSicuro(dati.get('dettagli'), 500),
                    metodo=request.method[:10],
                    percorso=(request.url_rule.rule if request.url_rule else '')[:255],
                    codice_http=risposta.status_code,
                )
            )
        except mysql.connector.Error:
            # Non trasforma un'operazione già completata in un errore o un doppio invio.
            current_app.logger.error('Registro attività non disponibile: scrittura non riuscita.')
        return risposta

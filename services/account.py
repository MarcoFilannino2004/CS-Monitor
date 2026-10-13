import re
from functools import wraps
from datetime import timedelta
import secrets
from flask import g, session, request, abort, redirect, url_for

USERNAME = re.compile(r"^[A-Za-z0-9_.-]{3,40}$")
EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def validaAccount(username, email, password=None):
    username = (username or '').strip()
    email = (email or '').strip().lower()
    if not USERNAME.fullmatch(username):
        raise ValueError('Il nome utente deve contenere da 3 a 40 lettere, numeri, punti, trattini o underscore.')
    if len(email) > 254 or not EMAIL.fullmatch(email):
        raise ValueError('Inserisci un indirizzo email valido.')
    if password is not None:
        validaPassword(password)
    return username, email


def validaPassword(password):
    if not isinstance(password, str) or not 10 <= len(password) <= 128:
        raise ValueError('La password deve contenere da 10 a 128 caratteri.')


def tokenCsrf():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return session['csrf_token']


def soloAdmin(funzione):
    @wraps(funzione)
    def protetta(*args, **kwargs):
        if g.utente is None or g.utente['ruolo'] != 'admin':
            abort(403)
        return funzione(*args, **kwargs)
    return protetta


def configuraSicurezza(app):
    from database import utenti_repository
    pubbliche = {'home', 'info', 'static', 'account.login', 'account.registrazione'}
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
                      PERMANENT_SESSION_LIFETIME=timedelta(hours=2))

    @app.before_request
    def caricaSessione():
        g.utente = None
        id_utente = session.get('id_utente')
        if id_utente is not None:
            utente = utenti_repository.cercaUtente(id_utente)
            if utente and utente['attivo'] and utente['versione_sessione'] == session.get('versione_sessione'):
                g.utente = utente
            else:
                session.clear()
        if request.endpoint is not None and request.endpoint not in pubbliche and g.utente is None:
            return redirect(url_for('account.login'))
        if request.method == 'POST':
            inviato = request.form.get('csrf_token', '')
            atteso = session.get('csrf_token', '')
            if not atteso or not secrets.compare_digest(inviato.encode('utf-8'), atteso.encode('utf-8')):
                abort(400, description='Il modulo è scaduto o non valido. Ricarica la pagina e riprova.')
        if (g.utente and g.utente.get('password_da_cambiare') and request.endpoint is not None
                and request.endpoint not in pubbliche | {'account.profilo', 'account.logout'}):
            return redirect(url_for('account.profilo'))

    @app.context_processor
    def datiAccount():
        return {'utente_corrente': getattr(g, 'utente', None), 'csrf_token': tokenCsrf}

    @app.after_request
    def intestazioniSicure(risposta):
        risposta.headers['X-Content-Type-Options'] = 'nosniff'
        risposta.headers['X-Frame-Options'] = 'SAMEORIGIN'
        risposta.headers['Referrer-Policy'] = 'same-origin'
        if getattr(g, 'utente', None) is not None or request.endpoint in {'account.login', 'account.registrazione'}:
            risposta.headers['Cache-Control'] = 'no-store'
        return risposta

from flask import Blueprint, render_template, request, redirect, url_for, session, g, flash
from database.utenti_repository import (
    creaUtente,
    autenticaUtente,
    aggiornaProfilo,
    cambiaPassword,
    visualizzaUtenti,
    gestisciUtente,
    reimpostaPassword,
)
from services.account import soloAdmin

account = Blueprint('account', __name__)


@account.route('/registrazione', methods=['GET', 'POST'])
def registrazione():
    errore = None
    if request.method == 'POST':
        try:
            if request.form.get('password') != request.form.get('conferma_password'):
                raise ValueError('Le password non coincidono.')
            # Il ruolo pubblico è sempre utente, indipendentemente dai dati inviati.
            creaUtente(
                request.form.get('username'),
                request.form.get('email'),
                request.form.get('password'),
            )
            flash('Registrazione completata. Ora puoi accedere.', 'success')
            return redirect(url_for('account.login'), code=303)
        except ValueError as e:
            errore = str(e)
    return render_template('registrazione.html', errore=errore)


@account.route('/login', methods=['GET', 'POST'])
def login():
    if g.utente:
        return redirect(url_for('dashboard'))
    errore = None
    if request.method == 'POST':
        utente = autenticaUtente(
            request.form.get('identificativo'), request.form.get('password', '')
        )
        if utente:
            session.clear()
            session.update(
                id_utente=utente['id_utente'], versione_sessione=utente['versione_sessione']
            )
            session.permanent = True
            return redirect(url_for('dashboard'), code=303)
        errore = 'Accesso non riuscito. Controlla i dati. Dopo 5 tentativi errati attendi 15 minuti o contatta un amministratore.'
    return render_template('login.html', errore=errore)


@account.post('/logout')
def logout():
    session.clear()
    return redirect(url_for('account.login'), code=303)


@account.route('/account', methods=['GET', 'POST'])
def profilo():
    errore = None
    if request.method == 'POST':
        try:
            if request.form.get('azione') == 'password':
                if request.form.get('nuova_password') != request.form.get('conferma_password'):
                    raise ValueError('Le nuove password non coincidono.')
                cambiaPassword(
                    g.utente['id_utente'],
                    request.form.get('password_attuale', ''),
                    request.form.get('nuova_password'),
                )
                session.clear()
                flash(
                    'Password cambiata. Accedi nuovamente: tutte le vecchie sessioni sono state chiuse.',
                    'success',
                )
                return redirect(url_for('account.login'), code=303)
            aggiornaProfilo(
                g.utente['id_utente'], request.form.get('username'), request.form.get('email')
            )
            flash('Profilo aggiornato.', 'success')
            return redirect(url_for('account.profilo'), code=303)
        except ValueError as e:
            errore = str(e)
    return render_template('profilo.html', errore=errore)


@account.route('/amministrazione/utenti', methods=['GET', 'POST'])
@soloAdmin
def amministrazione():
    errore = None
    if request.method == 'POST':
        try:
            if request.form.get('azione') == 'crea':
                creaUtente(
                    request.form.get('username'),
                    request.form.get('email'),
                    request.form.get('password'),
                    request.form.get('ruolo', 'utente'),
                    cambio_password=True,
                )
                flash('Account creato.', 'success')
            elif request.form.get('azione') == 'password':
                id_utente = request.form.get('id_utente', type=int)
                if not id_utente:
                    raise ValueError('Account non valido.')
                reimpostaPassword(
                    id_utente, g.utente['id_utente'], request.form.get('nuova_password')
                )
                flash(
                    'Password temporanea impostata. L’utente dovrà cambiarla al prossimo accesso.',
                    'success',
                )
            else:
                id_utente = request.form.get('id_utente', type=int)
                if not id_utente:
                    raise ValueError('Account non valido.')
                gestisciUtente(
                    id_utente,
                    g.utente['id_utente'],
                    request.form.get('ruolo'),
                    request.form.get('attivo') == '1',
                )
                flash(
                    'Account aggiornato. Le sessioni precedenti e il blocco per tentativi errati sono stati azzerati.',
                    'success',
                )
            return redirect(url_for('account.amministrazione'), code=303)
        except ValueError as e:
            errore = str(e)
    return render_template('amministrazione.html', utenti=visualizzaUtenti(), errore=errore)

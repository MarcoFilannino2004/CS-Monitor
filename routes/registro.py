from datetime import datetime, timedelta
from io import BytesIO
from flask import Blueprint, render_template, request, abort, send_file
from database.registro_repository import leggiRegistro
from services.account import soloAdmin
from services.registro import AZIONI, ESITI, testoSicuro

registro = Blueprint('registro', __name__)


def filtriRegistro():
    azione = request.args.get('azione', '')
    esito = request.args.get('esito', '')
    testo = request.args.get('testo', '').strip()[:100]
    if (azione and azione not in AZIONI) or (esito and esito not in ESITI):
        raise ValueError('Azione o esito non valido.')
    date = {}
    for campo in ('dal', 'al'):
        valore = request.args.get(campo, '')
        try:
            date[campo] = datetime.strptime(valore, '%Y-%m-%d') if valore else None
        except ValueError:
            raise ValueError('Inserisci date valide.') from None
    if date['dal'] and date['al'] and date['dal'] > date['al']:
        raise ValueError('La data iniziale deve precedere quella finale.')
    if date['al']:
        try:
            date['al'] += timedelta(days=1)
        except OverflowError:
            raise ValueError('La data finale non è valida.') from None
    return dict(azione=azione, esito=esito, testo=testo, **date)


@registro.get('/amministrazione/registro')
@soloAdmin
def pagina():
    errore = None
    try:
        filtri = filtriRegistro()
        dati = leggiRegistro(**filtri, pagina=request.args.get('pagina', 1, type=int))
    except ValueError as e:
        errore = str(e)
        dati = dict(attivita=[], totale=0, pagina=1, pagine=1)
    parametri = {k: request.args.get(k, '') for k in ('azione', 'esito', 'testo', 'dal', 'al')}
    return render_template(
        'registro_attivita.html',
        **dati,
        azioni=AZIONI,
        esiti=ESITI,
        filtri=parametri,
        errore=errore,
    )


@registro.get('/amministrazione/registro/esporta')
@soloAdmin
def esporta():
    try:
        dati = leggiRegistro(**filtriRegistro(), limite=None)
    except ValueError as e:
        abort(400, description=str(e))
    righe = []
    for r in dati['attivita']:
        livello = {'Riuscito': 'INFO', 'Fallito': 'ERROR', 'Negato': 'WARNING'}[r['esito']]
        messaggio = '; '.join(
            [
                f"azione={r['azione']}",
                f"utente={r['username']}",
                f"id_utente={r['id_utente'] or '-'}",
                f"risorsa={r['risorsa'] or '-'}",
                f"esito={r['esito']}",
                f"HTTP={r['codice_http']}",
                f"percorso={r['percorso']}",
                r['dettagli'],
            ]
        )
        righe.append(
            f"{r['data_attivita']:%Y-%m-%d %H:%M:%S} | {r['indirizzo_ip'] or '-'} | {livello} | {testoSicuro(messaggio, 1200)}"
        )
    contenuto = ('\n'.join(righe) + ('\n' if righe else '')).encode('utf-8')
    return send_file(
        BytesIO(contenuto),
        mimetype='text/plain',
        as_attachment=True,
        download_name='registro_attivita.log',
    )

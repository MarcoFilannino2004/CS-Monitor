from flask import Flask, render_template, abort, request, redirect, url_for, send_file, flash, g
from database.eventi_repository import (
    visualizzaEventi,
    cercaEvento,
    inserisciEvento,
    modificaEvento,
    eliminaEvento,
    statisticheEventi,
)
from models.evento_sicurezza import EventoSicurezza
from database.categorie_repository import visualizzaCategorie
import mysql.connector
import os
import csv
import secrets
import base64
from werkzeug.utils import secure_filename
from services.account import configuraSicurezza
from routes.account import account
from database.importazioni_repository import (
    salvaImportazione,
    visualizzaImportazioni,
    cercaImportazione,
)
from io import BytesIO, StringIO
from datetime import datetime
from itsdangerous import URLSafeTimedSerializer, BadSignature
from services.log_importer import analizzaLog, MAX_BYTES

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
app.config["MAX_FORM_MEMORY_SIZE"] = 2 * 1024 * 1024
app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
app.register_blueprint(account)
configuraSicurezza(app)


def ambitoEventi():
    return dict(id_utente=g.utente['id_utente'], amministratore=g.utente['ruolo'] == 'admin')


@app.errorhandler(400)
@app.errorhandler(403)
def richiestaNonConsentita(errore):
    return (
        render_template('errore_account.html', messaggio=errore.description, codice=errore.code),
        errore.code,
    )


@app.get('/importazioni')
def storicoImportazioni():
    return render_template(
        'importazioni.html', importazioni=visualizzaImportazioni(**ambitoEventi())
    )


@app.get('/importazioni/<int:id_importazione>')
def dettagliImportazione(id_importazione):
    importazione = cercaImportazione(id_importazione, **ambitoEventi())
    if importazione is None:
        abort(404)
    eventi = visualizzaEventi(id_importazione=id_importazione, **ambitoEventi())
    return render_template('dettagli_importazione.html', importazione=importazione, eventi=eventi)


@app.get('/importazioni/<int:id_importazione>/file')
def scaricaLog(id_importazione):
    importazione = cercaImportazione(id_importazione, **ambitoEventi())
    if importazione is None:
        abort(404)
    return send_file(
        BytesIO(importazione['contenuto']),
        mimetype='text/plain',
        as_attachment=True,
        download_name=importazione['nome_file'],
    )


@app.errorhandler(mysql.connector.Error)
def erroreDatabase(errore):
    app.logger.error("Operazione sul database non riuscita.")
    return render_template("errore_database.html"), 503


@app.errorhandler(413)
def richiestaTroppoGrande(errore):
    return (
        render_template(
            "importa_log.html",
            errore="Caricamento troppo grande. Il file deve essere al massimo di 256 KB.",
        ),
        413,
    )


@app.route("/eventi/importa", methods=["GET", "POST"])
def importaLog():
    eventi, errori, categorie = [], [], []
    errore = messaggio = token = None
    firma = URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="importazione-log")
    if request.method == "POST":
        try:
            if request.form.get("azione") == "conferma":
                token = request.form.get("anteprima", "")
                try:
                    anteprima = firma.loads(token, max_age=1800)
                    campi = {
                        'id_utente',
                        'eventi',
                        'nome_file',
                        'contenuto',
                        'righe_errate',
                        'identificativo',
                    }
                    if not isinstance(anteprima, dict) or not campi.issubset(anteprima):
                        raise ValueError('Anteprima non valida. Carica nuovamente il file.')
                    if anteprima['id_utente'] != g.utente['id_utente']:
                        raise ValueError('Questa anteprima appartiene a un altro account.')
                    eventi = anteprima['eventi']
                except BadSignature:
                    token = None
                    raise ValueError(
                        "Anteprima scaduta o non valida. Carica nuovamente il file."
                    ) from None
                categorie = visualizzaCategorie()
                selezionati = set(request.form.getlist("selezionati"))
                disponibili = {str(e["riga"]) for e in eventi}
                if not selezionati or not selezionati.issubset(disponibili):
                    raise ValueError("Seleziona almeno un evento valido da importare.")
                categorie_valide = {c["id_categoria"] for c in categorie}
                da_salvare = []
                for e in eventi:
                    if str(e["riga"]) not in selezionati:
                        continue
                    id_categoria = request.form.get(f"categoria_{e['riga']}", type=int)
                    if id_categoria not in categorie_valide:
                        raise ValueError(f"Seleziona una categoria valida per la riga {e['riga']}.")
                    da_salvare.append(
                        EventoSicurezza(
                            None,
                            id_categoria,
                            e["indirizzo_ip"],
                            e["descrizione"],
                            e["gravita"],
                            data_evento=datetime.strptime(e["data_evento"], "%Y-%m-%d %H:%M:%S"),
                        )
                    )
                id_importazione = salvaImportazione(
                    da_salvare,
                    g.utente['id_utente'],
                    anteprima['nome_file'],
                    base64.b64decode(anteprima['contenuto']),
                    len(eventi),
                    anteprima['righe_errate'],
                    anteprima['identificativo'],
                )
                flash(
                    f"Importazione completata: {len(da_salvare)} eventi salvati con stato Nuovo.",
                    'success',
                )
                return redirect(
                    url_for('dettagliImportazione', id_importazione=id_importazione), code=303
                )
            else:
                file = request.files.get("file_log")
                if file is None or not file.filename:
                    raise ValueError("Seleziona un file da caricare.")
                if os.path.splitext(file.filename)[1].lower() not in (".log", ".txt"):
                    raise ValueError("Sono ammessi soltanto file .log e .txt.")
                contenuto = file.read(MAX_BYTES + 1)
                eventi, errori = analizzaLog(contenuto)
                if eventi:
                    token = firma.dumps(
                        dict(
                            eventi=eventi,
                            id_utente=g.utente['id_utente'],
                            nome_file=secure_filename(file.filename)[:255] or 'eventi.log',
                            contenuto=base64.b64encode(contenuto).decode('ascii'),
                            righe_errate=len(errori),
                            identificativo=secrets.token_hex(32),
                        )
                    )
                    categorie = visualizzaCategorie()
        except ValueError as e:
            errore = str(e)
        except mysql.connector.Error:
            errore = "Impossibile completare l'operazione sul database. Riprova tra poco."
    importati = request.args.get("importati", type=int)
    if request.method == "GET" and importati and importati > 0:
        messaggio = f"Importazione completata: {importati} eventi salvati con stato Nuovo."
    return render_template(
        "importa_log.html",
        eventi=eventi,
        errori=errori,
        categorie=categorie,
        errore=errore,
        messaggio=messaggio,
        token=token,
    )


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/dashboard")
def dashboard():
    gravita = request.args.get("gravita")
    stato = request.args.get("stato")
    ordine = request.args.get("ordine", "recenti")
    testo = request.args.get("testo", "").strip()

    eventi = visualizzaEventi(gravita, stato, ordine, testo, **ambitoEventi())
    statistiche = statisticheEventi(**ambitoEventi())

    return render_template(
        "eventi.html",
        eventi=eventi,
        gravita=gravita,
        stato=stato,
        ordine=ordine,
        testo_ricerca=testo,
        statistiche=statistiche,
    )


@app.route("/eventi/<int:id_evento>")
def dettagliEvento(id_evento):

    evento = cercaEvento(id_evento, **ambitoEventi())

    if evento is None:
        abort(404)

    return render_template("dettagli_evento.html", evento=evento)


@app.errorhandler(404)
def paginaNonTrovata(errore):
    return render_template("404.html"), 404


@app.route("/eventi/nuovo", methods=["GET", "POST"])
def nuovoEvento():

    errore = None

    if request.method == "POST":
        try:
            id_categoria = int(request.form.get("id_categoria"))
            indirizzo_ip = request.form.get("indirizzo_ip")
            descrizione = request.form.get("descrizione")
            gravita = request.form.get("gravita")

            evento = EventoSicurezza(None, id_categoria, indirizzo_ip, descrizione, gravita)
            inserisciEvento(evento, id_utente=g.utente["id_utente"])
            flash("Evento aggiunto correttamente.", "success")

            return redirect(url_for("dashboard"))

        except (ValueError, TypeError) as e:
            errore = str(e)
        except mysql.connector.Error:
            errore = "Impossibile salvare l'evento. Riprova tra poco."

    categorie = visualizzaCategorie()
    return render_template(
        "nuovo_evento.html", errore=errore, categorie=categorie, dati=request.form
    )


@app.route("/eventi/cerca", methods=["GET"])
def ricercaEvento():

    id_evento = request.args.get("id_evento", type=int)

    if id_evento is None or id_evento <= 0:
        return redirect(url_for("dashboard"))

    evento = cercaEvento(id_evento, **ambitoEventi())

    if evento is None:
        abort(404)

    return redirect(url_for("dettagliEvento", id_evento=id_evento))


@app.route("/eventi/<int:id_evento>/modifica", methods=["GET", "POST"])
def modificaEventoPagina(id_evento):

    evento = cercaEvento(id_evento, **ambitoEventi())

    if evento is None:
        abort(404)

    categorie = visualizzaCategorie()
    errore = None

    if request.method == "POST":
        try:
            evento_modificato = EventoSicurezza(
                id_evento,
                int(request.form.get("id_categoria")),
                request.form.get("indirizzo_ip"),
                request.form.get("descrizione"),
                request.form.get("gravita"),
                request.form.get("stato"),
                evento["data_evento"],
            )

            modificaEvento(evento_modificato, **ambitoEventi())

            return redirect(url_for("dettagliEvento", id_evento=id_evento))

        except (ValueError, TypeError) as e:
            errore = str(e)
        except mysql.connector.Error:
            errore = "Impossibile salvare le modifiche. Riprova tra poco."

    dati = request.form if request.method == "POST" else evento
    return render_template(
        "modifica_evento.html", evento=evento, categorie=categorie, errore=errore, dati=dati
    )


@app.route("/eventi/<int:id_evento>/elimina", methods=["POST"])
def eliminaEventoPagina(id_evento):

    evento = cercaEvento(id_evento, **ambitoEventi())

    if evento is None:
        abort(404)

    eliminaEvento(id_evento, **ambitoEventi())

    return redirect(url_for("dashboard"))


@app.route("/info")
def info():
    return render_template("info.html")


@app.route("/eventi/esporta")
def esportaEventi():
    gravita = request.args.get("gravita")
    stato = request.args.get("stato")
    ordine = request.args.get("ordine", "recenti")
    testo = request.args.get("testo", "").strip()

    eventi = visualizzaEventi(gravita, stato, ordine, testo, **ambitoEventi())

    file = StringIO(newline="")
    writer = csv.writer(file, delimiter=";")
    writer.writerow(
        ["ID", "Categoria", "Indirizzo IP", "Descrizione", "GravitÃ ", "Stato", "Data evento"]
    )
    for evento in eventi:
        writer.writerow(
            [
                evento["id_evento"],
                evento["categoria"],
                evento["indirizzo_ip"],
                evento["descrizione"],
                evento["gravita"],
                evento["stato"],
                evento["data_evento"],
            ]
        )
    contenuto = BytesIO(file.getvalue().encode("utf-8-sig"))
    return send_file(
        contenuto, mimetype="text/csv", as_attachment=True, download_name="eventi_sicurezza.csv"
    )


if __name__ == "__main__":
    app.run(debug=True)

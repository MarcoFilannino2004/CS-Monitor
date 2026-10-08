from flask import Flask, render_template, abort, request, redirect, url_for, send_file
from database.eventi_repository import visualizzaEventi, cercaEvento, inserisciEvento,modificaEvento, eliminaEvento, statisticheEventi
from models.evento_sicurezza import EventoSicurezza
from database.categorie_repository import visualizzaCategorie
import mysql.connector
import os
import csv

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/dashboard")
def dashboard():
    gravita = request.args.get("gravita")
    stato = request.args.get("stato")
    ordine = request.args.get("ordine", "recenti")
    testo = request.args.get("testo", "").strip()

    eventi = visualizzaEventi(gravita, stato, ordine, testo)
    statistiche = statisticheEventi()

    return render_template("eventi.html", eventi=eventi, gravita=gravita, stato=stato, ordine=ordine, testo_ricerca=testo, statistiche=statistiche)

@app.route("/eventi/<int:id_evento>")
def dettagliEvento(id_evento):

    evento = cercaEvento(id_evento)

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
            inserisciEvento(evento)

            return redirect(url_for("dashboard"))

        except (ValueError, TypeError, mysql.connector.Error) as e:
            errore = str(e)

    categorie = visualizzaCategorie()
    return render_template("nuovo_evento.html", errore=errore, categorie=categorie)

@app.route("/eventi/cerca", methods=["GET"])
def ricercaEvento():

    id_evento = request.args.get("id_evento", type=int)

    if id_evento is None or id_evento <= 0:
        return redirect(url_for("dashboard"))

    evento = cercaEvento(id_evento)

    if evento is None:
        abort(404)

    return redirect(url_for("dettagliEvento", id_evento=id_evento))


@app.route("/eventi/<int:id_evento>/modifica", methods=["GET", "POST"])
def modificaEventoPagina(id_evento):

    evento = cercaEvento(id_evento)

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
                evento["data_evento"]
            )

            modificaEvento(evento_modificato)

            return redirect(url_for("dettagliEvento", id_evento=id_evento))

        except (ValueError, TypeError, mysql.connector.Error) as e:
            errore = str(e)

    return render_template("modifica_evento.html", evento=evento, categorie=categorie, errore=errore)

@app.route("/eventi/<int:id_evento>/elimina", methods=["POST"])
def eliminaEventoPagina(id_evento):

    evento = cercaEvento(id_evento)

    if evento is None:
        abort(404)

    eliminaEvento(id_evento)

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

    eventi = visualizzaEventi(gravita, stato, ordine, testo)

    percorso = os.path.join(app.instance_path, "eventi_sicurezza.csv")
    os.makedirs(app.instance_path, exist_ok=True)

    with open(percorso, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file, delimiter=";")

        writer.writerow(["ID", "Categoria", "Indirizzo IP", "Descrizione", "Gravità", "Stato", "Data evento"])

        for evento in eventi:
            writer.writerow([
                evento["id_evento"],
                evento["categoria"],
                evento["indirizzo_ip"],
                evento["descrizione"],
                evento["gravita"],
                evento["stato"],
                evento["data_evento"]
            ])

    return send_file(percorso, as_attachment=True, download_name="eventi_sicurezza.csv")


if __name__ == "__main__":
    app.run(debug=True)


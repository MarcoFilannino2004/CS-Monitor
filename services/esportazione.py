"""Generazione condivisa dei CSV e confronto degli eventi esportati."""

import csv
import hashlib
from io import StringIO


def contenutoCsv(eventi):
    file = StringIO(newline="")
    writer = csv.writer(file, delimiter=";")
    writer.writerow(
        ["ID", "Categoria", "Indirizzo IP", "Descrizione", "Gravità", "Stato", "Data evento"]
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
    return file.getvalue().encode("utf-8-sig")


def firmaEventi(eventi):
    return hashlib.sha256(contenutoCsv(eventi)).hexdigest()

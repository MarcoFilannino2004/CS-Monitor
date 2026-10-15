"""Scrittura e consultazione del registro; nessuna modifica o cancellazione."""

from database.strumenti import apriCursore


def inserisciAttivita(dati):
    with apriCursore() as (connessione, cursore):
        cursore.execute(
            """INSERT INTO registro_attivita
               (id_utente, username, indirizzo_ip, azione, esito, risorsa, dettagli,
                metodo, percorso, codice_http) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            tuple(
                dati[k]
                for k in (
                    'id_utente',
                    'username',
                    'indirizzo_ip',
                    'azione',
                    'esito',
                    'risorsa',
                    'dettagli',
                    'metodo',
                    'percorso',
                    'codice_http',
                )
            ),
        )
        connessione.commit()


def leggiRegistro(azione='', esito='', testo='', dal=None, al=None, pagina=1, limite=50):
    query = ' FROM registro_attivita WHERE 1=1'
    valori = []
    for campo, valore in [('azione', azione), ('esito', esito)]:
        if valore:
            query += f' AND {campo}=%s'
            valori.append(valore)
    if testo:
        query += ' AND (username LIKE %s OR indirizzo_ip LIKE %s OR risorsa LIKE %s)'
        valori.extend([f'%{testo}%'] * 3)
    if dal:
        query += ' AND data_attivita >= %s'
        valori.append(dal)
    if al:
        query += ' AND data_attivita < %s'
        valori.append(al)
    with apriCursore(True) as (_, cursore):
        cursore.execute('SELECT COUNT(*) AS totale' + query, tuple(valori))
        totale = cursore.fetchone()['totale']
        pagina = max(1, int(pagina))
        pagine = max(1, (totale + limite - 1) // limite) if limite else 1
        pagina = min(pagina, pagine)
        lettura = 'SELECT *' + query + ' ORDER BY data_attivita DESC, id_attivita DESC'
        parametri = list(valori)
        if limite:
            lettura += ' LIMIT %s OFFSET %s'
            parametri.extend([limite, (pagina - 1) * limite])
        cursore.execute(lettura, tuple(parametri))
        return dict(attivita=cursore.fetchall(), totale=totale, pagina=pagina, pagine=pagine)

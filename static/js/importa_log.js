const fileLog = document.getElementById('file_log');
const nomeFileLog = document.getElementById('nome-file-log');
fileLog.addEventListener('change', function() {
    nomeFileLog.textContent = fileLog.files.length ?
        fileLog.files[0].name :
        'Nessun file selezionato';
});

const selezioniEventi = Array.from(document.querySelectorAll('.selezione-evento'));
const categoriaGruppo = document.getElementById('categoria-gruppo');
const applicaCategoria = document.getElementById('applica-categoria');
const conteggioSelezionati = document.getElementById('conteggio-selezionati');
const esitoCategoria = document.getElementById('esito-categoria');

function aggiornaSelezione() {
    let selezionati = 0;
    selezioniEventi.forEach(function(checkbox) {
        const categoria = checkbox.closest('tr').querySelector('select');
        categoria.disabled = !checkbox.checked;
        categoria.required = checkbox.checked;
        if (checkbox.checked) selezionati++;
    });
    if (conteggioSelezionati) {
        conteggioSelezionati.textContent = `${selezionati} eventi selezionati su ${selezioniEventi.length}.`;
        applicaCategoria.disabled = !categoriaGruppo.value || selezionati === 0;
    }
    if (esitoCategoria) esitoCategoria.textContent = '';
}

selezioniEventi.forEach(function(checkbox) {
    checkbox.addEventListener('change', aggiornaSelezione);
});

// I controlli di gruppo esistono soltanto dopo aver caricato un file valido.
if (categoriaGruppo) {
    categoriaGruppo.addEventListener('change', aggiornaSelezione);
    document.getElementById('seleziona-tutti').addEventListener('click', function() {
        selezioniEventi.forEach(function(checkbox) {
            checkbox.checked = true;
        });
        aggiornaSelezione();
    });
    document.getElementById('deseleziona-tutti').addEventListener('click', function() {
        selezioniEventi.forEach(function(checkbox) {
            checkbox.checked = false;
        });
        aggiornaSelezione();
    });
    applicaCategoria.addEventListener('click', function() {
        if (!categoriaGruppo.value) return;
        let aggiornati = 0;
        selezioniEventi.forEach(function(checkbox) {
            if (checkbox.checked) {
                checkbox.closest('tr').querySelector('select').value = categoriaGruppo.value;
                aggiornati++;
            }
        });
        const nome = categoriaGruppo.options[categoriaGruppo.selectedIndex].text;
        esitoCategoria.textContent = `Categoria “${nome}” assegnata a ${aggiornati} eventi. Puoi ancora modificarla sulle singole righe.`;
    });
}
aggiornaSelezione();

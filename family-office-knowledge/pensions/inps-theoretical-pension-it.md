# Stima interna pensione INPS contributiva

## Ambito

Verifica fonti: 2026-07-29. Giurisdizione: Italia. Periodo eseguibile: 2026, con proiezioni di pianificazione dichiarate per date future.

Questa nota supporta una stima interna lorda e deterministica della componente INPS contributiva per scenari di uscita dal lavoro. Non sostituisce una certificazione INPS, una domanda amministrativa, una ricostituzione contributiva, una P1 ufficiale o una consulenza previdenziale.

## Fonti primarie

- INPS, "Il calcolo della pensione", ultimo aggiornamento indicato dalla fonte 2025-07-03: il criterio puo' essere contributivo, retributivo o misto; dal 1 gennaio 2012 si applica il contributivo sulla quota maturata da tale data; per il contributivo occorre individuare base imponibile, aliquota di computo, montante rivalutato e coefficiente di trasformazione.
- INPS, "Montante contributivo", ultimo aggiornamento indicato dalla fonte 2025-08-01: il montante deriva dai contributi annui rivalutati; per dipendenti l'aliquota di computo ordinaria indicata e' 33%; la rivalutazione e' composta, effettuata al 31 dicembre, escludendo i contributi dell'ultimo anno lavorato.
- INPS, "Coefficiente di trasformazione", ultimo aggiornamento indicato dalla fonte 2025-04-23: il montante viene trasformato in pensione annua con coefficienti legati all'eta' al conseguimento, con valori da 57 a 70 anni.
- Ministero del Lavoro e delle Politiche Sociali, Decreto direttoriale 20 novembre 2024 e comunicazione del 22 novembre 2024: aggiornamento biennale dei coefficienti di trasformazione con decorrenza 1 gennaio 2025.

## Regole operative

Il motore puo' stimare solo la quota contributiva quando l'input dichiara:

- persona e data di nascita;
- data candidata di uscita/pensione;
- montante contributivo storico gia' disponibile oppure basi annue da convertire in contributi;
- assunzioni future esplicite su imponibile, aliquota di computo e rivalutazione;
- rule pack applicabile o proiettivo.

Se la carriera e' mista/retributiva, o se mancano basi, montante, aliquote, data di nascita o data candidata, lo snapshot deve produrre `data_gaps` e non trasformare il risultato in una stima completa.

Quando e' presente una proiezione documentale INPS importata, il motore deve conservarla come stream separato o benchmark, annualizzarla solo se il rule pack dichiara il numero di mensilita' da usare per la pianificazione e mostrare lo scostamento rispetto alla stima interna. La stima interna non sovrascrive il documento.

Per anni successivi al periodo ufficiale codificato, i coefficienti e la rivalutazione possono essere usati solo come ipotesi di pianificazione marcate nel rule pack. Devono essere sostituiti da nuove regole ufficiali quando disponibili.

## Confine con il diritto alla pensione di vecchiaia

Verifica della fonte INPS: 2026-10-11. La scheda INPS sulla pensione di vecchiaia distingue i requisiti in base alla presenza di contribuzione anteriore al 1 gennaio 1996. Per la categoria ordinaria descritta dalla pagina indica 67 anni nel 2026, 67 anni e 1 mese nel 2027 e 67 anni e 3 mesi nel 2028; illustra inoltre requisiti contributivi e condizioni diverse per contribuzione pre/post 1996, deroghe e categorie escluse dall'adeguamento. Per i soli contributivi puri la pagina indica anche il requisito alternativo di 71 anni e cinque anni di contribuzione effettiva, con esclusione di quella figurativa.

Fonte primaria: [INPS, Pensione di vecchiaia](https://www.inps.it/it/it/dettaglio-scheda.it.schede-servizio-strumento.schede-servizi.pensione-di-vecchiaia.html).

Queste informazioni restano assenti dal rule pack di stima contributiva e non autorizzano da sole il motore a produrre una data di entitlement: il distinto pack di eligibility ordinaria le usa soltanto nel perimetro FPLD/AGO 2026-2028 approvato. Occorre comunque identificare gestione/categoria, regime contributivo, periodi ammessi, eventuali soglie d'importo, deroghe e stato assicurativo. Fuori dal caso supportato, il risultato italiano di V4.14 deve restare `null` con `data_gaps`; la stima contributiva qui sopra rimane un importo interno separato, non una prova del diritto.
## Binding aggiuntivo per V4.14h

Per il ramo post-1995 con 20 anni, la soglia è un confronto tra due evidenze distinte: importo mensile della pensione documentato e importo mensile dell'assegno sociale applicabile documentato per lo stesso anno. La fonte INPS dell'assegno sociale riporta per il 2026 EUR 546,24 mensili per 13 mensilità ([INPS, Assegno sociale](https://www.inps.it/it/it/dettaglio-scheda.it.schede-servizio-strumento.schede-servizi.assegno-sociale-50184.assegno-sociale.html)). Nel pack corrente 2027 e 2028 restano `data_gaps` finché l'importo annuale non è aggiunto con fonte e periodo propri; non si proietta e non si riusa il valore 2026.

Il perimetro abilitante è ristretto a lavoratore dipendente iscritto al FPLD nell'AGO, gestione singola ordinaria confermata. Gestioni autonome, esclusive, sostitutive, speciali, cumuli e aggregazioni estere/UE sono fuori scope e producono `null` + `data_gaps`.

# Eligibility ordinaria FPLD/AGO dipendenti (micro-slice V4.14b)

Verifica fonti: 2026-10-11. Giurisdizione: Italia. Periodo dei requisiti codificati: requisiti maturati dal 2026-01-01 al 2028-12-31. Il perimetro è soltanto quello ordinario di vecchiaia per dipendenti FPLD/AGO, con una sola gestione confermata; non è una certificazione INPS o una valutazione di altri regimi, totalizzazioni o cumuli.

- La scheda INPS sulla pensione di vecchiaia indica, per il percorso ordinario qui limitato, età di 67 anni nel 2026, 67 anni e un mese nel 2027 e 67 anni e tre mesi nel 2028. Per chi ha contribuzione anteriore al 1° gennaio 1996 richiede almeno 20 anni di contribuzione utile.
- Per chi ha il primo contributo dal 1° gennaio 1996, lo stesso requisito anagrafico e almeno 20 anni devono essere accompagnati da un importo mensile documentato almeno pari all'assegno sociale mensile applicabile, anch'esso documentato. In alternativa, la scheda riporta 71 anni, 71 anni e un mese, 71 anni e tre mesi rispettivamente per 2026, 2027 e 2028, con almeno cinque anni di contribuzione effettiva, esclusa la figurativa.
- L'aggiornamento INPS per il 2027-2028 è la fonte specifica per gli adeguamenti anagrafici di quei due anni. La circolare n. 104/2026 non è una fonte generale per questa eligibility: riguarda accordi ponte e non è usata dal pack.

Fonti primarie: [INPS, Pensione di vecchiaia](https://www.inps.it/it/it/dettaglio-scheda.it.schede-servizio-strumento.schede-servizi.pensione-di-vecchiaia.html); [INPS, Pensioni: requisiti aggiornati per il 2027 e il 2028](https://www.inps.it/it/it/inps-comunica/notizie/dettaglio-news-page.news.2026.03.pensioni-requisiti-aggiornati-per-il-2027-e-il-2028.html).

Il controllo eseguibile richiede data di nascita verificata, coorte, gestione/categoria e profilo ordinario a gestione singola confermati, evidenze contributive datate e cessazione del rapporto sempre verificata e source-bound per questo perimetro limitato ai dipendenti. Per il ramo contributivo puro richiede le due evidenze di importo mensile, riferite allo stesso anno della data candidata; non stima o calcola alcun importo. Dati mancanti o incerti, data fuori periodo, profilo speciale/escluso, gestione multipla/estera o aggregazione UE producono `not_assessed` con `data_gaps`, mai una conclusione legale negativa. Le semantiche giornaliere per nascite al 29 febbraio o fine mese non sono approvate e restano un gap fail-closed. Il controllo non emette riconoscimento, decorrenza economica, primo pagamento, stream pensionistico o data di uscita dal lavoro.

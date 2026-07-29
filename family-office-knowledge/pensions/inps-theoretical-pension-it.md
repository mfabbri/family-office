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

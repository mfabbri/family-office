# Current Next Increment

## ID e titolo

V4.8c - Earliest work-exit date with internal INPS estimate.

## Stato

`planned`

## Roadmap

`docs/roadmap/roadmap-v4-wealth-planning.md`

## Motivazione e dipendenze

V4.8b ha completato l'audit periodico dovuto dopo V4.6g, V4.7, V4.8 e V4.8a. La cadenza audit e' ripristinata. Su richiesta utente, prima di V4.9 viene inserito V4.8c per riallineare il lavoro all'obiettivo principale del progetto: trovare il primo momento sostenibile per smettere di lavorare, partendo da oggi, non valutare soltanto una data statica come 2037.

V4.8c dipende da V3.5e, V4.6e, V4.6g, V4.8a e V4.8b. Il perimetro e' previdenziale e di sostenibilita' patrimoniale di nucleo: seguire `knowledge -> rules -> tests -> engine`; non usare LLM per calcoli e distinguere sempre proiezione documentale INPS propria, pensione del coniuge, stima interna, quota spagnola pro-rata, assunzioni future e vincoli dichiarati.

## Piano operativo

1. Confermare gli snapshot disponibili: INPS importato per ciascun adulto del nucleo quando presente, pro-rata/teorico spagnolo, pension income, decumulation, liquidita', patrimonio e spese lifecycle.
2. Definire il contratto minimo `work-exit-feasibility/v1`: data di partenza, granularita' candidate, vincoli minimi, adulti del nucleo inclusi, date candidate, prima data sostenibile, motivi di fallimento delle date precedenti, provenance e data gaps.
3. Definire `inps-theoretical-pension/v1` come componente per candidato e persona: data candidata, contribuzione storica/proiettata, metodo codificato, coefficienti, montante, mensilita', limiti e data gaps.
4. Creare knowledge note e rule pack versionato per la stima INPS, includendo modalita' proiettiva per anni futuri non osservabili.
5. Implementare servizio deterministico e CLI breve, ad esempio `fo planning work-exit build`, con default del workspace e senza richiedere path JSON lunghi.
6. Integrare quota spagnola pro-rata, INPS stimata/documentale propria, pensione del coniuge, eventuali opzioni ponte e sostenibilita' del patrimonio senza fondere contributi o prestazioni.
7. Aggiungere test su prima data trovata, nessuna data sostenibile, candidate 2037/2039, documento INPS benchmark, pensione coniuge presente/mancante, regole future proiettive, data gaps e spiegazione delle date scartate.
8. Eseguire test mirati e regression appropriata prima di segnare `done`.

## Perimetro previsto

- Ricerca della prima data sostenibile di uscita dal lavoro per il nucleo, non semplice valutazione di una data predefinita personale.
- Stima pensionistica INPS interna lorda per ogni data candidata e per ciascun adulto incluso quando necessario.
- Composizione con quota spagnola pro-rata, pensione del coniuge e totale lordo congiunto, mantenendo stream separati per persona e fonte.
- Spiegazione dei vincoli che rendono non sostenibili le date precedenti.
- Nessuna certificazione ufficiale INPS, P1 ufficiale, netto fiscale non gia' disponibile o raccomandazione automatica.
- Nessun uso di LLM per calcoli previdenziali, fiscali, finanziari o raccomandazioni.

## Input personali necessari

Snapshot INPS importato per persona quando disponibile, pensione o contributi del coniuge, periodi/contributi italiani storici e proiettati, data di partenza ricerca, vincoli minimi di sostenibilita', date di nascita, assunzioni future esplicite, snapshot spagnolo teorico/pro-rata, patrimonio, liquidita' e spese. Usare fixture sintetiche per test e non copiare dati personali fuori dal workspace.

## Stato implementazione

Pianificato. V4.8b ha registrato:

- 44 test mirati OK sul perimetro V4.6g-V4.8a.
- Smoke CLI `pension-scenario`, `real-estate`, `protection`, `spanish-eu-theoretical-pension` e pro-rata da snapshot teorico OK.
- Da `family-office-engine/`: `$env:PYTHONPATH='src'; python -m unittest discover -s tests\unit` -> 435 test OK.
- `python family-office-engine\src\family_office_engine\governance\roadmap_audit.py` -> OK prima della chiusura audit.

Verifica operativa successiva: `fo pension import-inps` estrae una proiezione documentale INPS, ma `pension-income/v1` non annualizza il mensile INPS e non consuma ancora `it-es-eu-pension-pro-rata/v1`; V4.8c deve chiudere questo gap dentro una ricerca di fattibilita' della prima data di uscita.

## Criteri di completamento

- `work-exit-feasibility/v1` produce prima data sostenibile o blocco spiegato con provenance, data gaps e limiti espliciti.
- `inps-theoretical-pension/v1` produce stime lorde per le date candidate necessarie.
- Il comando CLI espone pensioni per persona, INPS, Spagna pro-rata, eventuali bridge, totale lordo congiunto di nucleo e motivi delle date scartate.
- Se la pensione del coniuge non e' disponibile o non stimabile, produce un gap esplicito per evitare una data di uscita incompleta.
- Le regole future sono marcate come proiezioni di pianificazione, non come legge futura ufficiale.
- Test mirati e regression pertinente verdi.
- Stato roadmap coerente e audit cadence non dovuta.

## Incrementi successivi

V4.9 - Succession and donation planning V2.

## Rischi, esclusioni e blocker

- Rischio previdenziale: non codificare regole normative senza fonti, rule pack versionato e test.
- Rischio temporale: le regole 2037/2039 non sono conoscibili nel 2026; usare assunzioni proiettive esplicite e data gaps.
- Rischio di obiettivo: non trasformare la capability in un semplice calcolatore di data target; la data target deve restare una candidata o un filtro diagnostico.
- Fuori perimetro: certificazione ufficiale INPS, netto fiscale non gia' disponibile, domande amministrative, ricongiunzioni/riscatti non codificati, ottimizzazioni opache o raccomandazioni.

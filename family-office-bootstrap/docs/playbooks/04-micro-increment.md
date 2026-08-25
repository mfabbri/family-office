# Micro-Increment

## Read first

- `family-office-engine/docs/roadmap/roadmap-index.md`
- `family-office-engine/docs/current-next-increment.md`
- sola roadmap attiva
- file/contratti direttamente coinvolti

Non leggere automaticamente long-term roadmap e decision log.

## Steps

1. Confermare ID, capacità osservabile e dipendenze.
2. Definire input, output, errori, data gaps e test.
3. Aggiornare `current-next-increment.md` solo se il piano cambia o inizia l'implementazione. Quando l'implementazione inizia, aggiornare nello stesso cambiamento anche lo stato del medesimo incremento nella roadmap attiva a `in_progress`: i due documenti devono restare allineati per l'audit.
4. Implementare il minimo necessario.
5. Eseguire test mirati.
6. Eseguire regression appropriata al gate.
7. Aggiornare contratto, roadmap e decision log solo se impattati.
8. Marcare `done` solo con evidenze riproducibili.

## CLI e wizard UX

Per incrementi esposti all'utente tramite CLI:

- documentare e testare il percorso `fo ...`; `python -m family_office_engine.cli.main ...` e' solo fallback tecnico;
- preferire default del workspace e comandi senza path lunghi;
- se un input JSON e' richiesto, aggiungere o aggiornare `wizard`, `prepare` o una guida compilabile;
- un wizard non deve chiedere metadati gia' disponibili da input o snapshot esistenti: mostrarli come contesto e chiedere solo dati operativi;
- salvare progressivamente dopo ogni risposta utile, cosi' `--overwrite` puo' riprendere o revisionare;
- valori fiscali, previdenziali, rendimenti o liquidabilita' incerti devono diventare `data_gaps`, non placeholder certi;
- gli errori CLI devono indicare il prossimo comando utile quando il problema e' recuperabile;
- quando uno snapshot contiene classificazioni non ovvie, aggiungere output riepilogativo o comando `explain` invece di costringere alla lettura del JSON.

## Done when

- capacità osservabile disponibile;
- test pertinenti verdi;
- privacy e provenance verificate;
- stato roadmap coerente;
- nessun gap critico implicito.

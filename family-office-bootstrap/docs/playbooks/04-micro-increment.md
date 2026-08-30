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

- partire dalla domanda o decisione che l'operatore deve risolvere, non da un comando interno o da un file snapshot; i sottocomandi tecnici restano disponibili ma non sono il percorso documentato di default;
- il percorso guidato deve mostrare prima i fatti riutilizzabili, raccogliere solo dati mancanti e concludere con un esito leggibile: risposta/diagnosi, assunzioni, `data_gaps`, limiti, provenienza e prossima azione;
- documentare e testare il percorso `fo ...`; `python -m family_office_engine.cli.main ...` e' solo fallback tecnico;
- preferire default del workspace e comandi senza path lunghi;
- la modifica manuale di JSON non e' il percorso operativo normale: se un input strutturato e' strettamente necessario, documentare nel piano il motivo e offrire `wizard`, `prepare`, import o generatore; una guida compilabile con validazione locale e' il fallback, non l'unica UX;
- un wizard non deve chiedere metadati gia' disponibili da input o snapshot esistenti: mostrarli come contesto e chiedere solo dati operativi;
- salvare progressivamente dopo ogni risposta utile, cosi' `--overwrite` puo' riprendere o revisionare;
- valori fiscali, previdenziali, rendimenti o liquidabilita' incerti devono diventare `data_gaps`, non placeholder certi;
- gli errori CLI devono indicare il prossimo comando utile quando il problema e' recuperabile;
- quando uno snapshot contiene classificazioni non ovvie, aggiungere output riepilogativo o comando `explain` invece di costringere alla lettura del JSON.
- non richiedere all'operatore di concatenare comandi di stato o validazione per dedurre un risultato: il journey deve orchestrare internamente le capability deterministiche necessarie.

## Done when

- capacità osservabile disponibile;
- test pertinenti verdi;
- privacy e provenance verificate;
- stato roadmap coerente;
- nessun gap critico implicito.

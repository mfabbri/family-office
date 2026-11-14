# Roadmap Maintenance

Aggiornare solo i documenti che cambiano semanticamente.

## Sempre valutare

- `current-next-increment.md`
- roadmap attiva

Quando un incremento passa a `in_progress` o `done`, aggiornare nello stesso cambiamento entrambi i documenti. Lo stato e l'ID dell'incremento corrente devono coincidere: `roadmap_audit.py` considera la divergenza un errore di governance.

La chiusura della sessione non implica il completamento dell'incremento: se review, autorizzazioni, suite o altri gate restano pendenti, conservare lo stato `in_progress`/`blocked`, annotare il blocker e una prossima azione concreta nel planner. Non usare `done` come stato di comodo per liberare la sessione.

## Solo se necessario

- `decision-log.md`: decisione architetturale, governance o debito deliberato;
- `roadmap-index.md`: cambia stato/gate della roadmap;
- `roadmap-long-term.md`: cambia direzione plurifase;
- altre roadmap: cambia una dipendenza reale.

Evitare aggiornamenti cosmetici ripetuti che aumentano diff e contesto senza valore operativo.

## Anti-stallo e fonte canonica

`current-next-increment.md` conserva lo storico ma espone in testa un riepilogo di stato attivo; l'identità canonica resta la coppia `## ID e titolo` + `## Stato` verificata da `roadmap_audit.py`. Un riepilogo storico non prevale sulla sezione canonica. Non aggiungere un altro micro-incremento per la stessa revisione senza nuovo finding/versione: preferire `human_review_required` e gate software separate. Applicare l'exit contract `family-office-engine/docs/roadmap/v4.14-exit-contract.md` senza rinumerare gli incrementi esistenti o cambiare a mano lo stato del parent.

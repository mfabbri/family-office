# Roadmap Maintenance

Aggiornare solo i documenti che cambiano semanticamente.

## Sempre valutare

- `current-next-increment.md`
- roadmap attiva

Quando un incremento passa a `in_progress` o `done`, aggiornare nello stesso cambiamento entrambi i documenti. Lo stato e l'ID dell'incremento corrente devono coincidere: `roadmap_audit.py` considera la divergenza un errore di governance.

Prima di chiudere l'ultimo incremento di una roadmap, verificare anche il successore previsto: stato dell'indice, primo incremento selezionabile e dipendenze esplicite. Se il target indicato dalla handoff e' gia `done` o il successore non contiene lavoro `planned`, non riaprire un incremento completato e non inventarne uno. Registrare il checkpoint effettivamente richiesto, mantenere gli stati storici e annotare che non esiste un successivo incremento selezionabile; una nuova voce richiede scope e dipendenze formalizzati.

Al handoff riconciliare `current-next-increment.md` e `current-work.json`: ID/stato, routing v4.0, blocker, verifica e `next_action` devono descrivere lo stesso task o la chiusura appena attestata. I validator strutturali non sostituiscono questo controllo semantico; rimuovere routing e azioni residue del task precedente.

La chiusura della sessione non implica il completamento dell'incremento: se review, autorizzazioni, suite o altri gate restano pendenti, conservare lo stato `in_progress`/`blocked`, annotare il blocker e una prossima azione concreta nel planner. Non usare `done` come stato di comodo per liberare la sessione.

Un'autorizzazione per piu' incrementi non supera dipendenze o gate: processare solo il prossimo incremento eleggibile e fermarsi quando serve evidenza esterna. Dopo il gate, ricalcolare la roadmap; il conteggio richiesto dall'utente non autorizza a saltare item o a riaprire quelli gia completati.

## Solo se necessario

- `decision-log.md`: decisione architetturale, governance o debito deliberato;
- `roadmap-index.md`: cambia stato/gate della roadmap;
- `roadmap-long-term.md`: cambia direzione plurifase;
- altre roadmap: cambia una dipendenza reale.

Evitare aggiornamenti cosmetici ripetuti che aumentano diff e contesto senza valore operativo.

## Anti-stallo e fonte canonica

`current-next-increment.md` conserva lo storico ma espone in testa un riepilogo di stato attivo; l'identità canonica resta la coppia `## ID e titolo` + `## Stato` verificata da `roadmap_audit.py`. Un riepilogo storico non prevale sulla sezione canonica. Non aggiungere un altro micro-incremento per la stessa revisione senza nuovo finding/versione: preferire `human_review_required` e gate software separate. Applicare l'exit contract `family-office-engine/docs/roadmap/v4.14-exit-contract.md` senza rinumerare gli incrementi esistenti o cambiare a mano lo stato del parent.

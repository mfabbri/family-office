# Roadmap Maintenance

Aggiornare solo i documenti che cambiano semanticamente.

## Sempre valutare

- `current-next-increment.md`
- roadmap attiva

Quando un incremento passa a `in_progress` o `done`, aggiornare nello stesso cambiamento entrambi i documenti. Lo stato e l'ID dell'incremento corrente devono coincidere: `roadmap_audit.py` considera la divergenza un errore di governance.

## Solo se necessario

- `decision-log.md`: decisione architetturale, governance o debito deliberato;
- `roadmap-index.md`: cambia stato/gate della roadmap;
- `roadmap-long-term.md`: cambia direzione plurifase;
- altre roadmap: cambia una dipendenza reale.

Evitare aggiornamenti cosmetici ripetuti che aumentano diff e contesto senza valore operativo.

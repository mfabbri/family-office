# Current Next Increment

## ID e titolo

V6.6a - Guided planning input wizards.

## Stato

`done`

## Roadmap

`docs/roadmap/roadmap-v6-operations-compliance.md`

## Motivazione e dipendenze

V6.6 era completato e l'audit era verde con `audit_due=false`. V6.6a era il primo incremento `planned` con dipendenza soddisfatta; V6.7 non viene aperto in questa sessione.

Dipendenza: V6.6.

## Piano ed esito operativo V6.6a

1. Aggiungere i tre percorsi guidati `wealth-strategy`, `protection` ed `estate` sopra i contratti esistenti.
2. Usare default workspace, draft privati, checkpoint progressivi, `--overwrite`, provenance dichiarata e `data_gaps` espliciti.
3. Mostrare fatti disponibili e una prossima azione; rifiutare path fuori dal workspace e non introdurre calcoli, import o esecuzione automatica.
4. Collegare `fo ask` ai wizard per gli input mancanti e verificare che valori di protezione ignoti restino `review_required`.

Completato. Modificati CLI, servizi di supporto operator analysis/protection, test e documentazione. Verifiche: 21 test mirati; regression engine 637 test OK con 1 skip Windows; compilazione; `pip check`; smoke help dei tre comandi; `roadmap_audit.py`; validazione routing strutturale; privacy/path boundary; `git diff --check`. `jsonschema` non è installato nell'interprete corrente: la validazione formale è stata saltata con warning, mentre il validator strutturale planner è passato. Nessun dato personale reale o segreto è stato aggiunto.

## Prossima azione

Ricalcolare il prossimo incremento in una sessione successiva secondo `roadmap-index.md`; non avviare V6.7 automaticamente.

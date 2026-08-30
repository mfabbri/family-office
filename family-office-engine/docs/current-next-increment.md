# Current Next Increment

## ID e titolo

V6.4 - Compliance calendar and alerts.

## Stato

`done`

## Roadmap

`docs/roadmap/roadmap-v6-operations-compliance.md`

## Motivazione e dipendenze

V6.4 e' il primo incremento pianificato della roadmap V6 con dipendenze soddisfatte. Trasforma fonti e policy versionate in un calendario locale di scadenze e alert, senza assumere date o obblighi personali non documentati.

Dipendenze: V3.4 `done`; V6.2 `done`.

## Piano operativo V6.4

1. Registrare knowledge e rule pack versionati, con giurisdizione, validita', fonte, owner e azione richiesta; nessuna data normativa e' hard-coded nell'engine.
2. Implementare `compliance-calendar/v1` e alert locali deterministici, con ricorrenze, date mobili, timezone esplicita, deduplicazione e `data_gaps` per fatti o obblighi non verificati.
3. Esporre un journey `fo compliance` che mostri calendario, fonte, responsabilita' e azione, con setup guidato per le sole scadenze workspace-local non derivabili.
4. Coprire con fixture sintetiche ricorrenze, date mobili, alert duplicati, timezone, errori recuperabili e CLI; eseguire regression, controlli privacy/confini e audit roadmap.

## Criteri di completamento V6.4

- ogni alert mostra fonte, responsabilita' e azione richiesta;
- ricorrenze, date mobili, deduplicazione e timezone sono deterministici e coperti da test;
- date, obblighi e owner non verificati diventano `data_gaps`, non certezze implicite;
- l'operatore non deve modificare JSON per il percorso ordinario e riceve un output leggibile;
- test end-to-end e regression sono verdi; roadmap e stato sono coerenti.

## Esito e verifiche

Completato. `compliance-calendar/v1` genera calendario e alert locali da policy versionata: ogni alert conserva fonte, owner e azione richiesta; le date sono calcolate deterministicamente per ricorrenze annuali, date una tantum e ultimo giorno lavorativo, con timezone esplicita e deduplicazione. `fo compliance setup` salva progressivamente scadenze workspace-local senza richiedere JSON; una fonte assente diventa `source_not_verified` e richiede verifica, senza dichiarare un obbligo personale.

Verifiche riproducibili: 5 test V6.4 e 20 test mirati V6.4/timeline/data-quality OK; regression engine 619 test OK; smoke `.venv/Scripts/fo.exe compliance calendar --help` OK; compilazione, validazione JSON di citation catalog e rule pack, `git diff --check`, controllo standard-library/workspace-only e `roadmap_audit.py` OK. Decision log aggiornato per il nuovo contratto cross-repository. La chiusura è il quarto incremento funzionale dall'audit V6.3b: il prossimo incremento funzionale resta bloccato dalla cadenza finché non viene completato il code audit richiesto; V6.5 non è stato avviato.

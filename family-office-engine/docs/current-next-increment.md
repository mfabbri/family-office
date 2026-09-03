# Current Next Increment

## ID e titolo

V6.11 - Annual review and contingency plan.

## Stato

`done`

## Roadmap

`docs/roadmap/roadmap-v6-operations-compliance.md`

## Motivazione e dipendenze

V6.10b e' completato. V6.11 e' il primo incremento funzionale successivo con dipendenze V6.3-V6.10 soddisfatte.

## Obiettivo e criteri di accettazione

Produrre una review annuale con KPI, eventi, cambi normativi, scostamenti, rischi e piano di aggiornamento.

Done when: il sistema indica cosa riesaminare, perche' e con quale priorita', distinguendo dati completi, obsoleti o mancanti.

## Piano concreto

- Definire il contratto deterministico `annual-review/v1` su metadati e snapshot workspace-local, senza leggere contenuti personali.
- Implementare `fo review annual` con riepilogo question-first di copertura, freshness, eventi, rischi, priorita' e azioni di contingenza.
- Coprire anno incompleto, dati obsoleti, cambio residenza ed evento straordinario con test unitari/integrativi e controlli di privacy/path.

Out of scope: lavoro parziale di V6.11, nuovi calcoli normativi non pianificati, dati personali fuori workspace.

## Prossima azione

V6.11 completato e verificato. La roadmap V6 non definisce ancora un incremento successivo: mantenere V6 come roadmap attiva fino a una transizione formale e non avviare lavoro ulteriore in questa sessione.

## Blocker di selezione successiva

Evidenze: tutti gli incrementi della roadmap V6 sono `done`, `roadmap_audit.py` restituisce `audit_due=false` e l'indice non definisce V6.12 né una roadmap successiva `in_progress`/`planned`. Impatto: non esiste un incremento con scope e criteri di accettazione verificabili da implementare senza inventare lavoro. Prerequisito: definire formalmente il prossimo incremento o aprire la roadmap successiva nell'indice, mantenendo una sola roadmap `in_progress`.

# Current Next Increment

## ID e titolo

V6.6d - Work-exit guided input wizard.

## Stato

`planned`

## Roadmap

`docs/roadmap/roadmap-v6-operations-compliance.md`

## Motivazione e dipendenze

Per usare il calcolo della prima data sostenibile di uscita dal lavoro in modo coerente con la UX del progetto, gli input devono essere introdotti dalla CLI e non tramite JSON compilato manualmente.

Dipendenza: V6.6c `done`.

## Obiettivo e criteri di accettazione

Implementare `fo planning work-exit wizard` per creare e validare nel workspace privato gli input `work-transition-readiness/v1` e `work-exit-feasibility/v1`, mostrando gli snapshot già disponibili e chiedendo soltanto dati mancanti. Il wizard deve salvare progressivamente, supportare la ripresa, rappresentare valori incerti come `data_gaps`, mantenere path confinati e distinguere fatti, assunzioni, limiti e prossima azione.

Out of scope: nuovi calcoli pensionistici o finanziari, import automatici, certificazioni INPS, consulenza fiscale o raccomandazioni.

## Prossima azione

Selezionare e implementare V6.6d in una sessione dedicata. V6.7 resta successivo e non viene avviato.

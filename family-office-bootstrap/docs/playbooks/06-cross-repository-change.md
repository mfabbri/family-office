# Cross-Repository Change

## Required plan

Definire prima:

- repository owner della semantica;
- contratto condiviso e versione;
- ordine di modifica;
- compatibilità e migrazione;
- test per ogni confine.
- percorso CLI per gli input strutturati: wizard, import, generatore o `prepare` come default; JSON manuale solo se strettamente necessario, motivato e validato localmente.
- journey utente question-first: domanda/decisione, fatti riutilizzabili, dati mancanti, tool deterministici coinvolti e risposta leggibile con provenienza, limiti e prossima azione; i contratti interni non devono emergere come procedura operativa.

## Ordine tipico

1. knowledge, se cambia significato normativo;
2. rules, se cambia logica calcolabile;
3. schema/contratto;
4. engine;
5. fixture sintetiche e integration test;
6. workspace migration, senza copiare dati privati.

Usare tier advanced/high. Un subagent read-only può mappare dipendenze; evitare scritture parallele sugli stessi contratti.

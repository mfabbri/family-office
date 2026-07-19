# Cross-Repository Change

## Required plan

Definire prima:

- repository owner della semantica;
- contratto condiviso e versione;
- ordine di modifica;
- compatibilità e migrazione;
- test per ogni confine.

## Ordine tipico

1. knowledge, se cambia significato normativo;
2. rules, se cambia logica calcolabile;
3. schema/contratto;
4. engine;
5. fixture sintetiche e integration test;
6. workspace migration, senza copiare dati privati.

Usare tier advanced/high. Un subagent read-only può mappare dipendenze; evitare scritture parallele sugli stessi contratti.

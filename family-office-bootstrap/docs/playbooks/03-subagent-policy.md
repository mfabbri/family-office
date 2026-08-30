# Subagent Policy

Il parent è un router/controller. La delega resta selettiva, ma è obbligatoria quando il model router assegna il lavoro sostanziale a Terra o Sol.

## Default

- `fo_explorer` (Luna/low) per discovery bounded che evita letture estese del parent.
- `fo_docs_reviewer` / `fo_docs_editor` (Luna/medium) per documentazione e governance circoscritte.
- `fo_planner` (Terra/medium) per planning cross-module con architettura e regole già definite.
- `fo_implementer` (Terra/medium) per implementazione deterministica.
- `fo_reviewer` (Terra/high) per review tecnica indipendente T3–T5.
- `fo_financial_reviewer` (Sol/high) per formule, cash-flow, leverage, stress test e opportunity cost.
- `fo_architect` (Sol/high) per architettura/migrazioni/trade-off.
- `fo_normative_reviewer` (Sol/xhigh) per fiscalità, previdenza, compliance e validità temporale.

## Vincoli

- Massimo 2 subagent sostanziali per task salvo dipendenze realmente indipendenti; il runtime consente fino a 3 thread concorrenti.
- Profondità pratica: un solo livello di delega.
- Nessun subagent se il task è risolvibile con una singola lettura e un singolo test e la policy non richiede uno specialista.
- Non delegare la stessa domanda a due modelli per "votazione".
- Non invocare reviewer finanziario e normativo sullo stesso cambiamento salvo che contenga entrambe le semantiche.
- I subagent devono restituire sintesi e riferimenti, non raw logs.
- Il parent non deve rileggere integralmente i file già sintetizzati da un explorer affidabile salvo incongruenze.
- Più agenti non devono modificare gli stessi file in parallelo.

## Quando parallelizzare

Solo se i workstream sono indipendenti, ad esempio:

- explorer: individua servizi/contratti riutilizzabili;
- normative reviewer: verifica solo il perimetro fiscale di una nuova activity classification.

Non parallelizzare implementazione e review dello stesso file prima che l'implementazione sia stabile.

## Contratto di ritorno

Ogni subagent deve restituire:

1. conclusione;
2. evidenze con file/simboli;
3. rischi o gap;
4. test/review eseguiti se applicabili;
5. massimo 5 azioni raccomandate;
6. nessun chain-of-thought o log completo salvo richiesta.

## Token hygiene

Le risposte dei subagent devono essere brevi e strutturate per poter essere incorporate senza riaprire il corpus. Il parent mantiene il contesto minimo necessario e usa progressive disclosure.

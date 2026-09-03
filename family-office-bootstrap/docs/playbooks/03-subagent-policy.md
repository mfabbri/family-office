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

## Esecuzione effettiva del parent

La delega non può trasformare il parent in un osservatore passivo. Prima di delegare il parent deve compiere il primo passo locale non bloccante: definire il piano, preparare il contratto o delimitare i file e i test. Dopo la delega deve mantenere il percorso critico attivo con lavoro non sovrapposto.

- Usare al massimo una finestra di attesa bounded per richiesta; durante l'attesa eseguire verifiche locali o preparare l'integrazione.
- Se la finestra scade, controllare subito worktree e stato dell'agent; non ripetere polling indefinito.
- Dopo un timeout o un risultato incompleto, il parent deve scegliere esplicitamente una sola azione: continuare localmente un fix bounded, inviare una richiesta di stato/consegna, oppure dichiarare un blocker con evidenze.
- Non delegare review prima che l'implementazione abbia prodotto diff e test mirati, salvo un gate architetturale esplicitamente prerequisito.
- Un reviewer può produrre NO-GO; il parent deve integrare o correggere direttamente i finding bounded, senza aprire una catena indefinita di deleghe.
- Ogni incremento deve avere un limite operativo: massimo due subagent sostanziali, massimo un ciclo di implementazione e un ciclo di review; ulteriori cicli richiedono un blocker documentato e una decisione nel planner.
- Il completion report deve elencare separatamente codice runtime, test, documentazione e file preesistenti preservati; non basta dire “implementato” o “test verdi”.
- Prima della chiusura eseguire `python planning/validate-execution-guardrails.py`; se fallisce, lo stato resta attivo o blocked e non si dichiara completato il lavoro.

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

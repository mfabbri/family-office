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

- Default: massimo 2 eventi di delega/escalation sostanziali per task; il runtime consente fino a 3 thread concorrenti. In via eccezionale, un'autorizzazione esplicita dell'utente può estendere il budget fino a 18 eventi per uno scope/versione nominati, registrando nel planner autorizzazione, ambito e blocker. L'estensione vale solo per quell'incremento e non modifica il default.
- Profondità pratica: un solo livello di delega.
- Nessun subagent se il task è risolvibile con una singola lettura e un singolo test e la policy non richiede uno specialista.
- Non delegare la stessa domanda a due modelli per "votazione".
- Non invocare reviewer finanziario e normativo sullo stesso cambiamento salvo che contenga entrambe le semantiche.
- I subagent devono restituire sintesi e riferimenti, non raw logs.
- Il parent non deve rileggere integralmente i file già sintetizzati da un explorer affidabile salvo incongruenze.
- Più agenti non devono modificare gli stessi file in parallelo.

## Esecuzione effettiva del parent

La delega non può trasformare il parent in un osservatore passivo. Prima di delegare il parent deve compiere il primo passo locale non bloccante: definire il piano, preparare il contratto o delimitare i file e i test. Dopo la delega deve mantenere il percorso critico attivo con lavoro non sovrapposto.

- Default: usare al massimo una finestra di attesa bounded per richiesta; durante l'attesa eseguire verifiche locali o preparare l'integrazione.
- Eccezione esplicita: se l'utente autorizza un numero di tentativi e un timeout per tentativo, registrare nel planner budget, ruolo/modello, scope e stop condition prima di riprendere. Il budget dell'utente sostituisce il default per quella richiesta, non diventa una policy generale; fermarsi appena arriva un output utile o quando il budget autorizzato termina.
- L'autorizzazione a una review aggiuntiva è specifica per tentativo, versione dell'artefatto, reviewer/ruolo, scope e timebox: non autorizza automaticamente il riesame di una versione corretta o ulteriori cicli. I checkpoint brevi condividono lo stesso budget complessivo e non lo azzerano.
- Un tentativo è una singola richiesta al ruolo incaricato con il suo timebox complessivo. Suddividere il timebox in finestre brevi per mantenere aggiornato l'utente non moltiplica il numero di tentativi; dichiarare i timeout intermedi senza trattarli come esito.
- Se la finestra scade, controllare worktree e stato dell'agent. Senza budget esplicito, non ripetere attese; con budget esplicito, continuare solo entro il limite e registrare ogni fallback prima di cambiare thread/route.
- Timeout o mancata risposta non sono GO, NO-GO né completamento. Per gate normativi mantenere `review_pending`/`blocked` secondo il contratto; per review architetturali non attribuire al reviewer conclusioni non ricevute. Un fallback conserva ruolo, modello e scope salvo nuova autorizzazione.
- Registrare `delegated` solo dopo che l'agent ha effettivamente accettato/ricevuto il task; un errore di spawn per thread capacity non è una delega. Se il task è stato avviato ma non consegna entro il timebox, registrare timeout/fallback, chiudere o chiedere una consegna una sola volta secondo il budget, e continuare il percorso critico localmente senza inferire un esito.
- Dopo un timeout o un risultato incompleto, il parent deve scegliere esplicitamente una sola azione: continuare localmente un fix bounded, inviare una richiesta di stato/consegna, consumare il prossimo tentativo già autorizzato, oppure dichiarare un blocker con evidenze.
- Non delegare review prima che l'implementazione abbia prodotto diff e test mirati, salvo un gate architetturale esplicitamente prerequisito.
- Un reviewer può produrre NO-GO; il parent deve integrare o correggere direttamente i finding bounded, senza aprire una catena indefinita di deleghe.
- Ogni incremento deve avere un limite operativo: massimo due subagent sostanziali, massimo un ciclo di implementazione e un ciclo di review; ulteriori cicli richiedono un blocker documentato e una decisione nel planner.
- Se un NO-GO porta a una nuova versione contrattuale, mantenere il risultato legato alla versione esaminata e chiedere/registrare la decisione per il ciclo successivo prima di riusare il reviewer; non ereditare il GO o il budget della versione precedente.
- `routing.trace` nel planner descrive il solo incremento attivo, così il guardrail sul budget non conta deleghe storiche di incrementi precedenti. Prima di compattare/rimuovere eventi storici, conservarne esito e motivazione in `verification.tests`/`notes` o nel decision log; non eliminare la traccia dell'incremento corrente.
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

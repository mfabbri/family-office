# Testing and Review

## Test ladder

1. test mirato del comportamento modificato;
2. test del modulo/package;
3. integration sui confini interessati;
4. golden/regression per calcoli o contratti;
5. suite completa al gate di incremento o release.

Non eseguire ripetutamente l'intera suite durante modifiche locali se i test mirati forniscono feedback sufficiente.

## Gate di completamento

Al gate di incremento o release l'intera suite del repository deve terminare con esattamente 0 failure, 0 errori e 0 skipped. Un failure si corregge nel codice o, con evidenza del contratto, nel test; non si waiva come out-of-scope. Uno skip non è un pass: va sostituito da un test equivalente eseguibile sulle piattaforme supportate. Se la suite non può essere eseguita o passare integralmente, lo stato resta `in_progress` o `blocked`, mai `done`.

### Windows e sandbox

- Un errore di accesso ACL/temp imposto dal sandbox non è né un pass né una deroga al gate: la suite resta non verificata finché non viene eseguita. Se il comando è necessario e il blocco è attribuibile al sandbox, richiedere l'escalation/permesso previsto, poi eseguire la suite completa e registrare il conteggio reale. Non cambiare asserzioni, input, permessi di sistema o semantica dei test per eludere il controllo; correggere invece il test quando la verifica equivalente multipiattaforma è parte del contratto.
- **Preflight ACL obbligatorio prima della suite Windows**: eseguire `family-office-bootstrap/planning/run-v414-windows-gate.ps1 -RepoRoot <repo> -PreflightOnly`. Lo script usa una directory temporanea per-run in `planning/.runtime/test-gate/` dentro il workspace, verificando creazione/lettura/scrittura/cleanup e l'effettivo `tempfile.gettempdir()`. Reindirizzare *solo le variabili d'ambiente del processo di test* a un percorso di scratch scrivibile è isolamento dell'ambiente, non waiver: i test e tutti i criteri 0/0/0 restano invariati. Se fallisce il preflight, non avviare la suite e registrare il blocker operativo (ACL/sandbox/interprete) con il log; richiedere la correzione dei permessi del processo o l'esecuzione in PowerShell utente autorizzata, senza disabilitare sandbox globalmente.
- Dopo un preflight positivo eseguire `run-v414-windows-gate.ps1 -RepoRoot <repo> -FullSuite`. Il runner arresta la cascata al primo test mirato fallito, registra i risultati e solo dopo esegue la suite integrale. Un PASS tecnico su un candidato immutato consente la sola rivalutazione del gate software; non trasferisce GO normativi né modifica automaticamente gli stati di roadmap.
- Invocare esplicitamente il Python del venv Engine, ad esempio `& .\family-office-engine\.venv\Scripts\python.exe -m unittest discover -s tests\unit -p 'test_*.py'` dalla root Engine; non usare il Python globale per una suite che dipende dalle librerie del repository.
- Quando output di sottoprocessi o cleanup temporanei è molto esteso, acquisire il log in un file temporaneo del run e riportare exit code e riepilogo del runner (`Ran`, failure, errori, skipped). Non confondere righe `ERROR` stampate intenzionalmente da uno scenario CLI con il risultato del runner; la suite passa solo se il processo termina con exit code 0 e il conteggio unittest è 0/0/0.
- A fine run rimuovere soltanto la directory temporanea creata da quel run, dopo aver verificato il path assoluto e che resti nel workspace. Lasciare intatti temporanei e dati untracked preesistenti.

## Review proportionality

- T0–T1: self-review e test mirati.
- T2: self-review strutturata + regression pertinente.
- T3: review high-effort, eventualmente subagent read-only.
- T4–T5: review indipendente, fonti/assunzioni e scenari avversi.

## Gate operativo

La review e' un gate, non un sostituto dell'implementazione. Il parent deve avere gia' un diff verificabile e test mirati prima di invocare il reviewer, salvo una review architetturale esplicitamente prerequisita. Le attese sul reviewer sono bounded: dopo un timeout si controlla il worktree e si prosegue localmente, si chiede una consegna sintetica oppure si registra un blocker; non si effettua polling indefinito. Un NO-GO deve produrre finding azionabili e un solo ciclo di correzione bounded. Se il finding non e' bounded o il ciclo fallisce, l'incremento resta `in_progress` e il planner registra evidenze, impatto e prerequisito. Per i gate normativi, il reviewer valuta una versione esatta del contratto: dopo una modifica sostanziale, il verdetto precedente non copre la nuova versione. Un ulteriore ciclo oltre il default richiede blocker documentato e decisione esplicita nel planner; autorizzazione e timebox valgono soltanto per quel tentativo.

### Exact-version e baseline immutabili

La review deve identificare e hashare l'intero pacchetto esaminato: candidati, dipendenze immutabili e baseline di confronto. Il report indica per ogni elemento hash atteso e osservato; verificare soltanto gli artefatti candidati può nascondere una deriva della baseline. Un GO precedente non si trasferisce a byte cambiati.

Se una baseline immutabile deriva ma l'hash della versione già revisionata è noto, non accettare silenziosamente la deriva né modificare un candidato più nuovo per occultarla: ripristinare solo i byte della versione già revisionata, verificare lo SHA-256 atteso e riesaminare il candidato esatto e invariato. Qualunque mismatch ulteriore rispetto alla correzione autorizzata è NO-GO.

Suite mirate/complete concluse e hash corrispondenti sono evidenze necessarie, ma non annullano i finding del reviewer. Un GO limitato chiude soltanto l'ambito e gli artefatti nominati nel verdetto; non chiude il parent, non abilita runtime o disponibilità generale.

### Migrazione di contratti versionati

Quando si aggiunge una nuova versione di schema/contratto, mantenere eseguibili i test di regressione delle versioni ancora supportate accanto ai test della nuova versione. Il fatto che lo schema precedente sia byte-identico non dimostra che il suo comportamento continui a essere testato. Prima di chiudere, verificare che la suite referenzi esplicitamente ogni versione supportata e copra i suoi invarianti; se i test vengono sostituiti, documentare l'equivalenza e il motivo della rimozione.

## Integrazione dei test delegati

- I test mirati o la suite di modulo eseguiti da un agent sono evidenza parziale. Il parent esegue la suite completa sul candidato integrato finale e registra comando, conteggio totale e `failure/error/skip`, che devono essere tutti zero.
- Per contratti fail-closed coprire il percorso pubblico fino all'output: verificare `data_gaps` e che valori non valutati non si propaghino in eligibility, amount, payment o altri output downstream. Le asserzioni su un helper privato non provano il comportamento del consumer.
- Dopo ogni modifica successiva alla review, ricalcolare gli hash del candidato. Il verdetto vale solo per gli artefatti esatti esaminati.

## CLI UX checks

Quando cambia un comando CLI o un wizard, verificare almeno:

- comando corto `fo ...` o wrapper locale documentato;
- errore recuperabile con prossimo comando esplicito;
- output riepilogativo leggibile senza aprire JSON;
- wizard con default da workspace/snapshot quando disponibili;
- salvataggio progressivo e ripresa con `--overwrite`;
- valori incerti registrati come `data_gaps`.

## Question-first UX checks

Quando una capability è destinata a rispondere a una domanda o supportare una decisione familiare, verificare almeno:

- un singolo ingresso guidato parte dalla domanda/decisione e non richiede una sequenza di sottocomandi tecnici;
- i fatti già disponibili sono riusati e mostrati come contesto, mentre vengono richiesti solo dati operativi mancanti;
- l'output finale è leggibile senza JSON e distingue risposta o diagnosi, fatti, assunzioni, `data_gaps`, limiti, provenienza e prossima azione;
- il journey invoca solo tool registrati e calcoli deterministici; un LLM può classificare o spiegare ma non calcolare valori fiscali, previdenziali o finanziari;
- un test end-to-end con fixture sintetiche copre il percorso completo e gli errori recuperabili.

## Smoke CLI riproducibile

Verificare il comando utente `fo ...` oltre al fallback tecnico `python -m family_office_engine.cli.main ...`. Su Windows, se `fo` non e' nel `PATH` della shell, invocare esplicitamente l'eseguibile del virtual environment del repository, ad esempio `./.venv/Scripts/fo.exe ...`; non considerare il fallback tecnico un sostituto dello smoke del comando utente.

## Completion report

Riportare soltanto:

- file modificati;
- comportamento ottenuto;
- test eseguiti e risultato;
- risultato della suite completa al gate: failure/error/skip, tutti pari a 0;
- rischi/gap residui;
- stato roadmap, se applicabile.

## Gate indipendenti e test proporzionati

- **Software readiness**: validazione ID/version/hash/periodi, test mirati, regressioni del consumer pubblico, non-propagazione `not_assessed`/`not_matched`, privacy, suite completa con 0 failure/error/skip al gate di chiusura.
- **Normative readiness (per conclusione)**: legge/fonte, percorso, periodo, fatti disponibili, review specialistica ex-version ove richiesta. `PENDING`/`NO-GO` vieta l'output normativo corrispondente, non l'esecuzione dei test o l'implementazione fail-closed di un binding già circoscritto.
- **Scenario readiness**: un'ipotesi sul futuro può essere simulata solo se è riconoscibile come ipotesi, e non è presentata come requisito o decorrenza legalmente accertata.
- Per modifiche a sola compatibilità non riaprire automaticamente una review normativa già terminata sul pack invariato. Riesaminare invece i test e il comportamento **del consumer**; escalation specialistica solo su trigger verificabile.
- Evitare suite complete ripetute senza diff; manteniamo l'obbligo 0/0/0 per il gate finale e per le piattaforme dichiarate supportate. Non mascherare failure ambientali come pass.

## Test anti-loop v4.0

Prima di chiamare un reviewer generare una matrice di massimo 5 righe: `(claim, file/line, fonte primaria/versione, test, atteso)`. Il reviewer deve verificare la modifica anziche' rigenerare un audit globale. In un NO-GO, catturare un test che riproduce il finding; vietato un nuovo reviewer sullo stesso hash senza una nuova domanda/versone autorizzata. Il costo dei test mirati e' quasi sempre inferiore a un nuovo turno di ragionamento; suite completa **una sola volta** al gate Windows/supportato, senza deroghe a 0 failure/error/skip.

## Integrita' dell'evidenza del gate esterno

- Prima di registrare un gate Windows esterno, leggere il `summary.json` del run e verificarne timestamp, comando/suite, exit code e conteggi. Il gate completo richiede Rules, citation index ed Engine attesi, con `failure=0`, `error=0` e `skipped=0`.
- Confermare che l'evidenza copra il tree corrente: usare revision/hash registrati dal runner quando disponibili e controllare che file sorgente e test pertinenti non siano stati modificati dopo l'avvio del run. Timestamp e conteggio totale, da soli, non provano la corrispondenza.
- Verificare nei log o nella discovery del runner che i nuovi test richiesti siano stati inclusi. Un aumento del conteggio della suite e' solo un indizio, non prova quale modulo sia stato eseguito.
- Ogni modifica successiva a codice o test invalida l'evidenza per gli artefatti modificati. Conservare il run precedente come storico e richiedere il gate applicabile sul tree aggiornato prima di marcare `done`.
- Se il runner supportato e' bloccato dal sandbox Codex, non aggirare il controllo ACL/AuthorizationManager e non qualificare il tentativo come esito della suite. Registrare comando, blocker operativo e comando Windows riproducibile per acquisire il gate esterno; nel frattempo sono ammissibili solo verifiche mirate indipendenti.

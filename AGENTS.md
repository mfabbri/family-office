# Family Office AI — AGENTS.md (policy essenziale)

Missione: Family Office AI produce decisioni familiari spiegabili usando fatti tracciati, regole versionate e calcoli deterministici. L'AI non calcola imposte, pensioni, risultati finanziari o diritti individuali.

## Invarianti non negoziabili

- Dati personali solo in `family-office-workspace/`; niente dati identificativi in repository software, log e fixture.
- Per **nuove** regole o nuove interpretazioni legali: fonte ufficiale → Knowledge → Rules versionate → test sintetici → Engine; review normativa indipendente con ambito, versione, hash e periodo.
- Per modifiche **tecniche a contratti normativi già approvati**: implementare e testare senza riaprire automaticamente l'interpretazione; riesame normativo solo con trigger sostanziale documentato. Vedere `12-dual-gate-and-convergence.md`.
- Output distinguono sempre fatto, ipotesi/proiezione, dato sconosciuto, `data_gaps` e determinazione amministrativa effettiva. `null`/`not_assessed` non è un diritto negato né un valore stimato.
- Nessun bypass dei guardrail di hash, fonte, temporalità, privacy, AML/KYC e non-inferenza; non trasformare assenza/`not_matched` in eligibility, importo o pagamento.
- Mai chiudere un incremento funzionale o release senza test riproducibili. Al gate finale la suite completa sul sistema supportato deve avere 0 failure, 0 errori, 0 skipped; esiti limitati non chiudono parent o discendenti.
- Non saltare predecessori incompleti nella roadmap attiva. È lecito completare preparazioni tecniche indipendenti senza dichiarare chiusi i gate o sbloccare i discendenti.
- Nessun commit/push, accesso a dati reali, modifica di ambienti esterni o operazione irreversibile senza autorizzazione pertinente.
- Evitare la modifica manuale di JSON per gli utenti ordinari: preferire wizard, import o `prepare` con validazione.
- Ogni capability deve partire da una domanda o decisione familiare e mostrare output, assunzioni, provenance e prossima azione.
- Per asset produttivi e opportunità di investimento consultare `11-investment-opportunity.md` quando pertinente.

## Caricamento selettivo

- Task minimo (typo/fix locale): leggi solo i file interessati; usa test mirati. Niente lettura obbligatoria dell'intera governance.
- Lavoro di roadmap: `family-office-bootstrap/planning/current-work.json`, `family-office-engine/docs/roadmap/roadmap-index.md`, `family-office-engine/docs/current-next-increment.md` e solo roadmap attiva. Esegui `roadmap_audit.py` prima di selezione/chiusura.
- Routing e delega: `$family-office-model-router`, `00-task-router.md`, `02-model-routing.md`, `03-subagent-policy.md` **solo quando servono**. La classificazione dipende da ciò che cambia, non dalla materia menzionata.
- Lavoro normativo: `07-normative-change.md`; lavoro su blocchi, prerequisiti, pensioni future o review inconcludenti: `12-dual-gate-and-convergence.md`.
- Non impostare l'intero processo come attesa di un reviewer. L'implementatore lavora sugli artefatti già approvati; in caso di review senza verdetto registrare PENDING e terminare il tentativo, senza nuovi retry impliciti.

## Criterio di done

Prima di dichiarare `done`, mostra file modificati, comportamento osservabile, test mirati/integrati, suite completa al gate, limiti normativi, gap e decisione sullo stato roadmap. Verifica `family-office-bootstrap/planning/validate-execution-guardrails.py` al gate; non chiamare un timeout GO/NO-GO.

Istruzioni specializzate: `family-office-engine/AGENTS.md`, `family-office-rules/AGENTS.md`, `family-office-knowledge/AGENTS.md` prevalgono per il rispettivo sottoalbero.

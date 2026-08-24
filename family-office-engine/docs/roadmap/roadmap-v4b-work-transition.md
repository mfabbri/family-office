# V4B Roadmap — Work Transition & Retirement Bridge

## Obiettivo

Trasformare la capability V4.8c da ricerca di un hard stop annuale a un motore deterministico che trovi **quando ridurre il lavoro full-time, quanto lavorare part-time, quando cessare del tutto e come finanziare il ponte fino alle pensioni**, preservando liquidita', obiettivi familiari e un livello di rischio dichiarato.

Il motore deve produrre almeno tre date distinte: `earliest_full_time_exit_date`, `recommended_full_time_exit_date` e `full_work_exit_date`. Le decorrenze INPS, Seguridad Social e RITA sono stream separati e non coincidono per default con la cessazione.

## Perche' questa roadmap esiste

V4.8c `work-exit-feasibility/v1` e' utile come proof-of-capability ma non e' sufficiente per il golden use case:

- usa granularita' annuale;
- prima della candidate date assume implicitamente che il lavoro copra le spese e non modella il risparmio accumulato;
- non rappresenta fasi 100% → 80/60/50/40% → 0%;
- l'INPS interno viene calcolato sulla candidate date, senza un entitlement timeline separato dalla cessazione;
- non modella netto da lavoro e contribuzione futura come funzione dell'FTE;
- non compone in modo nativo RITA, redditi familiari e prelievi patrimoniali con start/end mensili;
- non applica sequence-of-returns risk a una transizione plurifase;
- puo' confrontare importi lordi pensionistici con fabbisogni di spesa senza un unico contratto gross/net household.

Per coerenza con la regola di non anticipazione dell'AI, V5.1 e V5.2 restano completati ma V5.3+ attendono questo gate.

## Invarianti di dominio

1. `full_time_exit_date`, `work_cessation_date`, `pension_entitlement_date` e `pension_payment_start_date` non sono sinonimi.
2. Il calcolo primario usa timeline mensile; gli aggregati annuali sono derivati.
3. Ogni fase lavorativa ha FTE, start/end e regola di compensazione dichiarata.
4. Il netto non e' ottenuto moltiplicando il netto full-time per l'FTE.
5. Contributi INPS, TFR e previdenza complementare variano con la fase lavorativa secondo regole versionate o gap espliciti.
6. Ogni pensione e RITA ha diritto, start/end, lordo/netto, tassazione e provenance separati dove disponibili.
7. Gli asset sono spendibili solo quando il liquidity plan li rende disponibili.
8. Il baseline deterministico precede lo stress stochastic; il Monte Carlo non maschera input mancanti.
9. Un dato mancante che puo' cambiare la data di uscita produce `blocked` o riduce confidence; non viene stimato dall'LLM.
10. Tutti gli optimizer devono spiegare candidate scartate, vincoli violati e sensitivity principali.

## Pipeline target

```text
workspace facts + freshness/provenance
        ↓
work-transition-readiness/v1
        ↓
work-transition-scenario/v1 (fasi FTE mensili)
        ↓
employment-income-projection/v1
        ↓
pension-entitlement-timeline/v1
        ↓
retirement-bridge-timeline/v1
        ↓
work-transition-simulation/v1
        ↓
work-transition-candidate-set/v1
        ↓
work-transition-optimizer/v1
        ↓
work-transition-plan/v1 + evidence
```

## Incrementi

### V4.11 — Work-transition data readiness and lineage gate

**Stato:** `done`
**Tipo:** `functional`

Riconciliare freshness, provenance e precedence degli snapshot necessari al golden use case prima di aggiungere nuovi calcoli.

- Dipende da: V4.2, V4.3, V4.6e, V4.8a, V4.8c.
- Repository: `engine`, `workspace`.
- Output: `work-transition-readiness/v1`.
- Test: payroll vs manual assumptions, spouse income, spese, liquidita', asset duplicati, gross/net mismatch, snapshot stale, path multipiattaforma.
- Done quando: ogni input necessario e' selezionato o bloccato con lineage e freshness espliciti.

### V4.12 — Monthly work-transition scenario contract

**Stato:** `done`
**Tipo:** `functional`

Definire fasi lavorative mensili per ogni adulto: full-time, uno o piu' livelli part-time, cessazione e opzionale rientro.

- Dipende da: V4.11.
- Repository: `engine`, `workspace`.
- Output: `work-transition-scenario/v1`.
- Campi minimi: persona, start/end, FTE, status, compensation policy, contribuzione/benefit policy reference, vincoli contrattuali dichiarati.
- Test: 100→60→0, fasi sovrapposte, gap temporali, durata zero, due adulti, date invalide.
- Done quando: `full_time_exit_date` e `work_cessation_date` sono derivabili senza assumere pensionamento.

### V4.13 — Italian employment net-income and contribution projection

**Stato:** `planned`
**Tipo:** `functional`

Calcolare per fase il cashflow da lavoro e l'accumulo previdenziale usando rule pack italiani versionati e dati dichiarati/observed.

- Dipende da: V4.12 e rule pack fiscali/contributivi disponibili.
- Repository: `knowledge`, `rules`, `engine`.
- Output: `employment-income-projection/v1`.
- Include dove supportato: lordo, contributi lavoratore, imponibile, IRPEF/addizionali, netto, TFR, Fon.Te/previdenza complementare lavoratore e datore.
- Test: FTE 100/60/40, mensilita' aggiuntive, soglie fiscali, contributi, part-time non lineare sul netto, dato documentale vs proiezione.
- Done quando: ogni fase produce netto e contribuzione tracciabili oppure gap; nessun `net_full_time × FTE`.

### V4.14 — Entitlement-driven pension timeline IT/ES/EU

**Stato:** `planned`
**Tipo:** `functional`

Ricalcolare pensione e decorrenze in funzione della carriera generata dallo scenario, mantenendo separati diritto, decorrenza e importo.

- Dipende da: V4.13, V4.6e, V4.8a.
- Repository: `knowledge`, `rules`, `engine`.
- Output: `pension-entitlement-timeline/v1`.
- Include: stima INPS interna per scenario, benchmark INPS documentale, entitlement/eligibility rules, Spagna teorica e pro-rata UE, stream del coniuge.
- Test: cessazione prima della pensione, part-time che cambia montante, date diritto diverse dalle date pagamento, totalizzazione UE, regole future non consolidate, spouse gap.
- Done quando: nessuno stream pensionistico inizia per default alla `work_cessation_date`.

### V4.14a — Work-transition normative and contract audit

**Stato:** `planned`
**Tipo:** `audit`

Audit dovuto dopo V4.11-V4.14 prima di introdurre il decumulo integrato.

- Dipende da: V4.14.
- Repository: `bootstrap`, `knowledge`, `rules`, `engine`.
- Checklist: `family-office-bootstrap/docs/code-audit-checklist.md` + `11-work-transition-retirement-bridge.md`.
- Done quando: timeline, gross/net, contribuzione e entitlement sono coerenti, testati e senza blocker impliciti.

### V4.15 — Retirement bridge income composer

**Stato:** `planned`
**Tipo:** `functional`

Comporre gli stream che finanziano il periodo tra riduzione/cessazione e pensioni.

- Dipende da: V4.14a, V4.2, V4.3, RITA V2.
- Repository: `engine`, `rules`, `workspace`.
- Output: `retirement-bridge-timeline/v1`.
- Stream: reddito proprio residuo, coniuge, affitti, RITA, pensioni gia' attive, liquidita'/asset withdrawals e altri flussi espliciti.
- Test: RITA con start/end, asset vincolato, reddito coniuge, affitto, gap di eleggibilita', doppio conteggio.
- Done quando: il bridge e' una timeline mensile di stream con disponibilita' e trattamento gross/net espliciti.

### V4.16 — Monthly decumulation and sequence-risk simulation

**Stato:** `planned`
**Tipo:** `functional`

Eseguire il bilancio mensile household e il decumulo per bucket, prima deterministico e poi con stress stochastic separato.

- Dipende da: V4.15, V4.3, V4.5.
- Repository: `engine`.
- Output: `work-transition-simulation/v1`.
- Metriche: shortfall mensile, prelievi, reserve months, depletion, terminal wealth, tax/cost drag supportato, P05/P50/P95 e success probability per stress.
- Test: inflazione, crash iniziale, ponte lungo, RITA temporanea, pensioni differite, emergenza minima, seed riproducibile.
- Done quando: sequence-of-returns e liquidita' possono cambiare l'esito senza alterare il baseline deterministico.

### V4.17 — Phased-work candidate generator

**Stato:** `planned`
**Tipo:** `functional`

Generare una griglia controllata di alternative full-time/part-time/cessazione evitando combinazioni opache o ingestibili.

- Dipende da: V4.16.
- Repository: `engine`, `workspace`.
- Output: `work-transition-candidate-set/v1`.
- Dimensioni: data uscita full-time, FTE ammessi, durata fasi, data cessazione, policy RITA/bridge ammesse, constraint familiari.
- Test: griglia limitata, candidate duplicate, vincoli incompatibili, pruning spiegabile.
- Done quando: ogni candidate ha ID/hash, scenario derivato e motivo di inclusione/esclusione.

### V4.18 — Earliest/recommended/full work-exit optimizer

**Stato:** `planned`
**Tipo:** `functional`

Valutare le candidate e restituire date e alternative ordinate secondo constraint trasparenti.

- Dipende da: V4.17.
- Repository: `engine`.
- Output: `work-transition-optimizer/v1`.
- Output minimo: `earliest_full_time_exit_date`, `recommended_full_time_exit_date`, `full_work_exit_date`, piano FTE, pension start dates, success probability, P05 terminal wealth, minimum liquidity buffer, rejected candidates e sensitivity.
- Test: earliest non recommended, part-time migliore di hard stop, nessuna candidate sostenibile, constraint terminal wealth, probability threshold, reversibilita'.
- Done quando: il ranking e' spiegabile e una data non viene emessa se un gap bloccante puo' materialmente modificarla.

### V4.18a — Optimizer and stochastic audit

**Stato:** `planned`
**Tipo:** `audit`

Audit dovuto dopo V4.15-V4.18.

- Dipende da: V4.18.
- Repository: `engine`, `rules`, `knowledge`.
- Focus: determinismo, seed, pruning, metriche, no gross/net mixing, no pension-start shortcut, performance e regressioni.
- Done quando: nessun difetto di contract o simulazione blocca l'integrazione con tool registry.

### V4.19 — Legacy work-exit migration and tool-registry integration

**Stato:** `planned`
**Tipo:** `functional`

Integrare i nuovi tool nel registry V5.1 e definire il destino di `work-exit-feasibility/v1` senza rompere gli utenti esistenti.

- Dipende da: V4.18a, V5.1.
- Repository: `engine`, `bootstrap`.
- Output: registry aggiornato, compatibility adapter o deprecation notice versionata, migration guide.
- Test: vecchio comando continua o fallisce con migrazione esplicita; versioni tool; planner future-proof.
- Done quando: V5 puo' invocare soltanto i nuovi tool registrati per il golden use case e il legacy non viene confuso con l'optimizer completo.

### V4.20 — Golden use case and V5 resume gate

**Stato:** `planned`
**Tipo:** `functional`

Chiudere la roadmap con un workflow end-to-end sintetico e un readiness report applicabile al workspace reale.

- Dipende da: V4.19.
- Repository: `engine`, `bootstrap`, `workspace`.
- Output: `work-transition-plan/v1`, comando breve `fo planning work-transition plan` e golden scenario sintetico.
- Golden path: full-time → part-time → cessazione → RITA/patrimonio → pensione ES → pensione INPS, con spouse income e stress avverso.
- Test: end-to-end, lineage, data gaps, Windows/Linux, reproducibility, no personal data nelle fixture.
- Done quando: il comando produce le tre date, piano per fasi, bridge, pension start dates, metriche di rischio, motivi delle candidate scartate e blocker; il gate V4B → V5 e' verificato e, nello stesso aggiornamento di governance, `roadmap-v4b-work-transition.md` passa a `done`, V5 torna `in_progress` e `current-next-increment.md` viene posizionato su V5.3.

## Exit criteria V4B

- Il sistema non usa piu' `work-exit-feasibility/v1` come risposta completa al phased retirement.
- La data di uscita dal full-time puo' precedere di anni la cessazione e la pensione.
- Il part-time modifica sia cashflow corrente sia contribuzione/pensione futura.
- RITA e asset bridge rispettano eleggibilita', start/end e liquidita'.
- Il risultato distingue lordo/netto e segnala tassazione non disponibile.
- Il baseline e' mensile e deterministico; lo stress stochastic e' riproducibile.
- Le tre date chiave e almeno 2 alternative sono spiegabili e tracciabili.
- V5.1 tool registry e' aggiornato; V5.3 puo' riprendere senza chiedere all'LLM di inventare calcoli mancanti.

## Fuori perimetro

- negoziazione con il datore di lavoro o garanzia che un part-time sia contrattualmente ottenibile;
- certificazione ufficiale INPS/Seguridad Social/P1;
- consulenza legale, fiscale o previdenziale sostitutiva del professionista;
- previsione certa di norme future;
- ottimizzazione opaca non riconducibile a scenario, regole e metriche.

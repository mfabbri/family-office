# Agent Session Prompt

Il prompt breve già usato nel progetto resta valido:

```text
Leggi AGENTS.md, applica i playbook e completa autonomamente il prossimo incremento
della roadmap, includendo piano, implementazione, test e aggiornamento dello stato.
```

`AGENTS.md` obbliga ora il parent a consultare planner e router prima della delega.

Per una sessione diagnostica più esplicita si può usare:

```text
Lavora nel repository Family Office AI.

Leggi AGENTS.md e applica le skill $family-office-session,
$family-office-planner e $family-office-model-router. Verifica
family-office-bootstrap/planning/current-work.json e il roadmap audit.

Se esiste un incremento selected/in_progress, conferma che sia ancora aperto e
coerente con roadmap e repository; altrimenti usa l'algoritmo di roadmap-index.md
per selezionare un solo micro-incremento.

Produci il task envelope e registra nel planner tier, agent, modello, reasoning e
motivazione prima di delegare. Il parent Luna/medium è il router/controller:
Luna per discovery/docs, Terra per planning/implementazione/quality review, Sol per
architettura e review finanziaria o normativa critica.

Mantieni distinti fo_financial_reviewer e fo_normative_reviewer: il primo verifica
formule/scenari/leverage, il secondo fonti/validità temporale/fiscalità/compliance.
Non usare LLM per sostituire calcoli fiscali, pensionistici o finanziari deterministici.
Mantieni knowledge → rules → tests → engine, provenance, data gaps e privacy. Esegui
i test proporzionati al rischio e aggiorna lo stato solo con evidenze riproducibili.
```

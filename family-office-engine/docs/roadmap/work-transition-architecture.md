# Work Transition Architecture — Direction Change

## Decision

Il golden use case "quando posso lasciare il full-time, eventualmente lavorare part-time, e come finanzio il ponte fino alle pensioni" diventa una capability deterministica di primo livello. V5 AI Orchestration non deve compensare le lacune del modello con prompt o stime LLM.

## Baseline osservata

La baseline analizzata contiene V4.8c `work-exit-feasibility/v1` e V4.10 `wealth-strategy/v1`. V4.8c cerca candidate annuali e compone pensioni lorde, ma il servizio corrente:

- non ha un employment cashflow prima della candidate date: lo shortfall pre-candidate e' forzato a zero;
- usa una sola candidate date come data di cessazione e, per la stima INPS interna, come start dello stream;
- proietta contributi usando un unico reddito annuo costante fino alla candidate, senza fasi FTE;
- usa un saldo `available_bridge_assets` e spesa annua costante, non una timeline mensile di bucket e stream;
- non collega il decumulo V4.3 e il Monte Carlo a una sequenza full-time/part-time/bridge;
- non definisce una policy unica per gross/net tra redditi, pensioni e spese.

Nella baseline fornita non risultano inoltre un `family-office-workspace/planning/work-exit-feasibility.json` o uno snapshot reale omonimo: il percorso e' quindi implementato e testato, ma non ancora un golden workflow household operativo.

## Correzione architetturale

Separare il problema in quattro layer:

1. **Facts/readiness** — scegliere dati coerenti con freshness, provenance e no-double-count.
2. **Timeline economico-previdenziale** — lavoro, contribuzione, entitlement, pensioni e bridge su mesi.
3. **Simulation** — cashflow/decumulo deterministico + stress stochastic riproducibile.
4. **Optimization** — generare candidate discrete, verificare constraint, spiegare ranking e scarti.

## Date che non devono collassare

- `full_time_exit_date`: primo giorno fuori dal 100% FTE;
- `work_cessation_date`: primo giorno senza reddito da lavoro della persona;
- `pension_entitlement_date`: prima data in cui il diritto risulta maturato secondo rule pack/proiezione;
- `pension_payment_start_date`: decorrenza amministrativa dello stream, se codificata o dichiarata;
- `rita_start_date` / `rita_end_date`: finestra del bridge complementare;
- pensioni IT ed ES hanno date autonome.

## Contratti target

| Contratto | Responsabilita' |
|---|---|
| `work-transition-readiness/v1` | facts, freshness, precedence, gaps |
| `work-transition-scenario/v1` | fasi FTE mensili e vincoli |
| `employment-income-projection/v1` | lordo/netto, contribuzione, TFR, fondo pensione |
| `pension-entitlement-timeline/v1` | diritto, decorrenza e importi per scenario |
| `retirement-bridge-timeline/v1` | RITA, spouse/rent, pensioni attive, withdrawals |
| `work-transition-simulation/v1` | cashflow, decumulo, stress e risk metrics |
| `work-transition-candidate-set/v1` | candidate discrete e pruning |
| `work-transition-optimizer/v1` | tre date chiave, ranking, rejected reasons |
| `work-transition-plan/v1` | piano end-to-end e evidence |

## Compatibility

`work-exit-feasibility/v1` non va cancellato durante V4B. Deve essere marcato come legacy e mantenuto come diagnostica semplice finche' V4.19 non introduce adapter/deprecation esplicita e aggiorna il tool registry.

## Boundary AI

L'AI puo' in futuro trasformare "vorrei passare al 60% nel 2030" in un draft `work-transition-scenario/v1`, ma non puo':

- calcolare il netto part-time;
- decidere aliquote/contributi;
- spostare la decorrenza pensionistica;
- inventare eleggibilita' RITA;
- stimare success probability;
- scegliere una data se un tool deterministico e' bloccato.

## Acceptance outcome

Il report finale deve rispondere con tre date e almeno due alternative, mostrando: piano FTE, cashflow bridge, pension start dates, patrimonio usato per bucket, probability of success, P05 terminal wealth, minimum liquidity buffer, sensitivity principali, data gaps e motivi delle candidate scartate.

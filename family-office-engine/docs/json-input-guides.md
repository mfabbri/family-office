# JSON input guides

Questa pagina elenca gli input JSON che l'utente puo' dover compilare manualmente per le capability CLI attive. I file reali stanno in `family-office-workspace/`; gli esempi in `examples/` sono sintetici.

## Regole generali

- Mantieni lo stesso `household_id` tra file collegati.
- Usa ID tecnici, non dati personali reali.
- Usa date ISO `YYYY-MM-DD` e valute ISO maiuscole come `EUR`.
- Metti le incertezze note in `data_gaps` invece di trasformarle in dati certi.
- Non inserire calcoli fiscali, pensionistici o finanziari stimati a mano se il campo richiede un fatto osservato.

## `base-assumptions.json`

- Default: `../family-office-workspace/assumptions/base-assumptions.json`.
- Template/draft: `../family-office-workspace/assumptions/base-assumptions.template.json`, `base-assumptions.draft.json`.
- Comandi: `assumptions prepare`, `assumptions import`, `assumptions check`.
- Campi principali: `personal` per eta' e pensionamento target, `cashflow` per redditi/spese esplicite, `returns` per ipotesi tecniche dichiarate.

## `household-facts/v1`

- Default: `../family-office-workspace/household/household-facts.json`.
- Esempio: `examples/household-facts-sample.json`.
- Draft: `../family-office-workspace/household/household-facts.draft.json`.
- Comando: `household validate`.
- Campi: `household_id`, `persons`, `relationships`, `tax_residences`, `economic_roles`, `relevant_dates`, `data_gaps`.

## `ownership-beneficiary-graph/v1`

- Default: `../family-office-workspace/household/ownership-beneficiaries.json`.
- Esempio: `examples/ownership-beneficiary-graph-sample.json`.
- Draft: `../family-office-workspace/household/ownership-beneficiaries.draft.json`.
- Comando: `household ownership validate`.
- Campi: asset, debiti, quote, beneficiari, provenance, data gaps e riferimenti agli ID persona.

## `asset-availability/v1`

- Default: `../family-office-workspace/household/asset-availability.json`.
- Esempio: `examples/asset-availability-sample.json`.
- Draft/guida: `../family-office-workspace/household/asset-availability.draft.json`, `asset-availability-guide.md`.
- Comando: `household availability validate`.
- Campi: `asset_id`, asset class, rischio, valuta, giurisdizione, liquidita', vincoli, trattamento fiscale dichiarativo, prima disponibilita' e provenance.

## `timeline-events/v1`

- Default: `../family-office-workspace/household/timeline-events.json`.
- Esempio: `examples/timeline-events-sample.json`.
- Draft: `../family-office-workspace/household/timeline-events.draft.json`.
- Comando: `household timeline validate`.
- Campi: eventi puntuali, periodi, ricorrenze, priorita', persone o asset collegati, date e data gaps.

## `lifecycle-expenses/v1` input

- Default: `../family-office-workspace/household/lifecycle-expenses.json`.
- Comando: `expenses build-lifecycle`.
- Campi: anni o periodi, categorie di spesa, importi annui o ricorrenti, valuta, inflazione dichiarata e provenance.
- Nota: il motore annualizza solo spese dichiarate e non stima budget mancanti.

## `planning-goals/v1`

- Default: `../family-office-workspace/household/planning-goals.json`.
- Esempio: `examples/planning-goals-sample.json`.
- Draft: `../family-office-workspace/household/planning-goals.draft.json`.
- Comandi: `planning goals wizard`, `planning goals prepare`, `planning goals status`, `planning goals validate`, `planning goals demo`.
- Campi: `objectives`, `constraints`, `planning_horizon`, `risk_profile`, `liquidity_policy`, `data_gaps`.

## `liquidity-plan-input/v1`

- Default: `../family-office-workspace/planning/liquidity-plan-input.json`.
- Esempio: `examples/liquidity-plan-input-sample.json`.
- Guida: `examples/liquidity-plan-input-guide.md`.
- Draft: `../family-office-workspace/planning/liquidity-plan-input.draft.json`.
- Comandi: `planning liquidity wizard`, `planning liquidity build`, `planning liquidity demo`.
- Campi: `household_id`, `as_of_date`, `base_currency`, `monthly_expenses`, `minimum_reserve_months`, `concentration_threshold`, `data_gaps`.

## `decumulation-policy-set/v1`

- Default: `../family-office-workspace/planning/decumulation-policy-set.json`.
- Esempio: `examples/decumulation-policy-set-sample.json`.
- Guida: `examples/decumulation-policy-set-guide.md`.
- Draft: `../family-office-workspace/planning/decumulation-policy-set.draft.json`.
- Comandi: `planning decumulation wizard`, `planning decumulation build`, `planning decumulation demo`.
- Campi: `household_id`, `as_of_date`, `base_currency`, `current_age`, `policies`, `data_gaps`.
- Ogni policy dichiara `policy_id`, `label`, `retirement_age`, `end_age`, `annual_spending_need`, `cash_buffer_target`, `withdrawal_order`, `annual_return_sequence`, tassi espliciti e `include_rita`.

## `pension-contribution-input/v1`

- Default: `../family-office-workspace/planning/pension-contribution-input.json`.
- Esempio: `examples/pension-contribution-input-sample.json`.
- Comandi: `planning pension-contributions build`, `planning pension-contributions demo`.
- Campi: `household_id`, `as_of_date`, `tax_year`, `jurisdiction`, `marginal_tax_rate`, `already_deducted_contributions`, `first_employment_extra_deduction_room`, `available_liquidity`, `minimum_liquidity_after_contributions`, `options`, `data_gaps`.
- Ogni opzione dichiara `option_id`, `label`, `employee_contribution`, `employer_contribution`, `tfr_transfer`, `opportunity_cost_rate` e `horizon_years`.
- Nota: `marginal_tax_rate`, liquidita', costo opportunita' e contributi sono input dichiarati; il motore non calcola IRPEF completa o rendimenti.

## Scenario decisionale

### `decision-scenario-v2.json`

- Default: `../family-office-workspace/scenarios/decision-scenario-v2.json`.
- Esempio: `examples/decision-scenario-input-sample.json`.
- Comando: `scenarios compose-v2`.
- Campi: riferimenti scenario, summary, assunzioni esplicite, obiettivi e data gaps.

### `decision-outcome.json`

- Default: `../family-office-workspace/scenarios/decision-outcome.json`.
- Esempio: `examples/decision-outcome-input-sample.json`.
- Comando: `scenarios evaluate`.
- Campi: evaluator, parametri, seed e metriche richieste.

### `sensitivity-analysis.json`

- Default: `../family-office-workspace/scenarios/sensitivity-analysis.json`.
- Esempio: `examples/sensitivity-analysis-input-sample.json`.
- Comando: `scenarios sensitivity`.
- Campi: variabili perturbate, stress combinati, metrica di impatto e opzionale `outcome_evaluation`.

### `decision-score.json`

- Default: `../family-office-workspace/scenarios/decision-score.json`.
- Esempio: `examples/decision-score-input-sample.json`.
- Comando: `scenarios score`.
- Campi: alternative, `outcome_ref`, pesi, mapping da metriche policy a metriche outcome.

### `decision-dossier.json`

- Default: `../family-office-workspace/scenarios/decision-dossier.json`.
- Esempio: `examples/decision-dossier-input-sample.json`.
- Comando: `scenarios dossier`.
- Campi: titolo dossier, sezioni, alternative incluse, note di revisione e limiti.

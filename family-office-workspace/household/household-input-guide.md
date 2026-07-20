# Household Input Guide

Questa guida serve per compilare i file privati in `family-office-workspace/household/` senza leggere direttamente gli schema JSON dell'engine.

## Ordine consigliato

1. Compila `household-facts.json` partendo da `household-facts.draft.json`.
2. Esegui `fo household validate` e correggi errori o gap essenziali.
3. Compila `ownership-beneficiaries.json` partendo da `ownership-beneficiaries.draft.json`, usando gli stessi `person_id`.
4. Esegui `fo household ownership validate`.
5. Compila `asset-availability.json` partendo da `asset-availability.draft.json`, usando gli stessi `asset_id`.
6. Esegui `fo household availability validate`.
7. Compila `timeline-events.json` partendo da `timeline-events.draft.json`, usando gli stessi `person_id` e `asset_id`.
8. Esegui `fo household timeline validate`.
9. Esegui `fo planning goals status` per vedere se manca l'input, se il draft e' ancora da compilare o se lo snapshot e' pronto.
10. Esegui `fo planning goals prepare` se `planning-goals.json` non esiste ancora.
11. Compila `planning-goals.json`, usando gli `event_id` della timeline quando un vincolo dipende da un evento.
12. Esegui `fo planning goals validate`.

## Regole pratiche

- Usa ID stabili e leggibili, ad esempio `person_self`, `asset_main_brokerage`, `availability_main_brokerage`.
- Non stimare campi incerti: usa `unknown`, `null` o aggiungi una voce in `data_gaps`.
- `currency` usa codici ISO a 3 lettere, ad esempio `EUR`, `USD`, `GBP`.
- `jurisdiction` usa codici Paese a 2 lettere, ad esempio `IT`, `ES`, `US`.
- `provenance` deve spiegare da dove arriva il dato, ad esempio documento, estratto conto o inserimento manuale revisionato.
- Le date sono in formato `YYYY-MM-DD`.

Guide dettagliate per i due file piu' importanti del liquidity plan:

- `ownership-beneficiaries-guide.md`: significato di asset, debiti, quote, titolari e beneficiari.
- `asset-availability-guide.md`: significato di liquidita', vincoli, rischio, giurisdizione e trattamento fiscale descrittivo.

## Asset availability

Campi principali per ogni asset:

- `asset_id`: deve corrispondere a un asset di `ownership-beneficiaries.json`.
- `asset_class`: `cash`, `deposit`, `brokerage`, `pension_fund`, `insurance_policy`, `real_estate`, `company_share`, `other`.
- `risk_level`: `low`, `medium`, `high`, `illiquid`, `unknown`.
- `liquidity_tier`: `immediate`, `short_term`, `notice_required`, `locked_until_date`, `illiquid`, `unknown`.
- `constraints`: lista di vincoli, ad esempio `none`, `pension_lock`, `policy_terms`, `mortgage_or_lien`, `co_ownership`, `foreign_reporting`, `sale_process`, `other`, `unknown`.
- `tax_treatment`: etichetta dichiarativa, non calcolo fiscale. Usa `unknown` se non e' stato verificato.
- `first_available_date`: prima data in cui l'asset puo' essere usato o liquidato secondo le informazioni disponibili.

## Validazione locale

Dal repository `family-office-engine`:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main household validate
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main household ownership validate
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main household availability validate
```

Gli snapshot vengono scritti in `family-office-workspace/snapshots/`. Errori e gap vanno corretti nei file privati, non negli esempi sintetici dell'engine.

Per provare il progresso della CLI senza ricordare path JSON, usa la demo sintetica:

```text
fo planning goals demo
```

Da checkout sorgente:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning goals demo
```

Quando i file privati sono pronti, il comando reale rimane corto perche' usa i default del workspace:

```text
fo planning goals status
fo planning goals prepare
fo planning goals validate
```

Da checkout sorgente:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning goals status
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning goals prepare
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning goals validate
```

## Timeline events

Campi principali per ogni evento:

- `event_id`: ID stabile, ad esempio `event_self_retirement`.
- `event_type`: `retirement`, `tax_regime_end`, `deadline`, `contribution`, `extraordinary_expense`, `succession`, `residence_change`, `asset_availability`, `other`.
- `timing_type`: `point`, `period`, `recurring`.
- `start_date`: data dell'evento o inizio periodo.
- `end_date`: fine periodo; lascia `null` per eventi puntuali.
- `recurrence`: per eventi ricorrenti, dichiara `frequency`, `interval` e `count` oppure `until_date`.
- `subject_person_id`: persona collegata, se applicabile.
- `related_asset_id`: asset collegato, se applicabile.

La timeline ordina e valida eventi dichiarati, ma non calcola importi, imposte, pensioni o cashflow.

## Planning goals

Campi principali:

- `household_id`: stesso ID usato in `household-facts.json`.
- `as_of_date`: data di revisione degli obiettivi, formato `YYYY-MM-DD`.
- `planning_horizon`: anni di inizio e fine del piano, ad esempio 2026-2055.
- `risk_profile.capacity`: capacita' finanziaria di assorbire perdite (`low`, `medium`, `high`, `unknown`).
- `risk_profile.tolerance`: comfort psicologico con volatilita' e ribassi (`low`, `medium`, `high`, `unknown`).
- `risk_profile.max_loss_ratio`: perdita massima accettabile, ad esempio `0.20` per 20%.
- `liquidity_policy.minimum_reserve_months`: mesi di spese da tenere liquidi prima di pianificare il resto.
- `liquidity_policy.preferred_bucket`: bucket preferito tra `emergency_reserve`, `short_term`, `medium_term`, `long_term`, `unknown`.
- `objectives`: risultati desiderati. Ogni obiettivo ha `objective_id`, `category`, `priority`, `target` e `time_horizon_year`.
- `constraints`: vincoli da rispettare. `hard` significa non negoziabile; `soft` significa preferenza forte ma rivedibile.

Categorie obiettivo ammesse:

```text
retirement_income, capital_preservation, liquidity, family_protection,
tax_efficiency, estate, education, real_estate, other
```

Operatori soglia ammessi:

```text
min, max, target, range
```

I goals dichiarano preferenze e limiti per gli incrementi V4. Non calcolano strategie, imposte, rendimenti o raccomandazioni.

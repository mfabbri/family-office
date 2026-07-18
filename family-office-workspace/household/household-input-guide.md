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
9. Compila `planning-goals.json` partendo da `planning-goals.draft.json`, usando gli `event_id` della timeline quando un vincolo dipende da un evento.
10. Esegui `fo planning goals validate`.

## Regole pratiche

- Usa ID stabili e leggibili, ad esempio `person_self`, `asset_main_brokerage`, `availability_main_brokerage`.
- Non stimare campi incerti: usa `unknown`, `null` o aggiungi una voce in `data_gaps`.
- `currency` usa codici ISO a 3 lettere, ad esempio `EUR`, `USD`, `GBP`.
- `jurisdiction` usa codici Paese a 2 lettere, ad esempio `IT`, `ES`, `US`.
- `provenance` deve spiegare da dove arriva il dato, ad esempio documento, estratto conto o inserimento manuale revisionato.
- Le date sono in formato `YYYY-MM-DD`.

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

- `planning_horizon`: anni di inizio e fine piano.
- `risk_profile`: capacita', tolleranza e perdita massima dichiarata.
- `liquidity_policy`: mesi minimi di riserva e bucket preferito.
- `objectives`: obiettivi con `objective_id`, categoria, priorita' e target dichiarato.
- `constraints`: vincoli con severita' `hard`/`soft`, priorita', soglia e riferimenti opzionali a obiettivi o eventi timeline.

I goals dichiarano preferenze e limiti per gli incrementi V4. Non calcolano strategie, imposte, rendimenti o raccomandazioni.

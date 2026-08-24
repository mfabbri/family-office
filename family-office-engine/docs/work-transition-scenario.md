# Work-transition scenario

`work-transition-scenario/v1` definisce la timeline mensile delle fasi lavorative per adulto. Consuma uno snapshot `work-transition-readiness/v1` gia' non bloccato e produce solo fasi FTE, riferimenti policy e date derivate di lavoro. Non calcola netto, imposte, contributi, TFR, RITA, pensioni, rendimenti o ottimizzazioni.

## Comandi

Con i default del workspace privato:

```text
fo planning work-transition scenario
```

Smoke sintetico riproducibile:

```text
fo planning work-transition scenario --demo
```

Il manifest predefinito e' `family-office-workspace/planning/work-transition-scenario.json`; lo snapshot viene scritto in `family-office-workspace/snapshots/work-transition-scenario.snapshot.json`. Il default legge `family-office-workspace/snapshots/work-transition-readiness.snapshot.json`.

## Manifest

Il contratto e' `schemas/work-transition-scenario-input.schema.json`. Il manifest dichiara:

- `plan_start_date` e `plan_end_date` come primi giorni del mese;
- `work_phases` con `member_id`, `start_date`, `end_date`, `status`, `fte`, policy di compensazione, policy contributi/benefit, vincoli contrattuali e provenance;
- `declared_timeline_gaps` quando una lacuna nella sequenza e' intenzionale e spiegata.

Le date di fase sono mensili e inclusive. `full_time` richiede `fte=1.0`, `part_time` richiede `0 < fte < 1`, `not_working` richiede `fte=0.0`. I membri devono esistere nello snapshot readiness e una readiness `blocked`, incoerente o con hash non verificabile impedisce la costruzione dello scenario.

Una lacuna dichiarata resta un blocker: viene registrata con motivo esplicito, ma non produce una timeline utilizzabile o date derivate finche' non esiste una fase mensile per quel periodo.

## Output

Lo snapshot contiene:

- una `monthly_timeline` per adulto;
- `full_time_exit_date` e `work_cessation_date` derivate per membro;
- date pensionistiche esplicitamente `null`, per non confondere cessazione e decorrenze;
- gap bloccanti per sovrapposizioni, lacune dichiarate/non dichiarate, fasi mancanti o membri non validi.

V4.13 potra' usare le fasi e i riferimenti policy per proiettare netto e contribuzione senza reinterpretare la sequenza lavorativa.

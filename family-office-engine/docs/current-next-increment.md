# Current Next Increment

## ID e titolo

V4.11 - Work-transition data readiness and lineage gate.

## Stato

`planned`

## Roadmap

`docs/roadmap/roadmap-v4b-work-transition.md`

## Motivazione e dipendenze

La baseline corrente dispone di `work-exit-feasibility/v1`, ma quel servizio valuta un hard stop annuale: non rappresenta fasi FTE, non accumula risparmio pre-uscita, non separa cessazione e decorrenza pensionistica e non ricostruisce un household cashflow coerente da fonti con freshness diverse. Prima di aggiungere nuovi calcoli occorre quindi un gate deterministico che selezioni, riconcili e qualifichi gli snapshot realmente utilizzabili dal nuovo pipeline Work Transition.

Dipendenze disponibili: V4.2 liquidita', V4.3 decumulo, V4.6e/V4.8a pensione Spagna-UE, V4.8c work-exit legacy, V5.1 tool registry e V5.2 citation index. V5.1 e V5.2 restano completati; V5.3+ sono sospesi fino alla chiusura della roadmap V4B.

Prima dell'implementazione eseguire sempre:

```text
python family-office-engine/src/family_office_engine/governance/roadmap_audit.py
```

## Piano operativo V4.11

1. Definire `work-transition-readiness/v1` e il contratto input senza dati personali nei repository software.
2. Inventariare le sorgenti candidate per reddito proprio/coniuge, spese, patrimonio, liquidita', RITA/previdenza complementare, INPS, Spagna/UE e altri redditi.
3. Definire una policy deterministica di freshness e precedence basata su provenance/as-of date, senza sovrascrivere conflitti.
4. Rilevare doppio conteggio, periodi mancanti, snapshot stale, importi gross/net incompatibili e stream senza start/end.
5. Produrre un readiness snapshot che distingua `ready`, `partial` e `blocked`, con gap bloccanti per qualunque input necessario al calcolo della data.
6. Aggiungere CLI breve `fo planning work-transition readiness` o equivalente, fixture sintetiche e test.
7. Aggiornare roadmap, decision log e documentazione solo a criteri di completamento verificati.

## File previsti

- `family-office-engine/schemas/` per i contratti Work Transition;
- `family-office-engine/src/family_office_engine/services/` per il readiness builder;
- `family-office-engine/src/family_office_engine/cli/main.py` o modulo CLI estratto se l'audit lo richiede;
- `family-office-engine/tests/` con fixture esclusivamente sintetiche;
- documentazione API/CLI/input guide e roadmap V4B.

## Test e verifiche

- selezione della fonte piu' recente senza perdere provenance;
- conflitto tra manual assumptions e payroll documentale;
- gross/net mismatch;
- asset duplicato o non liquidabile;
- pension snapshot senza decorrenza;
- household member mancante;
- path Windows/Linux;
- test mirati, regression appropriata e `roadmap_audit.py`.

## Criteri di completamento

- il pipeline Work Transition ha un unico readiness snapshot riproducibile come punto di ingresso;
- nessun valore stale o duplicato viene scelto silenziosamente;
- ogni dato usato o escluso ha provenance, as-of e motivo;
- un gap critico blocca l'ottimizzazione invece di produrre una data apparente;
- V4.12 puo' modellare le fasi lavorative senza dover riconciliare nuovamente le fonti.

## Rischi ed esclusioni

V4.11 non calcola imposte, pensioni, RITA, rendimenti o date di uscita. Non corregge manualmente dati personali e non copia dati reali nei repository software. Eventuali incoerenze nel workspace diventano data gaps o azioni di onboarding, non assunzioni implicite.

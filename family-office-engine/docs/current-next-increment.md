# Current Next Increment

## ID e titolo

V5.3d - Rentable movable asset / camper adapter.

## Stato

`planned`

## Roadmap

`docs/roadmap/roadmap-v5-ai-orchestration.md`

## Motivazione e dipendenze

V5.3c e' completato senza blocker impliciti. V5.3d e' il primo incremento funzionale pianificato con dipendenza soddisfatta.

Dipendenze: V5.3c e' `done`. Prima dell'avvio applicare `11-investment-opportunity.md` come T4 finanziario; coinvolgere `knowledge -> rules -> tests -> engine` soltanto se l'adapter richiede una nuova semantica fiscale. Nessuna aliquota o classificazione deve essere dedotta o hard-coded.

Prima dell'implementazione eseguire sempre:

```text
python family-office-engine/src/family_office_engine/governance/roadmap_audit.py
```

## Piano operativo V5.3d

1. Definire l'adapter `rentable-movable-asset/v1` sopra `investment-opportunity/v1`, senza duplicare formule comuni.
2. Modellare soltanto driver dichiarati per disponibilita', uso personale, noleggio, tariffa, fee piattaforma, costi, downtime, riparazioni e valore residuo.
3. Mantenere il beneficio di uso personale e la classificazione dell'attivita' separati dal cash flow imponibile; classificazione assente come `data_gap`.
4. Aggiungere fixture sintetiche, test unitari/integrativi e smoke CLI; eseguire regression e `roadmap_audit.py` prima della chiusura.

## Criteri di completamento V5.3d

- `rentable-movable-asset/v1` separa utilizzo personale, cash flow da noleggio e trattamento fiscale;
- confronto possibile con alternative sullo stesso capitale e orizzonte, senza assunzioni implicite;
- utilizzo, downtime, major repair, mixed use, zero rental, residual-value shock e classification gap coperti da test;
- provenance, privacy, data gaps, regression e audit verdi.

## Cadenza audit

Il contatore e' `functional_since_audit=1` dopo V5.3c. Il prossimo audit obbligatorio e' V5.3g, dopo quattro incrementi funzionali V5.3c-V5.3f.

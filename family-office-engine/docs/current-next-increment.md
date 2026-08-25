# Current Next Increment

## ID e titolo

V5.3f - Stress test and opportunity-cost comparator.

## Stato

`planned`

## Roadmap

`docs/roadmap/roadmap-v5-ai-orchestration.md`

## Motivazione e dipendenze

V5.3e e' completato senza blocker impliciti. V5.3f e' il primo incremento funzionale pianificato con dipendenze soddisfatte.

Dipendenze: V5.3c, V5.3d e V5.3e sono `done`. Prima dell'avvio applicare `11-investment-opportunity.md` come T4 finanziario. Il confronto deve usare lo stesso capitale e orizzonte dichiarati, senza introdurre benchmark, fiscalita' o rendimenti impliciti.

Prima dell'implementazione eseguire sempre:

```text
python family-office-engine/src/family_office_engine/governance/roadmap_audit.py
```

## Piano operativo V5.3f

1. Definire `investment-opportunity-comparison/v1` per scenari base/upside/adverse e opportunity cost sullo stesso capitale/orizzonte.
2. Riutilizzare output dichiarati degli adapter e del financing plan; rendere benchmark, liquidita', concentrazione e vincoli household input o data gap.
3. Modellare solo stress espliciti: ricavi/utilizzo/rate/value down e costi/debt service/downtime up secondo l'asset.
4. Aggiungere fixture sintetiche, test unitari/integrativi e smoke CLI; eseguire regression e `roadmap_audit.py` prima della chiusura.

## Criteri di completamento V5.3f

- confronto impone stesso capitale e orizzonte, con benchmark mancante esplicitato come gap;
- scenari avversi, cash flow negativo e liquidity breach restano osservabili senza assunzioni implicite;
- rendimento, rischio, liquidita' e management burden restano dimensioni separate dal ranking;
- provenance, privacy, data gaps, regression e audit verdi.

## Cadenza audit

Il contatore e' `functional_since_audit=3` dopo V5.3c-V5.3e. Il prossimo audit obbligatorio e' V5.3g, dopo quattro incrementi funzionali V5.3c-V5.3f.

# Current Next Increment

## ID e titolo

V5.8 - Response composer with citations.

## Stato

`planned`

## Roadmap

`docs/roadmap/roadmap-v5-ai-orchestration.md`

## Motivazione e dipendenze

V5.7 e' completato. V5.8 e' il primo incremento funzionale pianificato con dipendenze soddisfatte.

Dipendenze: V5.2 e V5.7 sono `done`. V5.8 deve comporre risposte esclusivamente da `evidence-bundle/v1` e citazioni indicizzate.

Prima dell'implementazione eseguire sempre:

```text
python family-office-engine/src/family_office_engine/governance/roadmap_audit.py
```

## Piano operativo V5.8

1. Definire un compositore che accetti esclusivamente evidenze e citazioni indicizzate.
2. Rendere espliciti facts, assunzioni, limiti, fonti, conflitti e richieste di revisione professionale.
3. Aggiungere fixture sintetiche, test e smoke CLI; eseguire regression e `roadmap_audit.py` prima della chiusura.

## Criteri di completamento V5.8

- ogni affermazione deriva da evidence bundle e citazione identificabile oppure resta un limite o assunzione;
- numeri, conflitti, errori e data gaps non vengono nascosti nella composizione;
- il compositore non ricalcola imposte, pensioni o valori finanziari.

## Cadenza audit

V5.4a e' l'ultimo audit completato. V5.5, V5.6 e V5.7 sono i primi tre incrementi funzionali successivi; V5.8 sarebbe il quarto e non richiede ancora un audit. Il successivo incremento funzionale richiedera' un audit prima dell'avvio.

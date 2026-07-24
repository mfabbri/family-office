# Current Next Increment

## ID e titolo

V4.8 - Insurance and family protection.

## Stato

`done`

## Roadmap

`docs/roadmap/roadmap-v4-wealth-planning.md`

## Motivazione e dipendenze

V4.7 e' completato: il motore ora dispone di `real-estate-plan/v1` per confrontare mantenimento, locazione e vendita su input immobiliari espliciti. L'audit cadence non richiede un nuovo audit prima di V4.8.

V4.8 dipende da V3.1-V3.3, gia' completati secondo la roadmap. L'incremento e' T2 se resta su modellazione strutturale di coperture e beneficiari; escalare se introduce calcoli assicurativi, legali o fiscali normativi.

## Piano operativo

1. Verificare contratti esistenti per household, ownership, asset availability, estate baseline e planning goals.
2. Definire input minimo `protection-gap/v1` per polizze, beneficiari, coperture, premi, riscatti e fabbisogno familiare.
3. Implementare servizio deterministico minimo senza dedurre beneficiari, capitali assicurati o fabbisogni mancanti.
4. Aggiungere fixture sintetiche e test su beneficiario mancante, capitale insufficiente e distinzione polizza investimento/protezione.
5. Collegare CLI e documentazione soltanto per i comandi necessari.
6. Eseguire test mirati e regression appropriata prima di segnare `done`.

## Perimetro previsto

- Modellazione e confronto deterministico di coperture assicurative e fabbisogni familiari.
- Nessun LLM nei calcoli; capitale assicurato, premi, beneficiari, riscatti e fabbisogni devono essere espliciti o derivare da servizi deterministici.
- Nessuna raccomandazione legale, fiscale, assicurativa o patrimoniale senza revisione professionale dichiarata.

## Input personali necessari

Da definire prima dell'implementazione: polizze rilevanti, assicurati, contraenti, beneficiari, capitale assicurato, premi, scadenze, riscatti, eventi coperti, fabbisogno familiare e provenance. Usare fixture sintetiche finche' non esiste input personale nel workspace.

## Stato implementazione

Completato. V4.8 introduce `protection-gap/v1` con servizio deterministico, fixture sintetica, CLI `planning protection build/demo`, documentazione API/CLI/input/testing e test. Il comando demo sintetico ha prodotto `protection-gap/v1` con 2 fabbisogni, 3 polizze e shortfall esplicito di 70000.00 EUR.

Verifiche riproducibili:

- `$env:PYTHONPATH='family-office-engine\src'; python -m unittest family-office-engine\tests\unit\test_protection_gap.py` -> 5 test OK.
- `$env:PYTHONPATH='family-office-engine\src'; python -m unittest family-office-engine.tests.unit.test_validate.ValidateCliTest.test_main_planning_protection_demo_returns_success` -> 1 test OK.
- `$env:PYTHONPATH='family-office-engine\src'; python -m family_office_engine.cli.main planning protection demo --output family-office-workspace\snapshots\cli-check-protection-gap.synthetic.snapshot.json` -> complete, 2 needs, 3 policies, shortfall=70000.00 EUR, 0 gaps.
- `$env:PYTHONPATH='family-office-engine\src'; python -m unittest discover family-office-engine\tests\unit` -> 428 test OK.

## Criteri di completamento

- Il piano protezione separa polizze di rischio, investimento e coperture miste.
- Beneficiari, capitale, fabbisogno familiare, premi e riscatti sono tracciati con provenance e gap.
- Valutazioni legali, fiscali e assicurative sono solo da input espliciti o rule pack versionati oppure esposte come gap.
- Test mirati e regression pertinente verdi.

## Incrementi successivi

V4.9 - Succession and donation planning V2.

## Rischi, esclusioni e blocker

- Possibile impatto legale, fiscale e assicurativo: seguire `knowledge -> rules -> tests -> engine` se servono regole nuove.
- Fuori perimetro iniziale: consulenza assicurativa, analisi sanitaria, atti legali, fiscalita' completa e raccomandazioni vincolanti.

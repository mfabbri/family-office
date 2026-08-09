# Sources

`citation-catalog.json` e' il catalogo strutturato delle fonti pubbliche usate dal corpus knowledge. Il catalogo non sostituisce le note: assegna citation ID stabili, giurisdizione, tema, autorita', finestra di validita' verificata e collegamenti ai documenti.

Le fonti mancanti o non ancora strutturate devono restare visibili come gap nell'indice; non aggiungere date, autorita' o stato per deduzione. Usare `source-template.md` per nuove fonti e seguire `knowledge -> rules -> tests -> engine` quando cambia il significato normativo.

## Semantica temporale

Nel catalogo `valid_from` e `valid_to` delimitano la finestra nella quale il progetto ha verificato la fonte come applicabile al relativo uso. Non rappresentano automaticamente le date giuridiche originarie di entrata in vigore o abrogazione. Quando la finestra verificata non e' disponibile, i campi restano `null` e il retrieval corrente deve escludere la fonte con stato `unknown_validity`.

## Granularita' e gap iniziali

Il collegamento V5.2 e' tra documento knowledge e citation ID. Indica quali fonti supportano il documento, ma non prova automaticamente ogni singola frase: una futura risposta deve collegare l'affermazione specifica all'evidenza pertinente.

Il corpus iniziale mantiene senza citation ID strutturato:

- `taxation/impatriati.md`;
- `pensions/inps-theoretical-pension-it.md`;
- `pensions/fonte.md`;
- `pensions/previdenza-complementare-deducibilita-it.md`;
- `international/spain-pension.md`.

Questi documenti restano indicizzati con `knowledge_document_citation_missing` e non devono essere trattati come supporto normativo completo finche' il gap non viene risolto.

# Current Next Increment

## ID e titolo

V4.6c - Italy-Spain foreign asset monitoring.

## Stato

`planned`

## Roadmap

`docs/roadmap/roadmap-v4-wealth-planning.md`

## Motivazione e dipendenze

V4.6e e' completato. Il prossimo incremento selezionabile torna alla sequenza V4 pianificata: integrare attivita' finanziarie, piani pensionistici e immobili spagnoli con monitoraggio fiscale italiano, IVAFE/IVIE, tax events e documenti.

L'incremento e' T4: tocca fiscalita' e monitoraggio patrimoniale transfrontaliero. Si applica il flusso `knowledge -> rules -> tests -> engine`.

## Piano operativo

Da definire all'avvio dell'implementazione V4.6c.

## Perimetro previsto

- Classificazione di conti, fondi, piani pensionistici e immobili spagnoli.
- Rule pack per obblighi di monitoraggio, basi imponibili ed esenzioni motivate.
- Contratto `it-es-foreign-assets/v1`, servizio deterministico e CLI.
- Fixture sintetiche e test su conto, fondi, piano pensionistico, immobile, intermediario residente/non residente e dato non classificato.

## Input personali necessari

- Rendiconti e dati di titolarita' per attivita' spagnole detenute o movimentate nel periodo d'imposta.
- Classificazione dell'intermediario e paese di detenzione.
- Valori di fine periodo, giorni di detenzione e movimenti rilevanti dove richiesti.

## Stato implementazione

Non iniziato. Piano operativo da salvare prima di modificare knowledge, rules, engine o workspace.

## Criteri di completamento

- Obblighi dichiarativi e impatti sono esposti senza dedurre esenzioni non documentate.
- Titolarita', intermediario, giurisdizione e provenance restano trasparenti.
- Nessun valore fiscale e' hard-coded nell'engine.
- Test pertinenti e regression appropriata verdi; review indipendente delle fonti completata.

## Incrementi successivi

V4.6d - Italy-Spain cross-border dossier.

## Rischi, esclusioni e blocker

- Possibile blocker: dati patrimoniali esteri incompleti o classificazione dell'intermediario non documentata.
- Fuori perimetro iniziale: dichiarazione completa, ottimizzazione fiscale, Paesi diversi da Italia/Spagna, strumenti non classificabili.

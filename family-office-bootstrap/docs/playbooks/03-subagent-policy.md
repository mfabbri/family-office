# Subagent policy

I subagent sono un acceleratore selettivo, non il default.

## Default

- Il main agent implementa e testa.
- `fo_explorer` (Luna/low) solo per discovery bounded che evita letture estese del main.
- `fo_planner` (Terra/medium) solo per cambi cross-module con output di piano compatto.
- `fo_reviewer` (Terra/high) per review tecnica indipendente T3-T5.
- `fo_financial_reviewer` (Sol/high) per formule, cash-flow, leverage, stress test e opportunity cost.
- `fo_normative_reviewer` (Sol/high) per fiscalita', previdenza, compliance e validita' temporale.

## Vincoli

- Massimo 2 subagent concorrenti.
- Profondita' pratica: un solo livello di delega.
- Nessun subagent se il task e' risolvibile con una singola lettura e un singolo test.
- Non invocare reviewer finanziario e normativo sullo stesso cambiamento salvo che contenga entrambe le semantiche.
- Non delegare la stessa domanda a due modelli per "votazione".
- I subagent devono restituire sintesi e riferimenti, non raw logs.
- Il main non deve rileggere integralmente i file gia' sintetizzati da un explorer affidabile salvo incongruenze.

## Quando parallelizzare

Solo se i workstream sono indipendenti, ad esempio:

- explorer: individua servizi/contratti riutilizzabili;
- normative reviewer: verifica solo il perimetro fiscale di una nuova activity classification.

Non parallelizzare implementazione e review dello stesso file prima che l'implementazione sia stabile.

## Token hygiene

`interrupt_message = false` e' configurato per non aggiungere al contesto del modello messaggi di interruzione non necessari. Le risposte dei subagent devono essere brevi e strutturate per poter essere incorporate senza riaprire il corpus.

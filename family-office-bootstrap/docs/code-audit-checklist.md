# Code Audit Checklist

Questo audit e' un micro-incremento ricorrente. Deve essere eseguito almeno ogni 4 incrementi funzionali completati, prima di continuare con il successivo incremento di prodotto.

## Ambito

L'audit deve controllare i repository modificati dagli ultimi incrementi, con priorita' a:

- `family-office-engine/src/`
- `family-office-engine/tests/`
- `family-office-engine/schemas/`
- `family-office-engine/docs/`
- `family-office-rules/`
- template e guide in `family-office-workspace/household/`

Non copiare dati personali fuori dal workspace e non usare dati reali nei test dei repository software.

## Checklist

- Responsabilita' dei moduli: ogni servizio deve avere un confine chiaro e non accoppiare parser, regole, CLI e reporting oltre il necessario.
- Contratti: schema, fixture, builder, CLI, API docs e test devono descrivere lo stesso record type e la stessa versione.
- Test: ogni funzione pubblica nuova deve avere test mirati; ogni CLI nuova deve avere almeno un test di successo e test dei casi limite nel servizio.
- Regression: eseguire la suite completa dell'engine e registrare il risultato in `current-next-increment.md`.
- Error handling: errori utente e input non validi devono usare eccezioni tipizzate e messaggi CLI coerenti.
- Data gaps: dati mancanti o incerti devono diventare gap espliciti, non default silenziosi o stime implicite.
- Privacy: nessun dato personale reale in engine, rules, knowledge, bootstrap, fixture o documentazione pubblicabile.
- Dipendenze: nuove dipendenze devono essere dichiarate in `pyproject.toml` e verificate con l'interprete del venv del repository.
- Duplicazione: identificare helper duplicati o pattern divergenti tra servizi; trasformare in incremento futuro solo se il refactor e' piccolo e verificabile.
- Complessita': segnalare file, funzioni o CLI troppo grandi; non fare refactor ampi dentro l'audit se non sono necessari per correggere un bug.
- Compatibilita': path e comandi devono restare usabili su Windows e Linux.
- Roadmap: eventuali debiti trovati devono diventare `blocked`, `deferred` o nuovi micro-incrementi espliciti.

## Output dell'audit

Aggiornare:

- `family-office-engine/docs/current-next-increment.md` con ambito, controlli eseguiti, risultati e follow-up.
- `family-office-engine/docs/decision-log.md` se l'audit introduce una decisione di architettura, governance o debito tecnico.
- roadmap attiva, marcando l'audit `done` solo dopo avere registrato eventuali follow-up.

## Cadenza

La cadenza si conta sugli incrementi funzionali completati, escludendo audit, patch puramente documentali e micro-incrementi creati solo per aggiornare la governance. Dopo 4 incrementi funzionali senza audit, il prossimo incremento selezionabile deve essere un audit prima di proseguire.

# Developer Playbook

## 00 — Start Session

Verificare il layout dei repository e leggere AGENTS, roadmap index, roadmap attiva, current-next-increment e decision log. Non scrivere codice prima di avere salvato il piano dell'incremento.

Se l'utente chiede di procedere automaticamente, usare `docs/next-increment-developer-plan.md` e la politica in `roadmap-index.md`.

## 01 — Analyze

Classificare il cambiamento: contratto, codice, regola, conoscenza, dato, sicurezza o operazione. Identificare repository, dipendenze, periodo normativo e dati necessari.

## 02 — Design

Definire il micro-incremento minimo, input/output, schema version, provenance, errori, data gaps e test. Creare ADR se cambia architettura o responsabilità tra repository.

## 03 — Implement

Implementare una sola capacità osservabile. Evitare refactor non richiesti e non accoppiare parser, regole e UI nello stesso incremento.

Se l'incremento richiede moduli Python esterni, dichiararli prima in `family-office-engine/pyproject.toml`, installare o sincronizzare il venv del repository con `python -m pip install -e .`, e usare l'interprete del venv per CLI e test. Non affidarsi al Python globale per verificare disponibilità di parser o dipendenze.

## 04 — Test

Ordine preferito:

1. schema e unit;
2. integration fra repository;
3. fixture sintetiche/golden dataset;
4. regression;
5. prova sul workspace reale senza copiarne i dati nel repository.

I risultati devono essere riproducibili e compatibili con Windows e Linux.

## 05 — Documentation

Aggiornare nello stesso cambiamento:

- contratto o API;
- current-next-increment;
- stato nella roadmap;
- decision log;
- testing/CLI quando impattati.

## 06 — Review

Verificare privacy, sicurezza, titolarità, provenance, validità temporale, assenza di dati personali nel codice e separazione fra facts, assunzioni, stime e raccomandazioni.

## 06a — Code Audit

Eseguire un audit tecnico del codice almeno ogni 4 incrementi funzionali completati. Usare `docs/code-audit-checklist.md`.

L'audit deve verificare responsabilità dei moduli, allineamento tra contratti/schema/builder/CLI/docs/test, copertura dei casi limite, error handling, data gaps, privacy, dipendenze, duplicazioni, complessità e compatibilità multipiattaforma.

Se l'audit trova debiti o rischi non correggibili nello stesso micro-incremento, registrarli come follow-up espliciti nella roadmap o nel decision log. Non continuare con il quinto incremento funzionale consecutivo senza avere completato o esplicitamente bloccato l'audit.

## 07 — Release

Preparare changelog, versioni schema/regole, milestone, snapshot riproducibile e rollback. Non rilasciare modifiche normative o AI senza regression suite pertinente.

## 08 — Knowledge Update

Per norme o interpretazioni nuove: Knowledge → Rules → Tests → Engine. Ogni regola deve avere fonte, giurisdizione e periodo di validità.

## 09 — Roadmap Gate

Al termine di una roadmap verificare gli exit criteria e il gate indicato in `roadmap-index.md`. I gap residui devono essere `blocked`, `deferred` o trasformati in incrementi espliciti; non devono restare impliciti.

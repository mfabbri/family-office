# Developer Playbook

## Start

Leggere `../AGENTS.md` e `playbooks/00-task-router.md`. Classificare il task, applicare il budget di contesto e scegliere il tier modello prima di esplorare.

## Analyze and design

Identificare output, owner della semantica, contratti, dati, validità temporale e test. Per T0/T1 non creare piani o ADR non necessari. Per T2–T5 usare il playbook specifico.

## Implement

Fare una sola modifica osservabile, evitare refactor non richiesti e separare parser, regole, servizi e reporting. Dichiarare le dipendenze in `pyproject.toml` e verificare con l'interprete del repository.

## Test

Seguire `playbooks/08-testing-and-review.md`: test mirati durante il lavoro, regression completa al gate appropriato.

## Document

Aggiornare contratti e stato solo quando impattati. Non aggiornare decision log, long-term roadmap o tutte le roadmap per default.

## Review

Controllare privacy, sicurezza, provenance, periodo normativo e separazione tra facts, assunzioni, stime e raccomandazioni.

## Model and agents

Seguire `playbooks/02-model-routing.md` e `playbooks/03-subagent-policy.md`. Il default è single-agent standard/medium; aumentare complessità solo per trigger espliciti.

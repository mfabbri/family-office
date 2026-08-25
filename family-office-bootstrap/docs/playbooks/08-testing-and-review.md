# Testing and Review

## Test ladder

1. test mirato del comportamento modificato;
2. test del modulo/package;
3. integration sui confini interessati;
4. golden/regression per calcoli o contratti;
5. suite completa al gate di incremento o release.

Non eseguire ripetutamente l'intera suite durante modifiche locali se i test mirati forniscono feedback sufficiente.

## Review proportionality

- T0–T1: self-review e test mirati.
- T2: self-review strutturata + regression pertinente.
- T3: review high-effort, eventualmente subagent read-only.
- T4–T5: review indipendente, fonti/assunzioni e scenari avversi.

## CLI UX checks

Quando cambia un comando CLI o un wizard, verificare almeno:

- comando corto `fo ...` o wrapper locale documentato;
- errore recuperabile con prossimo comando esplicito;
- output riepilogativo leggibile senza aprire JSON;
- wizard con default da workspace/snapshot quando disponibili;
- salvataggio progressivo e ripresa con `--overwrite`;
- valori incerti registrati come `data_gaps`.

## Smoke CLI riproducibile

Verificare il comando utente `fo ...` oltre al fallback tecnico `python -m family_office_engine.cli.main ...`. Su Windows, se `fo` non e' nel `PATH` della shell, invocare esplicitamente l'eseguibile del virtual environment del repository, ad esempio `./.venv/Scripts/fo.exe ...`; non considerare il fallback tecnico un sostituto dello smoke del comando utente.

## Completion report

Riportare soltanto:

- file modificati;
- comportamento ottenuto;
- test eseguiti e risultato;
- rischi/gap residui;
- stato roadmap, se applicabile.

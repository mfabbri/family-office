# V6 Roadmap — Operations, Security and Compliance

## Obiettivo

Rendere il family office un sistema mantenibile nel tempo: aggiornamenti documentali, monitoraggio, sicurezza, audit, normativa, backup, release e revisione periodica.

## Prerequisiti

- Gate V5 completato per le funzioni AI.
- I requisiti di privacy e sicurezza restano comunque trasversali e possono essere anticipati come incrementi abilitanti.

## Incrementi

### V6.1 — Pipeline refresh orchestrator

**Stato:** `planned`

Creare un comando unico che rilevi input cambiati, esegua solo gli step necessari e produca un run manifest.

- Repository: `engine`, `workspace`.
- Output: `fo pipeline refresh`, DAG degli step e `pipeline-run/v1`.
- Test: run completo, incrementale, errore parziale, idempotenza.
- Done quando: gli snapshot non devono essere rigenerati manualmente in ordine.

### V6.2 — Lineage, hashes and freshness

**Stato:** `planned`

Aggiungere hash input, versione parser/regola, timestamp, path relativi e policy di scadenza a snapshot e report.

- Dipende da: V6.1.
- Repository: `engine`, `workspace`.
- Output: `artifact-lineage/v1` e freshness checker.
- Test: documento cambiato, rule pack aggiornato, snapshot obsoleto, path multipiattaforma.
- Done quando: ogni risultato dichiara se è aggiornato e da quali input deriva.

### V6.3 — Document intake and data-quality monitoring

**Stato:** `planned`

Controllare nuovi documenti, duplicati, periodi mancanti, variazioni anomale e riconciliazione degli asset.

- Dipende da: V6.2.
- Repository: `engine`, `workspace`.
- Output: `data-quality-report/v1` e code di remediation.
- Test: duplicati, gap mensili, totale incoerente e documento non classificato.
- Done quando: una decisione non usa silenziosamente dati vecchi o incompleti.

### V6.4 — Compliance calendar and alerts

**Stato:** `planned`

Gestire scadenze fiscali, documentali, previdenziali, polizze, rinnovi, review e trigger familiari.

- Dipende da: V3.4 e V6.2.
- Repository: `knowledge`, `rules`, `engine`, `workspace`.
- Output: `compliance-calendar/v1` e alert locali.
- Test: ricorrenze, scadenze mobili, alert duplicati e timezone.
- Done quando: ogni alert mostra fonte, responsabilità e azione richiesta.

### V6.5 — Regulatory update workflow

**Stato:** `planned`

Rilevare e valutare cambi normativi seguendo Knowledge → Rules → Tests → Engine, con validità temporale e approvazione.

- Repository: `bootstrap`, `knowledge`, `rules`, `engine`.
- Output: change proposal, impact assessment e release checklist normativa.
- Test: nuova aliquota, norma retroattiva, fonte non autorevole e rollback.
- Done quando: una regola non può cambiare senza fonte, test e periodo di validità.

### V6.6 — Secrets, encryption and access control

**Stato:** `planned`

Proteggere workspace, token, backup e dati identificativi con cifratura, secret store e least privilege.

- Repository: `bootstrap`, `engine`, `workspace`.
- Output: threat model, configurazione locale e security checks.
- Test: segreto nel repository, permessi eccessivi, file non cifrato e log sensibile.
- Done quando: nessun segreto o documento personale entra in pacchetti software o log diagnostici.

### V6.7 — Sanitized export and packaging

**Stato:** `planned`

Creare export allowlist per codice, roadmap e report, con redazione dei dati personali e manifest dei file.

- Dipende da: V6.6.
- Repository: `bootstrap`, `engine`.
- Output: `fo export sanitized` e policy di packaging.
- Test: `.venv`, `.history`, backup, snapshot e PDF personali esclusi.
- Done quando: uno ZIP condivisibile non può contenere dati privati per default.

### V6.8 — Backup, restore and disaster recovery

**Stato:** `planned`

Definire backup cifrati, retention, verifica integrità, restore selettivo e recovery drill.

- Dipende da: V6.6.
- Repository: `bootstrap`, `workspace`.
- Output: runbook e manifest backup.
- Test: restore su directory vuota, backup corrotto, chiave mancante e versioni.
- Done quando: il workspace può essere ricostruito con una prova documentata.

### V6.9 — Audit trail and approvals

**Stato:** `planned`

Registrare chi o cosa ha importato dati, modificato assunzioni, approvato scenari e generato raccomandazioni.

- Dipende da: V6.1 e V5.10.
- Repository: `engine`, `workspace`.
- Output: append-only `audit-event/v1` e approval workflow.
- Test: modifica, revoca, replay, clock skew e tamper detection.
- Done quando: ogni raccomandazione ad alto impatto ha una catena di approvazione ricostruibile.

### V6.10 — Regression, release and model governance

**Stato:** `planned`

Unificare test unitari, golden data, scenari, regole, AI evaluations e migrazioni in gate di release.

- Dipende da: V5.11 e V6.5.
- Repository: tutti tranne workspace reale.
- Output: release pipeline, version matrix e rollback plan.
- Test: release candidata, regressione fiscale, modello AI diverso e schema incompatibile.
- Done quando: ogni release ha evidenze, versioni e criteri di rollback.

### V6.11 — Annual review and contingency plan

**Stato:** `planned`

Produrre una review annuale con KPI, eventi, cambi normativi, scostamenti, rischi e piano di aggiornamento.

- Dipende da: V6.3–V6.10.
- Repository: `engine`, `workspace`.
- Output: `annual-review/v1`, KPI e contingency actions.
- Test: anno incompleto, dati obsoleti, cambio residenza e evento straordinario.
- Done quando: il sistema indica cosa riesaminare, perché e con quale priorità.

## Exit criteria V6

- Pipeline e aggiornamenti sono incrementali, tracciati e riproducibili.
- Dati privati, segreti, backup ed export hanno policy verificabili.
- Normativa e modelli AI sono soggetti a governance e regression test.
- Alert e review hanno owner, fonte e azione.
- Il sistema è recuperabile e auditabile senza dipendere dalla memoria dell'operatore.

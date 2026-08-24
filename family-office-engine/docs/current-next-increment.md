# Current Next Increment

## ID e titolo

V5.3b - Periodic code and contract audit.

## Stato

`planned`

## Roadmap

`docs/roadmap/roadmap-v5-ai-orchestration.md`

## Motivazione e dipendenze

V5.3a e' completato. Con V5.1, V5.2, V5.3 e V5.3a risultano quattro incrementi funzionali completati dall'ultimo audit: la cadenza impone V5.3b prima di qualsiasi ulteriore incremento funzionale.

Dipendenze: V5.3 e V5.3a sono `done`. L'audit deve verificare confini, contratti, formule comuni, provenance, data gaps, separazione personal use e regression prima degli adapter asset-specific.

Prima dell'implementazione eseguire sempre:

```text
python family-office-engine/src/family_office_engine/governance/roadmap_audit.py
```

## Piano operativo V5.3b

1. Applicare la checklist `family-office-bootstrap/docs/code-audit-checklist.md` ai contratti V5.1-V5.3a e ai confini repository coinvolti.
2. Verificare allineamento tra schema, core, CLI, fixture, test e documentazione di `investment-opportunity/v1`.
3. Verificare privacy, provenance, data gaps, separazione personal use, error handling, duplicazioni e dipendenze.
4. Eseguire regression e `roadmap_audit.py`; documentare follow-up o blocker espliciti.

## Criteri di completamento V5.3b

- checklist applicata e confini verificati;
- nessun blocker implicito prima degli adapter asset-specific;
- regression e audit verdi;
- follow-up o debiti tecnici documentati esplicitamente.

## Cadenza audit

Il contatore e' `functional_since_audit=4`. V5.3b e' l'audit obbligatorio e deve essere completato prima di V5.3c.

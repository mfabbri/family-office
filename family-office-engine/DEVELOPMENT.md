# Development

Installazione prevista: Python 3.11+.

## CLI

La CLI primaria e' `fo`, esposta da `pyproject.toml`:

```powershell
cd family-office-engine
.\.venv\Scripts\python -m pip install -e .
```

Dopo l'installazione editable:

```powershell
fo validate
fo planning goals wizard
fo planning liquidity wizard
```

Dalla root del progetto sono disponibili anche wrapper locali:

```powershell
.\fo.ps1 validate
.\fo.ps1 planning goals wizard
```

Per usare `fo` senza prefisso `.\`, dot-sourcare lo script di sessione dalla root:

```powershell
. .\use-family-office.ps1
fo validate
```

I comandi `python -m family_office_engine.cli.main ...` restano fallback tecnico per sviluppo e test, non l'interfaccia utente principale.

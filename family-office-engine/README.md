# Family Office Engine

## CLI

L'interfaccia utente primaria e' il comando corto `fo`.

Setup locale consigliato:

```powershell
cd family-office-engine
.\.venv\Scripts\python -m pip install -e .
fo validate
```

Dalla root del progetto puoi usare anche i wrapper locali senza digitare il modulo Python:

```powershell
.\fo.ps1 validate
.\fo.ps1 planning goals wizard
```

Per usare `fo` senza prefisso `.\`, prepara la sessione PowerShell dalla root:

```powershell
. .\use-family-office.ps1
fo validate
```

Software riutilizzabile per ingestion documentale, grafo patrimoniale, simulazioni, report e CLI.

Non contiene dati personali né regole normative hardcoded oltre ai contratti tecnici di esecuzione.

# Codex — Family Office AI routing 4.0

## Prima esecuzione

1. Controllare `codex --version`; per Astra la documentazione OpenAI richiede CLI almeno 0.153.0, ma usare una versione aggiornata per i modelli GPT-6.2. Il model picker Work/Codex non prova la disponibilita' dello stesso slug nel CLI locale.
2. Controllare che `gpt-6-luna`, `gpt-6.1-terra`, `gpt-6.2-sol` e `gpt-6.2-astra` siano effettivamente disponibili nel client scelto. Se non lo sono, **non** riprovare automaticamente; mantenere backup e registrare il fallback nel planner prima di cambiare configurazione.
3. Validare offline: `python family-office-bootstrap/planning/validate-codex-model-routing.py`.
4. Review hook tramite `/hooks` dopo modifica degli hook; questa patch non modifica hook o permessi.

## Principi

Parent Luna/low fa triage; subagent solo se migliorano l'esito. Implementer Sol/medium, reviewer tecnico indipendente Sol/medium, source review Sol/high, Astra solo su questioni sostanziali definite. Vedi `family-office-bootstrap/docs/playbooks/02-model-routing.md` per matrice completa.

L'utente controlla l'accesso reale ai modelli. Le condizioni Work/Codex e i prezzi API **non** sono intercambiabili. Non preassegnare costi monetari a token senza piano e listino aggiornato.

## Uso e telemetria

Gli hook locali registrano solo model/agent/event. Per analizzare un'esecuzione non interattiva con output JSONL **gia' disponibile** (non lancia nuovi agent):

```powershell
python .amily-office-bootstrap\planningeport-token-usage.py .un-codex.ndjson
```

Il report legge `turn.completed.usage`, mostra somme dei token, ma non legge/scrive prompt. Non interpretarlo come fattura API o quota residua Work. Per quest'ultima: Settings > Usage.

## Retrocompatibilita'

L'incremento V4.14 bloccato nel planner resta con routing v3.1 come documento storico; al prossimo ciclo **autorizzato**, passare a 4.0 mantenendo la trace precedente nel decision log. Il validator consente questo storico solo se lo stato e' `blocked`. Nessun cambiamento alla semantica dei gate.

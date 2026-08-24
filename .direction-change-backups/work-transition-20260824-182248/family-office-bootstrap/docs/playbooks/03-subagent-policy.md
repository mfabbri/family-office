# Subagent Policy

Il default è single-agent. Ogni subagent esegue chiamate e tool propri e quindi aumenta token, latenza e coordinamento.

## Consentito

Usare subagent quando il lavoro è:

- indipendente e parallelizzabile;
- prevalentemente read-only;
- delimitato da input/output chiari;
- sintetizzabile in un risultato breve;
- utile a isolare log, scansioni o review dal contesto principale.

Esempi: mappatura di un flusso, audit di test, verifica documentale, review indipendente di una patch T3–T5.

## Da evitare

- un agente per ogni fase standard;
- più agenti che modificano gli stessi file;
- delegazione per task T0/T1;
- catene ricorsive di agenti;
- subagent che restituiscono log grezzi o copie di file.

## Limiti del progetto

- `agents.max_depth = 1`;
- `agents.max_threads = 3`;
- massimo 2 subagent per task, salvo richiesta esplicita;
- preferire subagent read-only;
- il main agent resta responsabile di decisione, integrazione e test finali.

## Contratto di ritorno

Ogni subagent deve restituire:

1. conclusione;
2. evidenze con file/simboli;
3. rischi o gap;
4. massimo 5 azioni raccomandate;
5. nessun log completo salvo richiesta.

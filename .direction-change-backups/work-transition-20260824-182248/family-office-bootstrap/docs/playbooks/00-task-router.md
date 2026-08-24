# Task Router

Classificare il task prima di esplorare il repository.

| Classe | Caratteristiche | Esempi | Playbook | Tier iniziale |
|---|---|---|---|---|
| T0 | Meccanico, nessuna semantica | typo, rename, formatting | context + review | economy/low |
| T1 | Circoscritto a un modulo | bug semplice, test, parser locale | `05-bug-fix` | economy o standard/low-medium |
| T2 | Nuova capacità delimitata | CLI, servizio, contratto singolo | `04-micro-increment` | standard/medium |
| T3 | Cross-module o cross-repository | schema condiviso, ownership, integrazione | `06-cross-repository-change` | advanced/high |
| T4 | Normativo o finanziario critico | fiscalità, pensione, RW, simulazione | `07-normative-change` | critical/high-xhigh |
| T5 | Architetturale o esplorativo | nuova roadmap, orchestrazione AI | piano dedicato | critical/high-xhigh |

## Procedura

1. Identificare output richiesto e criteri di completamento.
2. Assegnare una sola classe primaria; usare la più alta se il task attraversa più classi.
3. Applicare `01-context-budget.md`.
4. Scegliere modello/effort con `02-model-routing.md`.
5. Aprire il playbook specifico.
6. Aumentare classe o contesto solo quando emerge un trigger documentato.

## Trigger di escalation

Escalare quando emerge almeno uno dei seguenti elementi:

- modifica di schema o contratto condiviso;
- impatto su più repository;
- dati mancanti con conseguenze finanziarie;
- interpretazione normativa o validità temporale;
- cambio di ownership, sicurezza o privacy;
- test contraddittori o comportamento non riproducibile;
- più di due ipotesi architetturali plausibili.

Non escalare solo perché il repository è grande.

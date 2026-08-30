# Task Router

Classificare il task prima di esplorare il repository. La classe T0–T5 governa rischio e playbook; il model router seleziona poi l'agent effettivo per la fase corrente.

| Classe | Caratteristiche | Esempi | Playbook | Route tipica |
|---|---|---|---|---|
| T0 | Meccanico, nessuna semantica | typo, rename, formatting | context + review | Luna low/medium |
| T1 | Circoscritto a un modulo | bug semplice, test, parser locale | `05-bug-fix` | Terra/medium se scrive runtime |
| T2 | Nuova capacità delimitata | CLI, servizio, contratto singolo | `04-micro-increment` | Terra/medium |
| T3 | Cross-module o cross-repository | schema condiviso, ownership, integrazione | `06-cross-repository-change` | Terra/medium + review; Sol/high se emerge un trade-off architetturale |
| T4 | Normativo o finanziario critico | fiscalità, pensione, RW, investimenti, leverage, IRR/NPV | `07-normative-change` o `11-investment-opportunity` | Sol/high financial review oppure Sol/xhigh normative review; Terra per implementazione deterministica |
| T5 | Architetturale o esplorativo | nuova roadmap, orchestrazione AI, migrazione | piano dedicato | Sol/high |

## Procedura

1. Identificare goal, output, vincoli e done-when.
2. Assegnare una sola classe primaria; usare la più alta se il task attraversa più classi.
3. Applicare `01-context-budget.md`.
4. Creare/aggiornare il task envelope in `../../planning/current-work.json`.
5. Scegliere agent/modello con `02-model-routing.md` e `$family-office-model-router`.
6. Registrare il routing prima della delega.
7. Aprire un solo playbook specifico, più testing/review se necessario.
8. Aumentare classe, contesto, reasoning o modello solo quando emerge un trigger documentato.

## Investment opportunity routing

Usare `11-investment-opportunity.md` quando il task riguarda acquisto, gestione, finanziamento, noleggio, cash flow o confronto di asset produttivi, inclusi immobili, camper/veicoli, box, barche, fotovoltaico o piccole attività.

- Analisi economica senza nuove regole fiscali: T4 finanziario → `fo_financial_reviewer` per il gate finanziario.
- Nuova classificazione fiscale/legale: T4 normativo + `07-normative-change` → `fo_normative_reviewer`.
- Solo integrazione UI/CLI di una capability esistente: T2/T3.
- Nuova famiglia di asset ma contratto generico già stabile: T2/T3, non T5.

## Trigger di escalation

Escalare quando emerge almeno uno dei seguenti elementi:

- modifica di schema o contratto condiviso;
- impatto su più repository;
- dati mancanti con conseguenze finanziarie;
- interpretazione normativa o validità temporale;
- cambio di ownership, sicurezza o privacy;
- test contraddittori o comportamento non riproducibile;
- più di due ipotesi architetturali plausibili;
- separazione non chiara tra rendimento finanziario e beneficio d'uso personale;
- leva finanziaria o fiscalità che cambia il ranking dell'investimento.

Non escalare solo perché il repository è grande.

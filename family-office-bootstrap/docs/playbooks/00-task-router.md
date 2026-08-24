# Task Router

Classificare il task prima di esplorare il repository.

| Classe | Caratteristiche | Esempi | Playbook | Tier iniziale |
|---|---|---|---|---|
| T0 | Meccanico, nessuna semantica | typo, rename, formatting | context + review | Luna/low |
| T1 | Circoscritto a un modulo | bug semplice, test, parser locale | `05-bug-fix` | Terra/low-medium |
| T2 | Nuova capacita' delimitata | CLI, servizio, contratto singolo | `04-micro-increment` | Terra/medium |
| T3 | Cross-module o cross-repository | schema condiviso, ownership, integrazione | `06-cross-repository-change` | Terra/medium-high |
| T4 | Normativo o finanziario critico | fiscalita', pensione, RW, investimenti, leverage, IRR/NPV | `07-normative-change` o `11-investment-opportunity` | Terra/medium + reviewer Sol/high |
| T5 | Architetturale o esplorativo | nuova roadmap, orchestrazione AI | piano dedicato | Terra/high; Sol solo review critica |

## Procedura

1. Identificare goal, output, vincoli e done-when.
2. Assegnare una sola classe primaria; usare la piu' alta se il task attraversa piu' classi.
3. Applicare `01-context-budget.md`.
4. Scegliere modello/effort con `02-model-routing.md`.
5. Aprire un solo playbook specifico, piu' testing/review se necessario.
6. Aumentare classe, contesto o reasoning solo quando emerge un trigger documentato.

## Investment opportunity routing

Usare `11-investment-opportunity.md` quando il task riguarda acquisto, gestione, finanziamento, noleggio, cash flow o confronto di asset produttivi, inclusi immobili, camper/veicoli, box, barche, fotovoltaico o piccole attivita'.

- Analisi economica senza nuove regole fiscali: T4 finanziario.
- Nuova classificazione fiscale/legale: T4 normativo + `07-normative-change`.
- Solo integrazione UI/CLI di una capability esistente: T2/T3.
- Nuova famiglia di asset ma contratto generico gia' stabile: T2/T3, non T5.

## Trigger di escalation

Escalare quando emerge almeno uno dei seguenti elementi:

- modifica di schema o contratto condiviso;
- impatto su piu' repository;
- dati mancanti con conseguenze finanziarie;
- interpretazione normativa o validita' temporale;
- cambio di ownership, sicurezza o privacy;
- test contraddittori o comportamento non riproducibile;
- piu' di due ipotesi architetturali plausibili;
- separazione non chiara tra rendimento finanziario e beneficio d'uso personale;
- leva finanziaria o fiscalita' che cambia il ranking dell'investimento.

Non escalare solo perche' il repository e' grande.

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

## Roadmap eligibility

`roadmap_audit.py` verifica la cadenza di audit e la coerenza strutturale, ma non certifica che tutti i predecessori siano `done`. Prima di selezionare **e prima di chiudere** un incremento, enumerare gli incrementi precedenti della roadmap attiva e le dipendenze dichiarate, quindi confrontare il loro stato con roadmap, `current-next-increment.md` e planner. Se questi puntano a valle di un predecessore incompleto, riallinearli al predecessore piu' antico; la separabilita' tecnica non costituisce un'eccezione.

Un GO locale chiude solo lo scope esaminato. Non usare il GO di un figlio o slice limitato per chiudere/sbloccare un parent. Dopo ogni verdetto ripetere il controllo della sequenza prima del passo seguente.

Per selezionare un suffisso di remediation, verificare che risolva il blocker del parent più antico e registrare la dipendenza esplicita. Se roadmap e decision log documentano un gate NO-GO ma lo stato del parent è ancora `in_progress`, riallineare lo stato a `blocked` nello stesso aggiornamento solo quando l'evidenza lo giustifica; non cambiare stato solo per far passare il validator. I validator strutturali non sostituiscono il controllo manuale dei predecessori.

## Ambiente Windows e integrità dei file

- Eseguire i test e i validator con il Python del repository (`family-office-engine/.venv/Scripts/python.exe`), così dipendenze e risultati sono riproducibili.
- Se PowerShell o il sandbox negano ACL sui temporanei, leggere l'errore completo e distinguere il problema d'ambiente da un failure applicativo. Per la suite obbligatoria usare il percorso di escalation previsto; non cambiare il test o la sua directory temporanea per ottenere un falso pass.
- Per modificare Markdown con accenti o caratteri non ASCII, preferire patch puntuali o scrittura con encoding UTF-8 esplicito. Evitare riscritture PowerShell dell'intero file senza encoding dichiarato; controllare il diff per `?` sostitutivi, BOM o righe alterate.
- Non ripulire directory temporanee o file untracked preesistenti. Eliminare soltanto un temporaneo creato dal task corrente dopo averne verificato il percorso assoluto dentro il workspace.

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

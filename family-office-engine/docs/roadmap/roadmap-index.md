# Roadmap Index and Selection Policy

Questo documento è il punto di ingresso unico per la pianificazione del progetto. Gli agenti devono usarlo insieme a `current-next-increment.md` per scegliere il prossimo micro-incremento senza richiedere una decisione manuale.

## Ordine delle roadmap

| Ordine | Roadmap | Obiettivo | Stato |
|---:|---|---|---|
| 0 | `roadmap-mvp.md` | Ingestion, patrimonio e simulazione iniziale | `done` |
| 1 | `roadmap-v1.md` | Parser documentali V1 | `done_with_gaps` |
| 2 | `roadmap-v2.md` | Cashflow, fiscalità, RITA e successione V1 | `done` |
| 3 | `roadmap-v3-decision-core.md` | Modello decisionale spiegabile | `done` |
| 4 | `roadmap-v4-wealth-planning.md` | Pianificazione patrimoniale multi-obiettivo | `in_progress` |
| 5 | `roadmap-v5-ai-orchestration.md` | Orchestrazione AI sopra strumenti deterministici | `planned` |
| 6 | `roadmap-v6-operations-compliance.md` | Esercizio continuo, sicurezza e compliance | `planned` |

La roadmap V3 e' `done`: V3.10b-V3.10d collegano scenario, outcome deterministici, sensitivity, scoring e dossier con lineage verificabile. La roadmap V4 e' `in_progress`: V4.1, V4.2, V4.2a, V4.3, V4.3a, V4.3b, V4.4, V4.5, V4.6a, V4.6b, V4.6c, V4.6d, V4.6e, V4.6f, V4.6g, V4.7 e V4.8 sono completati. V4.9 e' il prossimo incremento pianificato.

`done_with_gaps` indica che la capability è disponibile ma alcuni formati o fonti reali restano da aggiungere tramite incrementi mirati. Non blocca la roadmap successiva se i gap non sono prerequisiti dell'incremento selezionato.

## Stati ammessi per gli incrementi

- `planned`: definito e non iniziato;
- `in_progress`: incremento attivo riportato anche in `current-next-increment.md`;
- `done`: implementato, testato e documentato;
- `blocked`: non eseguibile finché non viene rimosso un impedimento esplicito;
- `deferred`: rinviato con motivazione registrata nel decision log.

Lo stato non deve essere dedotto dai commit o dal codice: deve essere scritto nella roadmap.

Ogni incremento deve inoltre dichiarare `**Tipo:**` con uno dei valori:

- `functional`: introduce o modifica una capability di prodotto e conta nella cadenza audit;
- `audit`: verifica periodica e azzera la cadenza quando passa a `done`;
- `governance`: modifica soltanto policy o automazioni di governo;
- `docs`: modifica soltanto documentazione o guide.

## Algoritmo di selezione

1. Leggere `family-office-engine/docs/current-next-increment.md`.
2. Eseguire `python family-office-engine/src/family_office_engine/governance/roadmap_audit.py` dalla root del progetto. Un errore blocca la selezione di un incremento funzionale.
3. Se contiene uno stato `planned` o `in_progress`, continuare quell'incremento.
4. Se lo stato è `blocked`, creare come incremento corrente il più piccolo lavoro necessario a rimuovere il blocco. Non saltare a una roadmap successiva.
5. Se l'incremento corrente è `done`, aprire la prima roadmap non completata nell'ordine della tabella.
6. Prima di selezionare il prossimo incremento funzionale, verificare la cadenza di code audit: dopo 4 incrementi funzionali completati senza audit, selezionare il micro-incremento di audit nella roadmap attiva. Se manca, crearlo con suffisso alfabetico senza rinumerare gli incrementi già tracciati.
7. Selezionare il primo incremento con stato `planned` le cui dipendenze risultano `done` o `deferred` con motivazione compatibile.
8. Salvare il piano concreto in `current-next-increment.md` prima di modificare codice, regole, knowledge o workspace.
9. Al completamento, aggiornare nello stesso cambiamento:
   - stato dell'incremento nella roadmap;
   - `current-next-increment.md`;
   - test e contratti impattati;
   - `decision-log.md`.

## Regola per i blocchi

Quando un incremento dipende da documenti personali mancanti, normativa non consolidata o un contratto non definito, l'agente deve creare un micro-incremento abilitante nella stessa roadmap. Esempi:

- fixture sintetica e contratto prima del parser reale;
- knowledge note e rule pack prima del calcolo fiscale;
- contratto e riconciliazione delle basi contributive prima della stima della pensione spagnola;
- migrazione dello snapshot prima dell'uso in una simulazione;
- data-quality check prima di una raccomandazione.

Un incremento abilitante deve essere aggiunto con suffisso alfabetico, ad esempio `V3.5a`, senza rinumerare gli incrementi già tracciati.

## Cadenza code audit

Ogni 4 incrementi funzionali completati deve essere eseguito un micro-incremento di code audit prima di procedere con il quinto incremento funzionale. Gli audit non contano nel gruppo dei 4.

L'audit usa `family-office-bootstrap/docs/code-audit-checklist.md` e deve almeno verificare:

- confini dei moduli e responsabilità;
- allineamento tra schema, builder, CLI, fixture, test e documentazione;
- copertura dei casi limite e regression suite;
- privacy e assenza di dati personali nei repository software;
- data gaps, error handling, dipendenze e duplicazioni;
- follow-up espliciti per debiti tecnici non corretti nello stesso audit.

## Gate tra roadmap

### Gate V2 → V3

- cashflow derivato dai documenti disponibile o gap esplicitamente bloccante;
- rule engine V1 versionato e invocabile;
- RITA e successione V1 producono output spiegabili, anche se parziali;
- snapshot con provenance e contratti stabili.

### Gate V3 → V4

- household graph, ownership, timeline e liquidità modellati;
- pension income e spese lifecycle integrati;
- carriera spagnola normalizzata da Vida Laboral e basi contributive; pensione spagnola stimata con regole versionate oppure bloccata esplicitamente per input insufficienti;
- coordinamento UE Italia–Spagna separa diritti nazionali, totalizzazione e quote pro-rata senza fondere i contributi;
- scenari, stress test e ranking multi-obiettivo riproducibili;
- ogni raccomandazione è riconducibile a facts, regole e simulazioni.

### Gate V4 → V5

- le principali decisioni patrimoniali sono esposte come tool deterministici;
- gli output includono fonti, ipotesi, limiti e confidence;
- esiste una suite di casi sintetici e golden scenarios;
- nessun calcolo fiscale o finanziario richiede un LLM.

### Gate V5 → V6

- router, planner ed executor AI usano esclusivamente tool registrati;
- le risposte citano evidenze e distinguono facts, assunzioni e raccomandazioni;
- esiste una evaluation suite contro hallucination, tool misuse e risposte non supportate.

## Requisiti trasversali

Questi requisiti valgono in tutte le roadmap e possono generare incrementi abilitanti anticipati:

- nessun dato personale nei repository software, rules o knowledge;
- niente LLM per calcoli fiscali, previdenziali o finanziari;
- provenance, versionamento e data gaps obbligatori;
- compatibilità multipiattaforma dei path;
- CLI semplice da usare: ogni capability utente deve preferire comandi corti con default del workspace, demo/smoke senza path JSON lunghi e help chiaro prima di richiedere opzioni avanzate;
- compilazione manuale di file JSON ridotta al minimo: quando un input strutturato resta necessario, deve essere accompagnato da draft, template, guida leggibile e validazione locale; gli incrementi futuri devono preferire import, wizard, generatori o comandi `prepare` dove possibile;
- dipendenze Python esterne dichiarate in `family-office-engine/pyproject.toml`, installate nel venv del repository e verificate con l'interprete del venv prima di eseguire parser, CLI o test;
- output riproducibili con input e seed dichiarati;
- privacy conforme, titolarità trasparente verso autorità e intermediari;
- revisione umana per raccomandazioni fiscali, legali o di investimento.

## Regola di non anticipazione dell'AI

La roadmap V5 non può essere usata per colmare capacità deterministiche mancanti. L'AI può classificare, pianificare, recuperare conoscenza e spiegare output, ma non deve inventare dati, aliquote, rendimenti, diritti pensionistici o risultati di scenario.

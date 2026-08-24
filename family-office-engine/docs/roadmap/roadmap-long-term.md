# Long-Term Roadmap

Il traguardo è un personal family office locale e verificabile che consolida documenti, applica regole versionate, simula scenari, confronta strategie e risponde in linguaggio naturale senza delegare i calcoli critici all'LLM.

## Percorso

1. **MVP** — ingestion, patrimonio netto, simulazione e report iniziale: `roadmap-mvp.md`.
2. **V1** — parser delle principali fonti documentali: `roadmap-v1.md`.
3. **V2** — cashflow documentale, fiscalità V1, RITA e successione: `roadmap-v2.md`.
4. **V3 Decision Core** — household graph, timeline, pensioni, lifecycle, scenari e raccomandazioni spiegabili: `roadmap-v3-decision-core.md`.
5. **V4 Wealth Planning** — decumulo, investimenti tax-aware, cross-border, immobiliare, polizze e successione avanzata: `roadmap-v4-wealth-planning.md`.
6. **V4B Work Transition** — ottimizzazione deterministica full-time → part-time → cessazione → RITA/patrimonio → pensioni, con timeline mensile e scenari contributivi: `roadmap-v4b-work-transition.md`.
7. **V5 AI Orchestration** — domande naturali, planner, tool execution, citazioni, guardrail e memoria decisionale: `roadmap-v5-ai-orchestration.md`. V5.1/V5.2 sono gia' completati; V5.3+ riprendono dopo il gate V4B.
8. **V6 Operations & Compliance** — refresh, alert, sicurezza, audit, aggiornamenti normativi e review annuale: `roadmap-v6-operations-compliance.md`.

L'ordine, gli stati, i gate e l'algoritmo automatico di selezione sono definiti in `roadmap-index.md`.

## Principi non negoziabili

- privacy conforme, non opacità;
- dati personali solo nel workspace privato;
- calcoli fiscali, previdenziali e finanziari deterministici e testati;
- provenance e validità temporale di dati e regole;
- CLI semplice, memorabile e orientata a workflow completi, con comandi corti, default del workspace e demo/smoke senza path JSON lunghi;
- compilazione manuale di file JSON ridotta al minimo, sostituita dove possibile da import documentali, wizard, generatori, comandi `prepare` e guide compilabili;
- raccomandazioni spiegabili, reversibili e soggette a revisione umana quando necessario;
- AI limitata a retrieval, pianificazione, orchestrazione e spiegazione di evidenze.

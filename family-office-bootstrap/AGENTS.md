# Agent Operating Instructions

Queste istruzioni valgono per qualsiasi coding agent.

## Ordine di lettura obbligatorio

1. `docs/repository-map.md`
2. `docs/developer-playbook.md`
3. `docs/workflow.md`
4. `docs/next-increment-developer-plan.md`
5. `../family-office-engine/docs/current-next-increment.md`
6. `../family-office-engine/docs/roadmap/roadmap-index.md`
7. roadmap attiva indicata dall'indice, partendo da `roadmap-v2.md`
8. `../family-office-engine/docs/roadmap/roadmap-long-term.md`
9. `../family-office-engine/docs/decision-log.md`

L'agente deve leggere le altre roadmap solo quanto basta per verificare dipendenze e gate; non deve anticiparne l'implementazione.

## Principi

- Non inserire dati personali nel repository `family-office-engine`.
- Non usare LLM per calcoli fiscali, previdenziali o finanziari: usare regole e simulatori testati.
- Ogni incremento deve essere piccolo, verificabile e tracciabile.
- Aggiornare documentazione, test, stato roadmap e decision log insieme al codice.
- Se cambia la normativa: aggiornare prima `knowledge`, poi `rules`, poi test, infine `engine`.
- Usare `roadmap-index.md` come unica politica di selezione del prossimo incremento.
- Non saltare un incremento bloccato: creare prima il più piccolo incremento abilitante.
- Non anticipare la roadmap AI per compensare dati, regole o simulatori mancanti.

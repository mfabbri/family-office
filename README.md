# Family Office AI Project

Pacchetto unico di avvio per il consulente finanziario/fiscale personale.

## Struttura

- `family-office-bootstrap/` — metodo operativo, roadmap, prompt, playbook, governance agentica.
- `family-office-engine/` — codice riusabile per calcoli, simulazioni, report, CLI.
- `family-office-rules/` — regole deterministiche fiscali, aliquote, vincoli, compliance, RW/IVAFE/IVIE.
- `family-office-knowledge/` — conoscenza fiscale/patrimoniale generale, riferimenti normativi, glossario, strategie.
- `family-office-workspace/` — caso concreto familiare, asset inventory, scenari, documenti di lavoro.

## Primo passo consigliato

Aprire la root del progetto e far leggere all'agente:

1. `family-office-bootstrap/AGENTS.md`, se presente;
2. roadmap e playbook in `family-office-bootstrap/docs/`;
3. profilo e asset inventory in `family-office-workspace/`.

L'obiettivo iniziale non è generare subito strategie fiscali, ma consolidare un inventario patrimoniale verificabile e separare correttamente:

- conoscenza normativa generale;
- regole calcolabili;
- dati personali del workspace;
- motore software;
- metodo operativo dell'agente.

## Roadmap operativa

Il prossimo incremento viene scelto automaticamente usando:

1. `family-office-engine/docs/current-next-increment.md`;
2. `family-office-engine/docs/roadmap/roadmap-index.md`;
3. la prima roadmap attiva nell'ordine V2 → V3 → V4 → V5 → V6.

Le roadmap V3–V6 separano Decision Core, Wealth Planning, AI Orchestration e Operations/Compliance, evitando che l'AI venga usata prima che dati, regole e simulatori siano verificabili.

## Previdenza spagnola

La roadmap V3 prevede una pipeline documentale e deterministica basata su Vida Laboral, basi contributive ufficiali e nóminas, seguita da stima della prestazione e coordinamento UE. La fiscalità e il netto per residente italiano sono trattati separatamente nella roadmap V4.

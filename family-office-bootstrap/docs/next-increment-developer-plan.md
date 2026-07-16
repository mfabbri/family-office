# Next Increment Developer Plan

Questo piano consente di avviare una sessione senza scegliere manualmente il prossimo incremento. La selezione è governata da `family-office-engine/docs/roadmap/roadmap-index.md`.

## Prompt breve

```text
Leggi AGENTS.md, usa roadmap-index.md per scegliere il prossimo incremento, salva il piano in current-next-increment.md e procedi fino ai criteri di completamento.
```

## Fonti da leggere

1. `family-office-bootstrap/AGENTS.md`
2. `family-office-bootstrap/docs/repository-map.md`
3. `family-office-bootstrap/docs/developer-playbook.md`
4. `family-office-bootstrap/docs/workflow.md`
5. `family-office-bootstrap/docs/next-increment-developer-plan.md`
6. `family-office-engine/docs/current-next-increment.md`
7. `family-office-engine/docs/roadmap/roadmap-index.md`
8. roadmap attiva e contratti citati dall'incremento selezionato
9. `family-office-engine/docs/decision-log.md`

Se un documento manca, l'agente deve segnalarlo, creare un incremento documentale abilitante quando necessario e continuare con il contesto affidabile disponibile.

## Algoritmo di scelta

Applicare integralmente l'algoritmo in `roadmap-index.md`:

1. continuare l'incremento corrente se `planned` o `in_progress`;
2. se `blocked`, risolvere il blocker con un micro-incremento abilitante;
3. se `done`, selezionare la prima roadmap non completata;
4. prima di scegliere il prossimo incremento funzionale, verificare la cadenza audit: dopo 4 incrementi funzionali completati senza audit, selezionare o creare il micro-incremento di code audit nella roadmap attiva;
5. scegliere il primo incremento `planned` con dipendenze soddisfatte;
6. non saltare a V5 per sostituire capacità deterministiche non implementate;
7. non usare dati reali nei test del repository software.

## Piano da salvare

Aggiornare:

```text
family-office-engine/docs/current-next-increment.md
```

Il file deve contenere:

- ID e titolo dell'incremento;
- stato: `planned`, `in_progress`, `done` o `blocked`;
- roadmap di appartenenza;
- motivazione e dipendenze;
- repository coinvolti;
- input attesi e classificazione dei dati;
- output e contratti prodotti o modificati;
- file previsti;
- test e verifiche;
- documentazione da aggiornare;
- criteri di completamento;
- rischi, esclusioni e blocker.

## Dimensione del micro-incremento

Un incremento deve produrre preferibilmente una sola capacità osservabile, ad esempio:

- un contratto e il relativo validatore;
- un parser per una famiglia documentale;
- un rule pack e i suoi test;
- un singolo tool deterministico;
- una migrazione di snapshot;
- un controllo di qualità o sicurezza.
- un code audit periodico dopo 4 incrementi funzionali.

Se richiede più contratti, più migrazioni indipendenti o più domini normativi, dividerlo in sotto-incrementi con suffisso alfabetico.

## Procedura operativa

1. **Start:** leggere fonti e stato.
2. **Selection:** scegliere o confermare l'incremento.
3. **Planning:** salvare il piano e impostare `in_progress` quando inizia il codice.
4. **Implementation:** modificare solo i file necessari.
5. **Verification:** unit, integration, golden/regression secondo disponibilità.
6. **Documentation:** aggiornare contratti, roadmap, current increment e decision log.
7. **Review:** controllare privacy, sicurezza, provenance, riproducibilità e compatibilità multipiattaforma.
8. **Completion:** marcare `done` solo quando i criteri sono verificati; non aprire automaticamente il codice del passo successivo nella stessa sessione salvo richiesta esplicita.

## Output atteso dall'agente

All'inizio:

- incremento scelto e ID;
- motivo della selezione;
- dipendenze verificate;
- file previsti;
- test previsti.

Alla fine:

- capacità completata;
- test e controlli eseguiti;
- contratti e documenti aggiornati;
- stato roadmap;
- prossimo incremento deducibile, senza implementarlo automaticamente nella stessa sessione.

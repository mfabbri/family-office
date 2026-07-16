# V2 Roadmap — Cashflow and Rules Foundation

## Obiettivo

Passare dalla fotografia patrimoniale a simulazioni alimentate da cashflow documentali e prime regole fiscali/previdenziali deterministiche.

## Incrementi

| ID | Incremento | Stato |
|---|---|---|
| V2.1 | Monte Carlo riproducibile | `done` |
| V2.2 | Dashboard decisionale | `done` |
| V2.3 | Cashflow model V2 con ingressi ricorrenti manuali | `done` |
| V2.4 | Payroll ingestion V1 da buste paga/CU classificate | `done` |
| V2.5 | Cashflow from payroll V1 usando netti reali estratti | `done` |
| V2.5a | Diagnostica import payroll prima delle tax rules | `done` |
| V2.6a | Runtime rule pack fiscale V1 con fixture sintetica | `done` |
| V2.6b | Import documenti fiscali reali CU e dichiarazione | `done` |
| V2.6c | Riconciliazione payroll, CU e dichiarazione | `done` |
| V2.6 | Tax rules V1 deterministiche, versionate e testate | `done` |
| V2.7 | Ottimizzatore RITA V1 | `done` |
| V2.8 | Successione e donazioni V1 | `done` |

## V2.5 — Cashflow from payroll V1

Collegare `payroll.snapshot.json` al cashflow, aggregando periodi, distinguendo valori osservati e annualizzati, evitando duplicazioni con assunzioni manuali.

- Output: `earned-income-cashflow/v1`.
- Test: mesi mancanti, tredicesima/quattordicesima, più datori, duplicati, prevalenza documentale.
- Done quando: stipendio e trattenute documentali alimentano la baseline con confidence e gap.

## V2.6 — Tax rules V1

Implementare il runtime minimo dei rule pack e un primo calcolo fiscale personale versionato per anno, partendo da knowledge e fixture sintetiche.

- Output: loader rule pack, `tax-calculation/v1`, explainability per regola.
- Test: anno, giurisdizione, scaglioni/aliquote applicabili, addizionali parametrizzate e regola mancante.
- Done quando: ogni importo fiscale deriva da rule ID, periodo di validità e test.

## V2.7 — RITA optimizer V1

Confrontare scenari RITA semplici usando posizione, età, periodo, fabbisogno e regole disponibili, dichiarando le condizioni non verificabili.

- Output: `rita-options/v1`.
- Test: eleggibilità, durata, importo, tassazione parametrica e gap bloccanti.
- Done quando: il risultato distingue diritto, stima e assunzione.

## V2.8 — Successione and donations V1

Creare una prima fotografia di masse, titolari, beneficiari, quote teoriche e liquidità, senza sostituire la verifica notarile/legale.

- Output: `estate-baseline/v1`.
- Test: coniuge, figli, asset esteri, titolarità ignota e polizze.
- Done quando: il sistema identifica dati mancanti e scenari base senza proporre occultamento.

## Direzione payroll e fiscalità

Le buste paga e le CU entrano prima come fonti documentali nel workspace privato. Il primo uso è l'estrazione di importi già presenti nei documenti: netto pagato, imponibili, trattenute e contributi dichiarati.

Il calcolo fiscale da lordo arriva solo tramite un modulo deterministico in `family-office-rules`/`family-office-engine`, con regole versionate e test sintetici. Non usare LLM per calcoli fiscali.

## Handoff alla V3

Dopo V2.8, verificare il gate V2 → V3 in `roadmap-index.md`. Il primo incremento successivo è V3.1; non usare direttamente la roadmap AI.

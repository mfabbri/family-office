# Investment opportunity analyzer

Playbook per introdurre o estendere asset produttivi valutabili dal family-office engine.

## Obiettivo

Valutare un'opportunita' come uso alternativo del capitale familiare usando servizi deterministici, con separazione esplicita fra:

- rendimento dell'asset;
- rendimento dell'equity e leva;
- fiscalita' e compliance;
- beneficio d'uso personale;
- costo del tempo del proprietario;
- liquidita', concentrazione e opportunity cost sul patrimonio complessivo.

## Read first

1. roadmap/current increment;
2. contratto o servizio di investimento piu' vicino;
3. `real_estate_plan.py`, `wealth_strategy.py`, liquidity/planning contracts solo se effettivamente coinvolti;
4. test del servizio piu' vicino;
5. knowledge/rules solo se serve nuova semantica normativa.

Non leggere tutte le roadmap o tutti i servizi finanziari.

## Contratto generico target

Preferire una base `investment-opportunity/v1` con adapter specifici, ad esempio:

- `real-estate-investment/v2`;
- `rentable-movable-asset/v1`.

Il core deve poter rappresentare almeno:

- acquisition cost e initial capex;
- operating revenue/costs;
- financing/debt service;
- taxes/fees come input o output di rule pack versionati;
- residual/exit value;
- owner-hours e owner-hour-value;
- personal-use economic benefit separato dal cash flow imponibile;
- base/upside/adverse scenario;
- liquidity and concentration impact;
- opportunity-cost comparator.

## Metriche

Implementare solo metriche con definizione contrattuale e testabile. Candidati:

- NOI;
- free cash flow;
- cash-on-cash return;
- cap rate dove semanticamente appropriato;
- DSCR;
- break-even occupancy/utilization;
- payback period;
- NPV;
- IRR;
- equity multiple.

Non inventare market return, occupancy, tariffa, rivalutazione, inflazione o residual value. Devono essere input/assunzioni versionate.

## Real estate adapter

Supportare progressivamente:

- long-term rental;
- short-term rental;
- mixed personal/rental use;
- management fee/agency;
- vacancy;
- maintenance/condominium/insurance;
- acquisition/exit costs;
- property tax/rental tax solo tramite knowledge/rules validi.

## Camper / rentable movable asset adapter

Separare sempre:

- giorni disponibili;
- giorni di uso personale;
- giorni noleggiati;
- tariffa media;
- platform/agency fee;
- insurance, storage, cleaning, maintenance, tyres, delivery/collection;
- mileage/wear assumptions;
- downtime and major-repair scenario;
- residual value;
- personal-use benefit come metrica economica non fiscale.

La classificazione `personal | occasional_rental | habitual_rental | business` non va dedotta automaticamente senza una regola normativa o un input validato.

## Financing

Riutilizzare o introdurre `financing-plan/v1` per distinguere:

- asset return;
- equity return;
- interest/principal;
- remaining debt;
- LTV;
- debt service;
- DSCR;
- fixed/variable rate assumptions;
- fees and early repayment where explicit.

## Opportunity cost

Confrontare lo stesso capitale, lo stesso orizzonte e scenari dichiarati con alternative gia' disponibili nel patrimonio (es. tax-aware portfolio/cash), senza inventare un benchmark. Se manca il benchmark, produrre un data gap.

## Household integration

Prima di marcare un investimento come comparabile, verificare impatto su:

- liquidity plan / emergency reserve;
- concentration;
- retirement/work-exit cash flow;
- protection gaps;
- estate complexity/reversibility;
- wealth-strategy package ranking.

Un buon IRR non supera automaticamente un vincolo di liquidita'.

## Model routing

- Luna/low: inventario file, fixture, schema, mapping campi, test matrix meccanica.
- Terra/medium: contratto, servizio deterministico, CLI/docs, integrazione ordinaria.
- Terra/high reviewer: contract drift, edge cases, regression cross-module.
- Sol/high financial reviewer: formule nuove, leverage, IRR/NPV/DSCR, scenario semantics.
- Sol/high normative reviewer: nuova fiscalita'/classificazione attivita'.
- Sol/xhigh: solo controversia normativa/architetturale materiale non risolta con fonti e test.

## Done when

- calcoli riproducibili e testati;
- assumptions e data gaps espliciti;
- personal-use benefit separato da revenue/cash flow fiscale;
- tax/legal treatment proviene da rule pack o resta gap;
- leverage non nasconde asset return;
- adverse scenario presente per asset illiquidi;
- integrazione con wealth strategy non crea nuove imposte/rendimenti nell'LLM;
- roadmap, current increment, docs e audit cadence sono coerenti.

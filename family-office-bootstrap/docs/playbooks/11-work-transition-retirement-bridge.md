# Work Transition & Retirement Bridge

Classificazione minima T4. Usare insieme a `07-normative-change.md` quando cambiano fiscalita', contribuzione, diritto pensionistico o RITA; usare anche `06-cross-repository-change.md` se il contratto attraversa engine/rules/knowledge.

## Read first

- `family-office-engine/docs/roadmap/roadmap-index.md`;
- `family-office-engine/docs/current-next-increment.md`;
- `family-office-engine/docs/roadmap/roadmap-v4b-work-transition.md`;
- `family-office-engine/docs/roadmap/work-transition-architecture.md`;
- solo contratti, servizi, rule pack e test citati dall'incremento corrente.

Non leggere automaticamente tutto il workspace o tutte le roadmap storiche.

## Invarianti

- separare full-time exit, work cessation, pension entitlement e pension payment start;
- timeline primaria mensile;
- reddito da lavoro pre-uscita deve essere uno stream esplicito, non `shortfall = 0`;
- FTE cambia netto e contribuzione tramite regole, non tramite moltiplicazione del netto;
- pensione futura deve dipendere dai contributi prodotti dalle fasi lavorative;
- INPS, Spagna/UE, spouse pension e RITA restano stream separati;
- RITA ha eligibility e start/end;
- non sommare lordo a spese nette senza bridge fiscale esplicito;
- asset non liquidabili o vincolati non finanziano il bridge;
- baseline deterministico prima del Monte Carlo;
- un gap materiale blocca date e ranking.

## Flow

```text
readiness/provenance
  → work phases
  → employment net + contributions
  → pension entitlement/payment timeline
  → bridge streams + liquidity
  → monthly deterministic simulation
  → stochastic stress
  → candidate generator
  → optimizer
  → evidence-backed plan
```

## Review gates

Prima di chiudere un incremento che cambia calcoli o date:

1. test mirati;
2. regression coerente col rischio;
3. `roadmap_audit.py`;
4. review `fo_retirement_transition_reviewer`;
5. se normativa, review `fo_normative_reviewer` oppure una review combinata delimitata, senza duplicare lavoro;
6. verificare privacy e assenza di dati personali nelle fixture.

## Anti-pattern da rifiutare

- pensione che parte automaticamente quando il lavoro finisce;
- un unico `retirement_age` per tutti gli stream;
- netto part-time = netto full-time × FTE;
- saldo patrimonio unico che ignora liquidity buckets;
- RITA permanente o senza eligibility;
- annualizzazione che perde mensilita' aggiuntive/start-end;
- recommendation basata solo sulla media Monte Carlo;
- LLM che colma importi o regole mancanti.

## Done when

La capability osservabile dell'incremento e' riproducibile, spiega provenance e gap, mantiene le date separate, non mescola gross/net, passa i gate normativi/tecnici pertinenti e non anticipa funzioni di incrementi successivi.

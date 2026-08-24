# Golden Use Case — Full-time to Part-time to Pension

## Intent

Verificare end-to-end che il Family Office possa trovare la prima uscita sostenibile dal full-time senza confonderla con cessazione o pensionamento.

## Fixture sintetica

Household con due adulti, nessun dato personale reale. Il primary ha reddito full-time, possibilita' di FTE 60% o 40%, previdenza INPS e una carriera ES coordinabile UE. Il spouse continua a generare reddito per una parte dell'orizzonte. Il household dispone di liquidita', investimenti liquidabili e una posizione di previdenza complementare potenzialmente utilizzabile come RITA quando eleggibile.

## Candidate set minimo

- hard stop: 100% → 0%;
- phased A: 100% → 60% per 4 anni → 0%;
- phased B: 100% → 40% per 3 anni → 0%;
- almeno tre diverse date di uscita dal full-time.

## Vincoli

- spending floor dichiarato;
- emergency reserve minimo;
- terminal wealth floor;
- probability of success minima per scenario stochastic;
- asset non liquidabili esclusi dal bridge;
- pensioni attive solo da entitlement/payment start supportati;
- RITA solo da finestra eleggibile;
- nessun gross/net mixing.

## Output obbligatorio

```text
earliest_full_time_exit_date
recommended_full_time_exit_date
full_work_exit_date
phases[]
pension_start_dates[]
bridge_streams[]
success_probability
p05_terminal_wealth
minimum_liquidity_buffer_months
rejected_candidates[]
blocking_data_gaps[]
```

## Acceptance tests

1. Una candidate part-time puo' rendere sostenibile un'uscita full-time precedente rispetto all'hard stop.
2. Ridurre FTE modifica il netto in modo non necessariamente lineare e modifica la contribuzione futura.
3. `work_cessation_date` non attiva automaticamente INPS o pensione ES.
4. Una RITA temporanea riduce i prelievi da asset solo nel proprio intervallo.
5. Un crash nei primi anni del bridge puo' far fallire lo stress pur lasciando positivo il baseline.
6. Uno snapshot stale o una pensione spouse mancante blocca l'optimizer se materiale.
7. Il risultato e' riproducibile a parita' di input/rule pack/seed.
8. Il legacy `work-exit-feasibility/v1` non viene presentato come equivalente al nuovo optimizer.

## V5 hand-off

Dopo V4.20 la supported-question taxonomy V5.3 deve poter classificare richieste come:

- "quando posso lasciare il full-time?";
- "se lavoro al 60% per 4 anni cosa cambia?";
- "qual e' il primo anno in cui posso smettere del tutto?";
- "quanto patrimonio serve per il ponte fino a INPS e Spagna?".

Il planner AI dovra' invocare i tool registrati V4B e spiegare i risultati; non ricalcolarli.

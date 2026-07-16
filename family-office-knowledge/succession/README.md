# Succession

V2.8 produce una baseline successoria locale e verificabile. Non sostituisce notaio, avvocato, commercialista o dichiarazione di successione.

## Perimetro V1

Il sistema puo' costruire:

- masse osservate da `net-worth.snapshot.json`;
- massa successoria calcolabile solo per componenti con quota di titolarita' esplicita;
- quote teoriche di successione legittima per casi semplici con coniuge e/o figli;
- indicatori di liquidita' per asset class;
- gap per titolarita', beneficiari, estero, testamento, debiti, immobili, donazioni pregresse e verifica professionale.

## Fuori perimetro

V1 non calcola:

- imposta di successione o donazione;
- imposte ipotecarie o catastali;
- quote di legittima avanzate, collazione, riduzione o riunione fittizia;
- effetti di testamenti, patti, trust, vincoli esteri o regimi patrimoniali complessi;
- validita' di beneficiari di polizze o fondi pensione;
- valutazioni catastali o immobiliari.

## Rule pack

Regola calcolabile:

```text
family-office-rules/succession/italy-current.json
```

Il rule pack espone solo quote teoriche di successione legittima per scenari semplici. Se lo scenario familiare non e' coperto, l'engine deve produrre un gap invece di stimare.

## Fonti

- Codice civile, Regio decreto 16 marzo 1942, n. 262, Libro II, successioni legittime: https://www.normattiva.it/eli/id/1942/04/04/042U0262/CONSOLIDATED
- Decreto legislativo 31 ottobre 1990, n. 346, testo unico successioni e donazioni: https://www.normattiva.it/eli/id/1990/10/31/090G0380/CONSOLIDATED
- Decreto-legge 3 ottobre 2006, n. 262, articolo 2, commi 47 e seguenti, reintroduzione e aliquote dell'imposta: https://www.normattiva.it/eli/id/2006/10/03/006G0285/CONSOLIDATED

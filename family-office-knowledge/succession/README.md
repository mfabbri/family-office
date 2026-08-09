# Succession

V2.8 produce una baseline successoria locale e verificabile. Non sostituisce notaio, avvocato, commercialista o dichiarazione di successione.

## Aggiornamento V4.9 - successione e donazioni V2

Verificato il 2026-07-29 su fonti Normattiva.

Per il perimetro Italia, il motore puo' estendere la baseline V1 con:

- massa ereditaria nota calcolata solo da valori, quote di titolarita' e provenance esplicite;
- massa fittizia dichiarata, sommando alla massa nota le donazioni pregresse marcate come rilevanti ai fini della verifica civilistica;
- quote di riserva per casi semplici con coniuge e/o figli;
- confronto tra attribuzioni pianificate, donazioni pregresse dichiarate e quota minima di riserva;
- stima deterministica di imposta di successione/donazione solo per relazioni coperte dal rule pack e solo su valori dichiarati;
- gap espliciti per estero, polizze con trattamento successorio non documentato, attribuzioni incomplete, liquidita' fiscale non dichiarata, valori o provenance mancanti.

La quota di riserva non sostituisce collazione, riduzione, riunione fittizia notarile o contenzioso. Il sistema deve segnalare conflitti e richiedere revisione professionale, non proporre schermi opachi o strategie elusive.

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
family-office-rules/succession/italy-2026-v2.json
```

Il rule pack espone solo quote teoriche di successione legittima per scenari semplici. Se lo scenario familiare non e' coperto, l'engine deve produrre un gap invece di stimare.

Il rule pack V2 espone quote di riserva e aliquote/franchigie per casi semplici di pianificazione. Se relazione, giurisdizione, trattamento assicurativo, donazione o scenario non sono coperti, l'engine deve produrre un gap.

## Fonti

- Codice civile, Regio decreto 16 marzo 1942, n. 262, Libro II, successioni legittime: https://www.normattiva.it/eli/id/1942/04/04/042U0262/CONSOLIDATED
- Decreto legislativo 31 ottobre 1990, n. 346, testo unico successioni e donazioni: https://www.normattiva.it/eli/id/1990/10/31/090G0380/CONSOLIDATED
- Decreto legislativo 18 settembre 2024, n. 139, revisione imposte indirette diverse dall'IVA: https://www.normattiva.it/atto/caricaDettaglioAtto?atto.codiceRedazionale=24G00157&atto.dataPubblicazioneGazzetta=2024-10-02
- Decreto-legge 3 ottobre 2006, n. 262, articolo 2, commi 47 e seguenti, reintroduzione e aliquote dell'imposta: https://www.normattiva.it/eli/id/2006/10/03/006G0285/CONSOLIDATED

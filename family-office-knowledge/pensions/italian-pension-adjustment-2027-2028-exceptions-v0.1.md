# Adeguamento pensionistico IT 2027?2028 ? fonte ed eccezioni v0.1

**Stato:** candidato Knowledge in attesa di review normativa exact-hash  
**Data della verifica delle fonti:** 2026-11-21  
**Perimetro:** fonte e condizioni di applicabilit? dell'incremento requisiti 2027?2028 per il solo screening pensionistico italiano; non costituisce una regola eseguibile n? una determinazione individuale.

## Fonti e ruoli

| ID | Fonte ufficiale | Ruolo | Data pubblicazione / vigenza rilevante | Consultazione |
|---|---|---|---|---|
| it.l199-2025.original-publication | Legge 30 dicembre 2025, n. 199, Supplemento ordinario n. 42/L alla GU n. 301 del 30-12-2025, art. 1 commi 185?190. [Pubblicazione ufficiale GU](https://www.gazzettaufficiale.it/eli/gu/2025/12/30/301/so/42/sg/pdf) | Legislazione primaria, pubblicazione originale | I commi 185?190 entrano in vigore il 30-12-2025 secondo le note ufficiali di pubblicazione. | 2026-11-21 |
| it.inps.circolare-28-2026 | INPS, Circolare n. 28 del 16-03-2026, sezioni 2?4. [Testo ufficiale INPS](https://www.inps.it/it/it/inps-comunica/atti/circolari-messaggi-e-normativa/dettaglio.circolari-e-messaggi.2026.03.circolare-numero-28-del-16-03-2026_15199.html) | Prassi amministrativa; non ? fonte primaria | Istruzioni applicative per il biennio 2027?2028. | 2026-11-21 |
| it.inps.old-age-guidance | INPS, Pensione di vecchiaia. [Scheda ufficiale](https://www.inps.it/it/it/dettaglio-scheda.it.schede-servizio-strumento.schede-servizi.pensione-di-vecchiaia.html) | Guidance amministrativa | Requisiti descritti per le coorti/periodi esposti nella pagina. | 2026-11-21 |

## Fatti normativi da tenere distinti

1. L'art. 1, comma 185, legge 199/2025 prevede per il biennio 2027?2028 l'incremento dei requisiti di accesso al sistema pensionistico, applicato nella misura di un mese nel 2027 e di tre mesi nel 2028.
2. I commi 186?187 disciplinano condizioni in cui l'incremento non si applica ai requisiti di pensione di vecchiaia e pensione anticipata richiamati dall'art. 24, commi 6 e 10, D.L. 201/2011. Le condizioni includono specifiche professioni gravose con durate di attivit? e anzianit? contributiva minima, oppure determinate lavorazioni faticose/pesanti con le condizioni del D.Lgs. 67/2011 e anzianit? contributiva minima. Il perimetro soggettivo comprende gli iscritti indicati dalla legge; l'appartenenza a un profilo FPLD/AGO, da sola, non prova n? esclude queste condizioni.
3. Il comma 190 dispone che il comma 186 non si applica a chi, al momento del pensionamento, gode dell'APE Sociale; quindi non ? corretto trasformare una generica classificazione di profilo in esenzione se ? presente tale condizione.
4. I commi 188?189 disciplinano fattispecie distinte (lavoratori precoci e modifiche al D.Lgs. 67/2011). Non sono mappate in questa nota come percorsi di eligibility.
5. La circolare INPS 28/2026 espone requisiti anagrafici di 67 anni nel 2026, 67 anni e un mese nel 2027 e 67 anni e tre mesi nel 2028; per l'alternativa contributiva dei soggetti con primo accredito dal 1996 indica cinque anni effettivi e 71 anni, 71 anni e un mese, 71 anni e tre mesi rispettivamente. L'applicazione delle esclusioni dei commi 186?187 al percorso ex art. 24, comma 7, D.L. 201/2011 non ? risolta da questa nota e non deve essere inferita per analogia.

## Limiti e gap vincolanti

- Nessun pack Rules o consumer Engine ? approvato da questa nota.
- Le condizioni dei commi 186?187 richiedono prove e classificazioni specifiche; un valore booleano generico o una dichiarazione negativa non costituisce prova source-bound. Profilo sconosciuto/contraddittorio resta not_assessed + data_gaps.
- Per l'APE Sociale rileva la condizione descritta al comma 190 al momento del pensionamento; non si pu? inferire da una categoria lavorativa.
- Il perimetro del comma 7 art. 24, i percorsi precoci/usuranti dei commi 188?189, le forme fuori FPLD e la prova amministrativa individuale restano fuori da questa nota.
- Il valore soglia dell'assegno sociale per il 2027?2028 resta unknown + data_gaps.
- Tutti i cinque eventi della timeline restano not_assessed, date e importi null, con revisione umana richiesta. La cessazione dal lavoro non determina alcuna data pensionistica.

## Uso previsto

Questa nota pu? orientare la progettazione di un successivo Rules versionato solo dopo review normativa indipendente exact-hash. Ogni consumer dovr? trattare l'assenza di prove per condizioni/esclusioni come gap, non come falso, e dovr? mantenere separati screening, requisito maturato, riconoscimento, decorrenza economica e primo pagamento. La nota non chiude n? sblocca V4.14.

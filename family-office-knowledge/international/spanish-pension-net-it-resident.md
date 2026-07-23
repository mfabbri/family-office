# Netto pensione spagnola per residente fiscale italiano

## Ambito

- Giurisdizioni: Italia e Spagna.
- Periodo d'imposta: 2026.
- Verificato il: 2026-07-23.

Questa nota supporta il rule pack `it.spanish-pension-net-it-resident.2026.v1` e il contratto engine `spanish-pension-net-it-resident/v1`.

## Fonti

- Agenzia delle Entrate, dichiarazione precompilata 2026, sezione "Lavoro dipendente e pensioni": per residenti italiani con redditi prodotti all'estero o pensioni ai superstiti di fonte estera e' prevista l'indicazione dei redditi esteri. URL: https://infoprecompilata.agenziaentrate.gov.it/portale/semplificata-mod-lavoro-dipendente-e-pensioni
- Agenzia delle Entrate, dichiarazione precompilata 2026, Quadro CE: il credito d'imposta per redditi prodotti all'estero richiede imposte estere definitive e dati per determinare credito teorico ed effettivo ex art. 165 TUIR. URL: https://infoprecompilata.agenziaentrate.gov.it/portale/quadro-ce
- DPR 22 dicembre 1986, n. 917, art. 165, credito d'imposta per redditi prodotti all'estero: le imposte pagate all'estero a titolo definitivo sono detraibili nei limiti della quota d'imposta italiana corrispondente al rapporto tra redditi esteri e reddito complessivo netto. URL: https://www.normattiva.it/uri-res/N2Ls?urn:nir:presidente.repubblica:decreto:1986-12-22;917~art165!vig
- MEF, circolare n. 9/E del 5 marzo 2015, determinazione del credito d'imposta: riepiloga la formula RE x imposta italiana / RCN e i limiti dell'imposta italiana netta. URL: https://def.finanze.it/DocTribFrontend/getPrassiDetail.do?id=%7B8F43B1E3-7F72-4A17-8572-1F6905FC28F3%7D
- Legge 30 dicembre 2024, n. 207, art. 1 comma 2: scaglioni IRPEF nazionali usati dal rule pack `it.irpef-national.2026.v1`. URL: https://www.gazzettaufficiale.it/eli/id/2024/12/31/24G00229/sg
- Rule pack e knowledge V4.6a: `it-es-pension-tax-classification/v1` determina se la pensione e' imponibile in Italia, in Spagna o bloccata per fatti mancanti.

## Regole operative per il motore

- Se la classificazione convenzionale assegna potesta' impositiva esclusiva all'Italia, la pensione spagnola concorre all'imponibile italiano esplicito.
- Se la classificazione assegna potesta' impositiva esclusiva alla Spagna, il primo incremento V4.6b non calcola IRPEF italiana sulla pensione; espone il lordo, la ritenuta spagnola dichiarata e il netto dopo ritenuta dichiarata.
- L'imposta italiana sulla pensione e' calcolata come differenza tra IRPEF nazionale lorda su `other_italian_taxable_income + gross_spanish_pension` e IRPEF nazionale lorda su `other_italian_taxable_income`.
- Il credito estero e' riconosciuto solo quando l'input dichiara imposta estera definitiva e credito applicabile. Il credito effettivo e' il minimo tra imposta estera definitiva, imposta italiana incrementale sulla pensione, limite art. 165 e capienza dichiarata.
- Il limite art. 165 e' calcolato come `italian_tax_after_pension * foreign_income / total_taxable_income`, con ulteriore limite all'imposta netta/capienza dichiarata quando fornita.

## Limiti

- Non sono calcolati detrazioni, addizionali, acconti, rimborsi, imposte spagnole da aliquote spagnole, credito per imposte non definitive, regime opzionale art. 24-ter, pensioni non classificate o dichiarazione completa.
- Il risultato deve essere revisionato da un professionista per uso fiscale effettivo.

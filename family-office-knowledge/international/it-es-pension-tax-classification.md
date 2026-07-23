# Classificazione fiscale pensioni Italia-Spagna

## Ambito

- Giurisdizioni: Italia e Spagna.
- Periodo d'imposta: 2026, con Convenzione Italia-Spagna vigente dal 24 novembre 1980.
- Verificato il: 2026-07-23.

Questa nota supporta il rule pack `it-es.pension-tax-classification.2026.v1` e il contratto engine `it-es-pension-tax-classification/v1`.

## Fonti

- MEF, Documentazione economica e finanziaria, Convenzione Italia-Spagna del 29 settembre 1980, articolo 18 "Pensioni": pensioni e remunerazioni analoghe da cessato impiego sono imponibili solo nello Stato di residenza, salvo art. 19 paragrafo 2. URL: https://def.finanze.it/DocTribFrontend/getAttoNormativoDetail.do?ACTION=getArticolo&articolo=Articolo+18&codiceOrdinamento=200001800000000&id=%7B7913F6DF-FFD7-436F-9416-CC6F2E1C6962%7D
- BOE, Convenio entre Espana e Italia para evitar la doble imposicion, articoli 18 e 19: testo spagnolo ufficiale della Convenzione. URL: https://boe.es/buscar/act.php?id=BOE-A-1980-27501
- Agenzia delle Entrate, FiscoOggi, risposta n. 246/2019 su pensionato residente in Spagna: per pensioni da ex lavoratori dipendenti privati la Convenzione prevede tassazione nel Paese di residenza e detassazione nel Paese di erogazione, previa documentazione. URL: https://www.fiscooggi.it/rubrica/normativa-e-prassi/articolo/se-pensionato-risiede-spagna-tasse-versate-si-recuperano-italia
- Agencia Tributaria, scheda "Italia" per residenti con redditi esteri: distingue pensioni da lavoro pubblico, generalmente imponibili nello Stato erogatore salvo nazionalita' dello Stato di residenza, e pensioni da lavoro privato imponibili nello Stato di residenza. URL: https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/folletos/folletos-residentes-rentas-extranjeras/italia.html
- INPS, normativa fiscale residenti all'estero: l'applicazione delle Convenzioni richiede verifica dei requisiti e documentazione per chiedere detassazione o trattamento convenzionale. URL: https://www.inps.it/it/it/dettaglio-approfondimento.schede-informative.49937.normativa-fiscale-residenti-all-estero.html

## Regole operative per il motore

- Pensione collegata a precedente impiego privato: classificare in art. 18; la potesta' impositiva e' esclusiva dello Stato di residenza fiscale del beneficiario.
- Pensione pagata da Stato, suddivisione politica/amministrativa o ente locale per servizi resi a tale ente: classificare in art. 19.2; in generale la potesta' impositiva e' esclusiva dello Stato pagatore.
- Eccezione art. 19.2: se il beneficiario e' residente nell'altro Stato contraente e ne ha la nazionalita', la pensione pubblica e' imponibile solo nello Stato di residenza.
- Se residenza fiscale, nazionalita' richiesta, payer pubblico/privato o natura del servizio non sono espliciti, il motore deve produrre `data_gaps` e non applicare automaticamente la Convenzione.
- La classificazione produce documenti richiesti e warning operativi; non calcola imposta, netto, credito per imposte estere o rimborsi.

## Limiti

- Non sono coperti organismi ibridi, enti previdenziali professionali con status controverso, pensioni di sicurezza sociale trattate da accordi specifici diversi, regimi opzionali per nuovi residenti, addizionali, ritenute effettive e dichiarazione completa.
- L'applicazione pratica richiede certificato di residenza fiscale, documentazione del payer e revisione professionale.

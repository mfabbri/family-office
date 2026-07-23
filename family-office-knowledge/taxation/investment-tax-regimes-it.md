# Regimi fiscali investimenti Italia

## Ambito

- Giurisdizione: Italia.
- Periodo d'imposta: 2026, salvo successive modifiche normative.
- Verificato il: 2026-07-23.

Questa nota supporta il rule pack `it.tax-aware-investment.2026.v1` e il contratto engine `tax-aware-portfolio/v1`.

## Fonti

- Agenzia delle Entrate, dichiarazione precompilata 2026, sezione "Plusvalenze di natura finanziaria": indica le plusvalenze e gli altri redditi diversi finanziari soggetti a imposta sostitutiva del 26% e il codice tributo relativo. URL: https://infoprecompilata.agenziaentrate.gov.it/portale/semplificata-mod-plusvalenze-natura-finanziaria
- Agenzia delle Entrate, dichiarazione precompilata 2026, sezione "Estero e cripto attivita'": descrive monitoraggio fiscale e determinazione di IVAFE per investimenti e attivita' finanziarie estere. URL: https://infoprecompilata.agenziaentrate.gov.it/portale/semplificata-mod-estero-e-cripto-attivit%C3%A0
- Agenzia delle Entrate, scadenzario IVAFE 2026: conferma soggetti e versamento dell'imposta sul valore delle attivita' finanziarie detenute all'estero. URL: https://www1.agenziaentrate.gov.it/servizi/scadenzario/main.php?chi=3991&come=514&cosa=11515&entroil=30-06-2026&op=4&vista=0
- MEF, Documentazione economica e finanziaria, prassi IVAFE: descrive IVAFE al 2 per mille sui prodotti finanziari e base imponibile di mercato al termine dell'anno. URL: https://def.finanze.it/DocTribFrontend/getPrassiDetail.do?id=%7B8FDC5F14-47CD-43FB-A4CE-637D71401DE6%7D
- Senato della Repubblica, dossier sulla tassazione delle rendite finanziarie: riepiloga aliquota generale del 26%, eccezione 12,5% per titoli di Stato/risparmio postale/project bond, regimi dichiarativo, amministrato e gestito, e bollo annuo 2 per mille sui prodotti finanziari. URL: https://www.senato.it/show-doc?id=1363883&leg=19&part=dossier_dossier1-sezione_sezione13-h1_h13&tipodoc=DOSSIER
- Senato della Repubblica, dossier su IVAFE e bollo: riepiloga imposta di bollo 2 per mille e IVAFE 2 per mille, con IVAFE 4 per mille dal 2024 per prodotti finanziari in Stati o territori a regime fiscale privilegiato individuati dal DM 4 maggio 1999. URL: https://www.senato.it/show-doc?id=1447613&leg=19&part=dossier_dossier1-sezione_sezione1-h1_h15&tipodoc=DOSSIER
- Agenzia delle Entrate, risposta/prassi su broker esteri e regimi: conferma che il regime dichiarativo richiede autoliquidazione e che il regime amministrato richiede intermediari abilitati residenti o stabili organizzazioni in Italia. URL: https://def.finanze.it/DocTribFrontend/getPrassiDetail.do?id=%7BC20F2FF7-894D-43B4-9CD5-484CF0EC0A4B%7D

## Regole operative per il motore

- I redditi finanziari ordinari sono trattati con aliquota sostitutiva del 26% solo quando l'input li dichiara come `ordinary_financial`.
- I redditi da strumenti pubblici qualificati sono trattati con aliquota del 12,5% solo quando l'input li dichiara come `government_qualified`.
- L'imposta di bollo per rapporti/prodotti finanziari detenuti presso intermediario residente e l'IVAFE per prodotti finanziari esteri sono modellate come imposta patrimoniale annua pari allo 0,2% del valore dichiarato.
- Il regime dichiarativo espone un vincolo operativo di dichiarazione/autoliquidazione; il regime amministrato richiede un intermediario italiano abilitato; il regime gestito e' ammesso solo quando l'input dichiara un mandato di gestione.
- Le minusvalenze sono compensate solo contro imponibili compatibili dichiarati nello stesso scenario. Il motore non ricostruisce zainetti fiscali, scadenze quadriennali o categorie da documenti.

## Limiti

- Questa nota non copre PIR, cripto-attivita', partecipazioni qualificate, fondi immobiliari, imposta sulle successioni, fiscalita' estera, credito d'imposta estero, addizionali o dichiarazione completa.
- La quota agevolata di OICR esposti a titoli pubblici richiede un dato dichiarato a monte; senza quel dato il motore deve produrre gap invece di stimare una quota.
- L'IVAFE maggiorata per Stati o territori a regime fiscale privilegiato e le soglie/fissi per conti correnti esteri non sono incluse nel primo rule pack `tax-aware-investment-rule-pack/v1`.

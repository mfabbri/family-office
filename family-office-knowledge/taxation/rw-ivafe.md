# Quadro RW, IVAFE e IVIE

## Ambito

- Giurisdizione: Italia, con attivita' detenute in Spagna.
- Periodo d'imposta: 2026 per il rule pack operativo; le pagine del modello dichiarativo 2026 possono riferirsi a possedimenti del periodo precedente e sono usate solo come fonte di struttura dichiarativa.
- Verificato il: 2026-07-24.

Questa nota supporta il rule pack `it-es.foreign-asset-monitoring.2026.v2` e il contratto engine `it-es-foreign-assets/v1`.

## Fonti

- Agenzia delle Entrate, dichiarazione precompilata 2026, Quadro RW: chiarisce che il quadro RW riguarda investimenti all'estero e attivita' estere finanziarie per persone fisiche residenti in Italia, anche ai fini IVIE e IVAFE; indica inoltre che il monitoraggio non sussiste per depositi e conti correnti esteri con valore massimo complessivo non superiore a 15.000 euro, restando fermo l'obbligo se e' dovuta IVAFE. URL: https://infoprecompilata.agenziaentrate.gov.it/portale/quadro-rw
- Agenzia delle Entrate, dichiarazione precompilata 2026, sezione "Estero e cripto attivita'": descrive i dati IVIE/IVAFE, il credito per imposta patrimoniale estera entro l'imposta dovuta e la detrazione IVIE per abitazione principale quando spettante. URL: https://infoprecompilata.agenziaentrate.gov.it/portale/semplificata-mod-estero-e-cripto-attivit%C3%A0
- Agenzia delle Entrate, scadenzario IVIE 2026: individua persone fisiche residenti titolari di proprieta' o altro diritto reale su immobili esteri come soggetti IVIE e richiama il versamento saldo 2025/primo acconto 2026. URL: https://www1.agenziaentrate.gov.it/servizi/scadenzario/main.php?chi=3990&come=507&cosa=11514&entroil=30-06-2026&op=4&vista=0
- MEF, Documentazione economica e finanziaria, prassi IVAFE: descrive IVAFE al 2 per mille sui prodotti finanziari esteri e base imponibile legata al valore di mercato al termine dell'anno o del periodo di detenzione. URL: https://def.finanze.it/DocTribFrontend/getPrassiDetail.do?id=%7B8FDC5F14-47CD-43FB-A4CE-637D71401DE6%7D
- Camera dei deputati, tema "Bonus edilizi e tassazione immobiliare": riepiloga l'innalzamento dell'aliquota IVIE ordinaria all'1,06%, il calcolo proporzionale per quota e mesi, il credito per imposte patrimoniali estere e la disciplina dell'abitazione principale. URL: https://temi.camera.it/temi/19_tl18_tassazione_immobili.html
- Normattiva, DL 28 giugno 1990, n. 167, articolo 4: disciplina il monitoraggio fiscale delle attivita' estere e le esclusioni quando le attivita' finanziarie sono affidate in gestione o amministrazione a intermediari residenti e i redditi sono assoggettati a ritenuta o imposta sostitutiva. URL: https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legge:1990-06-28;167~art4

## Regole operative per il motore

- Il motore classifica solo attivita' dichiarate esplicitamente come conti/depositi, prodotti finanziari, piani pensionistici esteri o immobili esteri.
- Per un residente fiscale italiano, un'attivita' spagnola detenuta presso intermediario non residente richiede valutazione RW; eventuali esclusioni per intermediario residente sono applicate solo su attivita' finanziarie e solo se l'input documenta gestione/amministrazione/intervento dell'intermediario e assoggettamento dei redditi a ritenuta o imposta sostitutiva.
- Per conti e depositi esteri, il monitoraggio usa la soglia di valore massimo complessivo annuo del rule pack; l'IVAFE fissa usa la giacenza media complessiva e importo fisso del rule pack. Se sono presenti piu' conti e manca un aggregato documentato, il motore deve produrre gap invece di sommare massimi non datati come se fossero simultanei.
- Per prodotti finanziari esteri e piani pensionistici trattati come prodotto finanziario estero, l'IVAFE proporzionale usa aliquota e periodo/quote dichiarati nel rule pack.
- Per immobili esteri, l'IVIE usa valore dichiarato, quota e mesi di possesso; il mese e' contato se il possesso e' di almeno 15 giorni. La soglia di versamento, abitazione principale, detrazione per abitazione principale di lusso e credito per imposta patrimoniale estera sono applicati solo quando documentati dall'input e dal rule pack.

## Limiti

- Questa nota non produce una dichiarazione completa, non decide codici RW puntuali e non sostituisce revisione professionale.
- La qualificazione dei piani pensionistici esteri puo' dipendere da documenti contrattuali e trattamento fiscale specifico: senza classificazione documentata il motore deve produrre gap.
- Le soglie aggregate su piu' rapporti e intermediari richiedono input completo; il motore segnala incompletezza invece di ricostruire rapporti mancanti.
- Cripto-attivita', Paesi diversi da Spagna, attivita' d'impresa, trust e titolarita' effettiva complessa sono fuori dal primo perimetro.

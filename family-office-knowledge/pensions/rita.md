# RITA

La RITA, rendita integrativa temporanea anticipata, e' una prestazione della previdenza complementare che consente di erogare in forma frazionata il montante accumulato fino al conseguimento della pensione pubblica di vecchiaia, quando ricorrono requisiti specifici.

## Requisiti modellati in V2.7

Il rule pack V1 modella solo i requisiti minimi verificabili da input espliciti:

- cessazione o assenza dell'attivita' lavorativa;
- almeno 5 anni di partecipazione alla previdenza complementare;
- percorso ordinario: maturazione della pensione pubblica di vecchiaia entro 5 anni e almeno 20 anni di contribuzione nei regimi obbligatori;
- percorso per inoccupazione prolungata: inoccupazione superiore a 24 mesi e maturazione della pensione pubblica di vecchiaia entro 10 anni.

Il servizio produce un'opzione lorda semplice dividendo il montante complementare disponibile per la durata esplicita in mesi.

## Fuori perimetro

V2.7 non calcola:

- diritto alla pensione pubblica;
- importo della pensione pubblica;
- fiscalita' effettiva della RITA;
- costi, vincoli procedurali o finestre operative del singolo fondo;
- rendimento del montante durante l'erogazione;
- consulenza previdenziale, fiscale o legale.

Questi elementi devono restare `data_gaps`, limitazioni o input espliciti finche' non esistono rule pack e test dedicati.

## Collegamento rule pack

Regola calcolabile:

```text
family-office-rules/italy/current/rita.yaml
```

Il file e' JSON compatibile con YAML per evitare dipendenze parser aggiuntive nel runtime V1.

## Contratto documentale RITA stream v0.1

Il contratto revisionato riguarda l'Italia e il testo dell'art. 11 del D.Lgs.
252/2005 vigente dal 28-06-2026 al 31-12-2026, verificato il 18-10-2026.
Il GO e' limitato alla specifica documentale: non approva eligibility individuale,
rule pack, servizio, fiscalita', netto o integrazione nel retirement bridge.
Fonte: [Normattiva, art. 11, testo vigente](https://www.normattiva.it/atto/caricaDettaglioAtto?atto.articolo.numero=11&atto.codiceRedazionale=005G0278&atto.dataPubblicazioneGazzetta=2005-12-13&bloccoAggiornamentoBreadCrumb=true&classica=true&dataVigenza=09%2F09%2F2026&generaTabId=true&tipoDettaglio=singolavigenza&title=lbl.dettaglioAtto).

Un record `rita-fund-stream/v1` conserva separatamente eligibility solo se
attestata, domanda, accettazione, inizio e fine programmati, pagamenti effettivi,
montante richiesto, lordo e periodicita', stato fiscale, netto, fondo/issuer,
valuta, riferimenti alle fonti e coverage/as-of. Ogni fatto asserito richiede
evidenza, issuer e copertura; valori mancanti o confliggenti restano nulli o
unknown con `data_gaps`. I campi sono controlli software, non formati prescritti
dalla legge. Il netto richiede regole fiscali indipendenti e dati adeguati.

Domanda e cessazione non provano accettazione; accettazione, schedule e primo
accredito sono eventi distinti. Schedule assente o confliggente e importi solo
stimati non provano un flusso disponibile. `rita-options/v1` e' una opzione lorda
teorica, non una decisione del fondo o prova di pagamento. Le prestazioni del
comma 3-bis sono distinte e fuori da questo contratto. Le procedure e le prove
individuali restano di competenza del fondo.

### Intake tecnico V4.15b

`fo rita-stream` domanda quali dati il fondo ha confermato e salva la bozza e
lo snapshot nel workspace privato; `fo rita-stream --revise` permette di
rivedere una trascrizione. Ogni osservazione indica valore, file sorgente
relativo al workspace, issuer, intervallo di copertura e natura attestata o
stimata. L'operatore verifica la trascrizione: l'hash SHA-256 identifica il file
ma non certifica autore o contenuto. Date, importi e periodicita' sono validati
senza ricavare un calendario o importi; dati non attestati, non coperti o
confliggenti producono gap. Il tipo di prestazione deve essere attestato come
`rita`; `other` e' escluso. Il netto rimane non calcolato e non valutato.
La disponibilita' dello stream non e' accertata dal servizio.

## Fonti

- Decreto legislativo 5 dicembre 2005, n. 252, articolo 11, testo consolidato Normattiva: https://www.normattiva.it/eli/id/2005/12/13/005G0277/CONSOLIDATED
- Legge 27 dicembre 2017, n. 205, articolo 1 commi 168-169, testo consolidato Normattiva: https://www.normattiva.it/eli/id/2017/12/29/17G00222/CONSOLIDATED

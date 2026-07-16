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

## Fonti

- Decreto legislativo 5 dicembre 2005, n. 252, articolo 11, testo consolidato Normattiva: https://www.normattiva.it/eli/id/2005/12/13/005G0277/CONSOLIDATED
- Legge 27 dicembre 2017, n. 205, articolo 1 commi 168-169, testo consolidato Normattiva: https://www.normattiva.it/eli/id/2017/12/29/17G00222/CONSOLIDATED

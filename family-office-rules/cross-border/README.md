# Cross-Border

Regole tecniche per coordinamento cross-border, senza dati personali.

- `eu-pension-coordination-it-es.json` è il profilo storico v0.25/v4 e resta byte-identico.
- `eu-pension-coordination-it-es-v5.json` resta selezionabile come profilo storico.
- `eu-pension-coordination-it-es-v8.json` e' il default CLI coesistente: l'Art. 57(3) richiede tutte le istituzioni interessate sollevate come precondizione di validazione, senza determinare istituzione pagatrice, entitlement o pagamento. Annex VIII resta non disponibile e fail-closed.
- `eu-pension-coordination-it-es-v6.json` aggiunge il contratto source-bound Art. 87a(1): intervallo massimo `[2012-06-28, 2022-06-29)`, cessazione anticipata per cambio di situazione o opt-out e failure chiusa per fatti ignoti. Il corrigendum RO del 2015 riguarda solo Annex XI 2(c)(iii)(a), non l'art. 1(11) o l'art. 87a. Il ramo emette solo stato/provenance Title II e non determina Art. 57, diritto pensionistico, importi, riconoscimento, decorrenza o pagamento.
- I registry digest sono controlli tecnici di integrità del record, non prova di autenticità o sufficienza; non viene dichiarato alcun hash del contenuto ufficiale.
- Il corrigendum del 2026-07-22 è registrato solo come HR/SV con gap esplicito; non si applica a EN/IT/ES né agli artt. 93-94 senza evidenza ulteriore.

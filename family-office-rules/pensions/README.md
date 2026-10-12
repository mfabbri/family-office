# Regole pensionistiche e verifica delle fonti

I rule pack pensionistici attivi devono dichiarare per ogni fonte autorità, giurisdizione, atto/disposizioni o oggetto documentale, URL HTTPS ufficiale e `retrieved_on`. La freschezza della review è distinta dalla validità legale (`valid_from`/`valid_to`): la review non estende la validità normativa e non certifica il diritto individuale.

## Cadenza operativa

- Il ruolo responsabile è il maintainer normativo del repository. Riesaminare ogni fonte almeno ogni 90 giorni e subito dopo una modifica ufficiale potenzialmente rilevante; quest'ultimo trigger è un'attività umana, non un monitoraggio automatico.
- Dalla root del repository, eseguire `fo planning pension-sources audit`. Il comando non usa la rete e restituisce codice non-zero se provenance o review sono mancanti, incoerenti o scadute.
- Per aggiornare le date dopo aver consultato e valutato ciascuna fonte ufficiale, usare `fo planning pension-sources review`. Il wizard richiede conferma fonte per fonte; non apre, scarica o controlla i siti. Confermare la review solo dopo la verifica umana di URL, contenuto e disposizioni dichiarate. Una nuova review aggiorna solo `reviewed_on` e `next_review_due` (90 giorni dopo); non cambia il testo della regola né i periodi legali.
- Tutti i consumer pensionistici inclusi nel perimetro V4.14b rifiutano pack con provenance mancante o review overdue. Il perimetro audit attivo è dichiarato nel codice ed è limitato a cinque pack IT/ES/UE, incluso `italy/2026/inps-old-age-eligibility.json`; altri pack, ad esempio net pension/tax o contributivi, richiedono inclusione esplicita prima di essere considerati coperti.

L'audit è un controllo locale dei metadati, non monitoraggio normativo, parere legale, certificazione della fonte o decisione INPS/Seguridad Social. Output e decisioni individuali richiedono le fonti e la review umana appropriate.
## Pack eligibility italiana aggiunto

Il perimetro freshness attivo V4.14b comprende ora cinque pack, incluso `italy/2026/inps-old-age-eligibility.json`. Il nuovo pack serve soltanto allo screening deterministico di eligibility ordinaria FPLD/AGO per dipendenti, con requisiti maturati nel 2026-2028. Non calcola importi e non emette riconoscimento, decorrenza, pagamento, stream o data di uscita dal lavoro.

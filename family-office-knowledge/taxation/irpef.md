# IRPEF nazionale

## Perimetro IRPEF nazionale 2025-2026

Questa nota copre solo l'imposta lorda IRPEF nazionale per il 2025 e il 2026, calcolata su un imponibile gia' determinato. Non copre detrazioni, trattamento integrativo, addizionali regionali o comunali, crediti d'imposta, oneri deducibili/detraibili, acconti, sostituti d'imposta o compilazione della dichiarazione.

## Fonte normativa

- **2025 storico.** Fonte primaria: Legge 30 dicembre 2024, n. 207, art. 1 comma 2, pubblicata in Gazzetta Ufficiale n. 305 del 31 dicembre 2024. Per il periodo d'imposta 2025 gli scaglioni sono:
  - fino a 28.000 euro: 23%;
  - oltre 28.000 euro e fino a 50.000 euro: 35%;
  - oltre 50.000 euro: 43%.
- **2026.** Fonte primaria: Legge 30 dicembre 2025, n. 199, art. 1 comma 3, pubblicata in Gazzetta Ufficiale il 30 dicembre 2025. La disposizione sostituisce nell'art. 11, comma 1, lettera b), TUIR le parole "35 per cento" con "33 per cento". Verificata il 2026-10-11 presso la Gazzetta Ufficiale: https://www.gazzettaufficiale.it/atto/serie_generale/caricaArticoloDefault/originario?atto.codiceRedazionale=25G00212&atto.dataPubblicazioneGazzetta=2025-12-30&atto.tipoProvvedimento=LEGGE
  - fino a 28.000 euro: 23%;
  - oltre 28.000 euro e fino a 50.000 euro: 33%;
  - oltre 50.000 euro: 43%.

## Regola implementabile

I rule pack devono:

- applicare gli scaglioni del rispettivo periodo d'imposta in modo progressivo e contiguo;
- esporre `rule_id`, periodo di validita' e fonte;
- mantenere il pack 2025 storico separato dal pack 2026 aggiornato;
- produrre solo imposta lorda nazionale;
- dichiarare esplicitamente che la base imponibile deve essere fornita a monte;
- non stimare detrazioni o addizionali in assenza di rule pack dedicati.

## Avvertenze operative

La normativa fiscale puo' cambiare anche durante l'anno. Ogni modifica deve aggiornare prima questa nota, poi il rule pack, poi i test e infine l'integrazione engine. I risultati sono calcoli deterministici da regole versionate, non consulenza fiscale.

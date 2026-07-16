# IRPEF nazionale

## Perimetro V2.6

Questa nota copre solo l'imposta lorda IRPEF nazionale per il 2026, calcolata su un imponibile gia' determinato. Non copre detrazioni, trattamento integrativo, addizionali regionali o comunali, crediti d'imposta, oneri deducibili/detraibili, acconti, sostituti d'imposta o compilazione della dichiarazione.

## Fonte normativa

- Fonte primaria: Legge 30 dicembre 2024, n. 207, art. 1 comma 2, pubblicata in Gazzetta Ufficiale n. 305 del 31 dicembre 2024.
- La norma modifica l'art. 11 del DPR 22 dicembre 1986, n. 917, prevedendo per la determinazione dell'imposta lorda tre aliquote per scaglioni:
  - fino a 28.000 euro: 23%;
  - oltre 28.000 euro e fino a 50.000 euro: 35%;
  - oltre 50.000 euro: 43%.

## Regola implementabile

Il rule pack V2.6 deve:

- applicare gli scaglioni in modo progressivo e contiguo;
- esporre `rule_id`, periodo di validita' e fonte;
- produrre solo imposta lorda nazionale;
- dichiarare esplicitamente che la base imponibile deve essere fornita a monte;
- non stimare detrazioni o addizionali in assenza di rule pack dedicati.

## Avvertenze operative

La normativa fiscale puo' cambiare anche durante l'anno. Ogni modifica deve aggiornare prima questa nota, poi il rule pack, poi i test e infine l'integrazione engine. I risultati sono calcoli deterministici da regole versionate, non consulenza fiscale.

# Regime Impatriati

Il regime impatriati deve essere trattato come evento fiscale tracciabile, non come calcolo fiscale libero.

## Fonte normativa

- D.Lgs. 27 dicembre 2023, n. 209, art. 5, Gazzetta Ufficiale n. 301 del 28 dicembre 2023.

## Nuovo regime dal 2024

Per i soggetti che trasferiscono la residenza fiscale in Italia a decorrere dal periodo d'imposta 2024, l'art. 5 del D.Lgs. 209/2023 prevede, al ricorrere dei requisiti, la concorrenza al reddito complessivo del 50% dei redditi agevolabili, entro limite annuo di 600.000 euro. La percentuale puo' ridursi al 40% in presenza delle condizioni familiari previste dalla norma.

La durata ordinaria e' il periodo d'imposta del trasferimento e i quattro periodi d'imposta successivi. Per i trasferimenti anagrafici nel 2024 e con acquisto di abitazione principale entro i termini previsti, l'art. 5 prevede ulteriori tre periodi d'imposta.

## Regime previgente

L'art. 5, comma 9, del D.Lgs. 209/2023 fa salve le disposizioni previgenti per i soggetti che hanno trasferito la residenza anagrafica in Italia entro il 31 dicembre 2023. Per casi personali gia' in corso, la scadenza deve essere modellata come assunzione verificata nel workspace.

## Uso nel progetto

Per il caso MVP, il regime viene rappresentato come calendario di eventi fiscali fino al 2029. Lo snapshot degli eventi deve indicare:

- regime applicato;
- anni coperti;
- quota imponibile parametrica;
- fonte normativa;
- stato di validazione.

Il motore non deve usare LLM per calcolare imposte. Le simulazioni useranno solo regole deterministiche e parametri espliciti.

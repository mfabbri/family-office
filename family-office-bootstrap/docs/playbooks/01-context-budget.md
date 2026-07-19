# Context Budget

## Budget iniziale

Prima di ampliare l'analisi:

- massimo 2 listing di directory;
- massimo 3 ricerche testuali mirate;
- massimo 8 file letti integralmente;
- preferire `rg`/ricerca simboli e intervalli di righe a letture complete;
- non leggere roadmap non attive;
- non riversare log completi nel contesto se basta il riepilogo degli errori.

Il budget è una soglia di revisione, non un limite assoluto. Superarlo richiede una ragione concreta.

## Progressive disclosure

Ordine preferito:

1. file target o errore;
2. test direttamente collegato;
3. contratto/schema interessato;
4. chiamanti o dipendenze reali;
5. documentazione di roadmap, solo se il task è di roadmap;
6. decision log o long-term roadmap, solo per conflitti o decisioni architetturali.

## Compressione operativa

- Sintetizzare ogni esplorazione prima di aprire nuovi rami.
- Conservare file, simboli, decisioni e blocker; scartare output ripetitivo.
- Usare test mirati durante l'implementazione.
- Eseguire la suite completa una sola volta al gate appropriato, salvo fallimenti che richiedano iterazione.
- Evitare di rileggere file invariati nello stesso task.

## Stop condition

Se il task può essere completato e verificato con il contesto corrente, smettere di esplorare.

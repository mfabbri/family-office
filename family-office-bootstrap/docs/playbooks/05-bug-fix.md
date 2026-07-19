# Bug Fix

## Read first

1. errore o test fallito;
2. file target;
3. test diretto;
4. contratto solo se il comportamento atteso non è chiaro.

## Steps

1. Riprodurre con il test più piccolo possibile.
2. Distinguere bug applicativo, test fragile, ambiente o dato.
3. Correggere la causa minima.
4. Aggiungere/aggiornare una regression mirata.
5. Eseguire test del modulo.
6. Eseguire suite completa solo se il fix tocca contratto condiviso o comportamento trasversale.

Non aggiornare roadmap o decision log per una correzione locale priva di impatto progettuale.

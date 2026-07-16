# Pensione pubblica spagnola

## Ambito

Questa nota copre solo la pensione di jubilacion contributiva ordinaria del sistema spagnolo, come base per rule pack deterministici del family office.

Non copre:

- jubilacion anticipada;
- jubilacion demorada;
- complementi, massimali, minimi o integrazioni;
- fiscalita';
- coordinamento UE;
- rivalutazione o integrazione completa delle lagune contributive.

## Fonti primarie

- BOE, Real Decreto Legislativo 8/2015, texto refundido de la Ley General de la Seguridad Social, testo consolidato consultato il 2026-07-16.
- BOE, stesso testo consolidato, ultima actualizacion publicada il 2026-02-04, Articolo 210 e Disposizione transitoria nona per la percentuale maturata.

## Requisiti ordinari codificati nel baseline

L'articolo 205 richiede, per la pensione ordinaria nel Regimen General:

- eta' ordinaria di 67 anni, oppure 65 anni quando si accreditano 38 anni e 6 mesi di contribuzione;
- almeno 15 anni di contribuzione complessiva;
- almeno 2 anni compresi nei 15 anni immediatamente anteriori al fatto causante.

La disposizione transitoria settima applica gradualmente eta' e anni di contribuzione. Nel baseline sono codificati:

- anno 2026: 65 anni con almeno 38 anni e 3 mesi; altrimenti 66 anni e 10 mesi;
- dal 2027: 65 anni con almeno 38 anni e 6 mesi; altrimenti 67 anni.

## Base reguladora

La disposizione transitoria quadragesima introduce una progressione per la base reguladora dal 2026 al 2036 basata sulle migliori basi contributive entro una finestra mensile precedente il mese prima del fatto causante. Dal 2037 rinvia all'applicazione integrale dell'articolo 209.1.

Il baseline codifica la tabella 2026-2036 come parametri, ma non calcola ancora importi.

## Percentuale maturata

L'articolo 210 stabilisce che i primi 15 anni cotizzati danno diritto al 50% della base reguladora e che, oltre tale soglia, si applicano percentuali aggiuntive secondo regole progressive.

La Disposizione transitoria nona codifica la progressione applicabile:

- anni 2023-2026: per i mesi aggiuntivi 1-49 si aggiunge lo 0,21% per mese; per i 209 mesi successivi si aggiunge lo 0,19% per mese;
- dal 2027: per i mesi aggiuntivi 1-248 si aggiunge lo 0,19% per mese; per i 16 mesi successivi si aggiunge lo 0,18% per mese.

Il rule pack codifica queste percentuali come frazioni decimali mensili (`0.0021`, `0.0019`, `0.0018`) e applica un tetto massimo del 100%. Questa regola abilita il futuro estimatore a calcolare la percentuale maturata, ma non calcola ancora base reguladora, importo mensile, massimali, minimi o fiscalita'.

## Uso operativo

Questa nota alimenta `family-office-rules/spain/statutory-retirement-general.json`, rule pack tecnico non ufficiale. Il motore deve citare sempre fonte, schema, stato e limitazioni e deve bloccare i calcoli futuri quando una regola necessaria non e' ancora codificata.

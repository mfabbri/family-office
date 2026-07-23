# Coordinamento pensioni UE Italia-Spagna

## Ambito

Questa nota copre il coordinamento UE delle pensioni pubbliche di vecchiaia tra Italia e Spagna per il family office. Serve a distinguere:

- diritti nazionali autonomi;
- totalizzazione dei periodi ai soli fini del diritto;
- calcolo teorico e pro-rata quando applicabile;
- pagamenti separati da ciascuno Stato.

Non copre fiscalita', netto, domanda amministrativa, P1 ufficiale, ricorsi, pensioni private o complementari.

## Fonti primarie

Verifica fonti: 2026-07-23.

- Regolamento (CE) n. 883/2004, EUR-Lex, in particolare articoli 50, 51, 52 e 56.
- Your Europe, State pensions abroad, sezione su eligibility periods e calcolo pro-rata, ultima verifica indicata dalla fonte 2025-04-25.
- Seguridad Social, pensione contributiva di jubilacion ordinaria, requisiti 2026: 66 anni e 10 mesi con almeno 15 anni di contributi oppure 65 anni con almeno 38 anni e 3 mesi, in entrambi i casi con almeno 2 anni nel periodo specifico di riferimento.
- Seguridad Social, cuantia pensione di jubilacion, base reguladora: dal 2026 transizione tra metodo 300/350 e alternativa sulle migliori basi nel periodo transitorio.

## Regole operative

Ogni Paese resta competente per la propria legislazione e per la propria quota di prestazione. I contributi italiani e spagnoli non vengono trasferiti o fusi.

Quando il diritto nazionale richiede periodi minimi, l'istituzione competente deve considerare, se necessario, anche i periodi maturati negli altri Stati membri per verificare il diritto. Questa totalizzazione non trasforma i periodi esteri in contributi nazionali e non produce una pensione unica.

Per il calcolo, ogni istituzione determina secondo le proprie regole:

- l'eventuale beneficio indipendente, se il diritto e' maturato solo con periodi nazionali;
- il beneficio teorico come se tutti i periodi UE fossero stati maturati nella propria legislazione;
- il beneficio pro-rata, applicando al teorico il rapporto tra periodi nazionali e periodi totali UE;
- l'importo piu' favorevole tra beneficio indipendente e pro-rata, quando entrambi sono calcolabili.

Per la Spagna, nel perimetro ordinario 2026, il motore puo' valutare due
soglie di diritto distinte:

- diritto autonomo spagnolo, usando solo periodi spagnoli non sovrapposti;
- diritto per totalizzazione UE, usando periodi UE non sovrapposti ai soli fini
  del diritto, senza trasformare mesi italiani in basi spagnole.

Il requisito dei 2 anni nei 15 anni precedenti deve essere esposto
separatamente e ancorato a una data dichiarata nello scenario. Se mancano data
di nascita, periodi datati, completezza della cronologia INPS, scenario futuro
o anchor del requisito recente, il risultato deve restare bloccato o parziale
invece di dedurre mesi futuri.

L'importo teorico spagnolo non puo' essere inventato dal coordinamento UE:
deve provenire da una stima spagnola deterministica o da un input esplicito
con provenance. La quota pro-rata spagnola applica al teorico il rapporto tra
periodi spagnoli non sovrapposti e periodi UE totali non sovrapposti.

## Uso operativo

Il motore deve produrre un dossier che mantenga separate le prestazioni nazionali, dichiari i periodi usati per il coordinamento e blocchi il pro-rata quando mancano periodi normalizzati o importi teorici nazionali. Le stime interne non sostituiscono il documento P1 o le decisioni delle istituzioni competenti.

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

- Regolamento (CE) n. 883/2004, EUR-Lex, in particolare articoli 50, 51, 52, 56 e 57: https://eur-lex.europa.eu/eli/reg/2004/883/oj/eng.
- Regolamento (CE) n. 987/2009, EUR-Lex, in particolare articoli 12 e 13 per aggregazione, sovrapposizioni e conversione dei periodi, e articolo 43 per disposizioni aggiuntive di calcolo: https://eur-lex.europa.eu/eli/reg/2009/987/oj/eng.
- Your Europe, State pensions abroad, sezione su eligibility periods e calcolo pro-rata, ultima verifica indicata dalla fonte 2025-04-25.
- Seguridad Social, pensione contributiva di jubilacion ordinaria, requisiti 2026: 66 anni e 10 mesi con almeno 15 anni di contributi oppure 65 anni con almeno 38 anni e 3 mesi, in entrambi i casi con almeno 2 anni nel periodo specifico di riferimento.
- Seguridad Social, cuantia pensione di jubilacion, base reguladora: dal 2026 transizione tra metodo 300/350 e alternativa sulle migliori basi nel periodo transitorio.

## Regole operative

Ogni Paese resta competente per la propria legislazione e per la propria quota di prestazione. I contributi italiani e spagnoli non vengono trasferiti o fusi.

Quando necessario, i periodi assicurativi/residenziali degli altri Stati membri concorrono sia all'acquisizione del diritto sia al calcolo teorico/pro-rata, secondo la normativa applicabile. Non diventano basi contributive nazionali né producono una pensione unica. La precedente formulazione del rule pack `aggregation_for_entitlement_only` è quindi troppo restrittiva e va rimossa/corretta prima di qualsiasi uso eseguibile.

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

### Importo teorico spagnolo da periodi UE

Verifica fonti: 2026-07-24.

Nel calcolo pro-rata dell'articolo 52 del Regolamento (CE) n. 883/2004,
l'importo teorico e' la prestazione che l'interessato potrebbe chiedere se
tutti i periodi assicurativi maturati in altri Stati membri fossero stati
maturati sotto la legislazione applicata dall'istituzione competente alla data
di liquidazione.

Per la Spagna, la Seguridad Social espone una regola operativa specifica per
il caso in cui siano stati totalizzati periodi di altri Stati membri: la
prestazione teorica spagnola si determina sulle basi reali di contribuzione
della persona negli anni immediatamente anteriori all'ultima contribuzione alla
Seguridad Social spagnola; quando nella finestra di riferimento devono essere
computati periodi coperti sotto la legislazione di altri Stati membri, per quei
periodi si usa la base di contribuzione spagnola piu' vicina nel tempo,
aggiornata secondo l'indice dei prezzi al consumo (IPC). L'importo cosi'
ottenuto e' poi incrementato con le rivalutazioni delle pensioni della stessa
natura per gli anni successivi, se tali rivalutazioni sono codificate.

Per il perimetro family office, questa regola diventa eseguibile solo se:

- i periodi IT/ES datati sono espliciti e non fusi;
- le basi spagnole ufficiali sono disponibili dalla riconciliazione;
- l'IPC necessario e' versionato nel rule pack o dichiarato come gap;
- l'anno di pensionamento e' coperto dai parametri spagnoli applicabili;
- rivalutazioni successive non codificate restano escluse o diventano gap.

I mesi italiani nella finestra di base reguladora non diventano contributi
italiani usati come basi spagnole: servono solo a identificare mesi UE
totalizzati, valorizzati con una base spagnola reale vicina nel tempo e IPC
versionato.

## Uso operativo

Il motore deve produrre un dossier che mantenga separate le prestazioni nazionali, dichiari i periodi usati per il coordinamento e blocchi il pro-rata quando mancano periodi normalizzati o importi teorici nazionali. Le stime interne non sostituiscono il documento P1 o le decisioni delle istituzioni competenti.

## Periodi inferiori a un anno e sovrapposizioni

L'articolo 57 del Reg. 883/2004 consente di non erogare una quota per periodi sotto un anno soltanto quando ricorrono entrambe le condizioni: durata inferiore a un anno e nessun diritto acquisibile considerando quei soli periodi secondo la legislazione nazionale. Gli altri Stati devono comunque considerarli nel calcolo dell'importo teorico previsto dall'articolo 52(1)(b)(i); se l'esonero liberasse tutti gli Stati, l'articolo 57(3) assegna la prestazione secondo la regola dell'ultimo Stato le cui condizioni sono soddisfatte. Non codificare quindi una soglia autonoma e assoluta di 12 mesi.

L'articolo 56(1)(b) rinvia al regolamento di applicazione per le sovrapposizioni. Il Reg. 987/2009, articolo 12, prevede regole diverse per periodi obbligatori/volontari, periodi equivalenti, dati temporali non precisi e aggregazione senza doppio conteggio; l'articolo 13 disciplina la conversione tra unità. La deduplicazione uniforme per mese non sostituisce tali regole: quando natura o unità dei periodi non sono classificabili, il motore deve produrre un gap invece di scegliere arbitrariamente quale Stato prevale.

Fonti di coordinamento: [Reg. 883/2004](https://eur-lex.europa.eu/eli/reg/2004/883/oj/eng), [Reg. 987/2009](https://eur-lex.europa.eu/eli/reg/2009/987/oj/eng), [Seguridad Social, coordinamento UE per prestazioni di vecchiaia e superstiti](https://www.seg-social.es/wps/portal/wss/internet/InformacionUtil/32078/966/1819/1823).

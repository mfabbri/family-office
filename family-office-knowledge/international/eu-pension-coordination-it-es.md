# Coordinamento pensioni UE Italia-Spagna

## Ambito

Questa nota copre il coordinamento UE delle pensioni pubbliche di vecchiaia tra Italia e Spagna per il family office. Serve a distinguere:

- diritti nazionali autonomi;
- totalizzazione dei periodi ai soli fini del diritto;
- calcolo teorico e pro-rata quando applicabile;
- pagamenti separati da ciascuno Stato.

Non copre fiscalita', netto, domanda amministrativa, P1 ufficiale, ricorsi, pensioni private o complementari.

## Fonti primarie

Verifica fonti: 2026-10-15. Il controllo ha usato le versioni consolidate EUR-Lex disponibili a tale data; il testo consolidato è uno strumento documentale, mentre gli atti pubblicati nella Gazzetta ufficiale restano la fonte autentica.

- Regolamento (CE) n. 883/2004, EUR-Lex, testo consolidato corrente al 31-07-2019, in particolare articoli 50, 51, 52, 56 e 57 e Allegato VIII, parte 2: https://eur-lex.europa.eu/eli/reg/2004/883/2019-07-31/eng. EUR-Lex elenca modifiche del testo consolidato fino al Reg. (UE) 2019/1149; verificare gli atti autentici e gli eventuali accordi applicabili prima di un uso eseguibile.
- Regolamento (CE) n. 988/2009, atto modificativo che ha inserito l'art. 57(4) e l'eccezione per gli schemi dell'Allegato VIII, parte 2: https://eur-lex.europa.eu/eli/reg/2009/988/oj/eng.
- Regolamento (CE) n. 987/2009, EUR-Lex, testo consolidato corrente al 01-01-2018: articoli 12 e 13 per aggregazione, sovrapposizioni e conversione dei periodi; articolo 46(1) per le informazioni/documenti che il richiedente fornisce sui periodi esteri; articolo 47(7) per la comunicazione tra istituzioni quando risultano applicabili gli artt. 46(2) o 57(2)/(3) del regolamento di base. https://eur-lex.europa.eu/eli/reg/2009/987/2018-01-01/eng. La consolidazione pubblicata non sostituisce il controllo degli atti autentici e della loro vigenza.
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

In deroga all'art. 52(1)(b), l'art. 57(1) del Reg. 883/2004 consente all'istituzione di non essere tenuta a pagare la prestazione per i periodi rilevanti maturati sotto la legislazione che applica soltanto se ricorrono entrambe le condizioni: la durata aggregata dei periodi pertinenti è strettamente inferiore a un anno e, considerando soltanto tali periodi, non si acquisisce un diritto alla prestazione secondo quella legislazione. Esattamente un anno non soddisfa la prima condizione. La durata deve basarsi sulle unità riconosciute e sulle regole di aggregazione/conversione applicabili, non su un conteggio automatico di mesi di calendario. Non è dunque una soglia autonoma di 12 mesi applicata al totale UE.

L'art. 57(2) dispone che ciascuna istituzione competente di ogni Stato membro interessato consideri i periodi del paragrafo 1 ai fini dell'importo teorico dell'art. 52(1)(b)(i). Se l'applicazione del paragrafo 1 solleverebbe tutte le istituzioni interessate dai loro obblighi, l'art. 57(3) prevede in via residuale che la prestazione sia erogata esclusivamente secondo la legislazione dell'ultimo Stato membro le cui condizioni sono soddisfatte, come se tutti i periodi di assicurazione e residenza considerati ai sensi degli artt. 6 e 51(1)-(2) fossero stati compiuti sotto quella legislazione.

Il raccordo con l'art. 52 va mantenuto esplicito: il paragrafo 1 distingue prestazione indipendente nazionale (lett. a), importo teorico (lett. b, punto i) e importo pro-rata effettivo (lett. b, punto ii); il paragrafo 3 richiede il confronto e il pagamento dell'importo più elevato tra prestazione indipendente e pro-rata quando entrambi sono dovuti. Più precisamente, ai sensi del paragrafo 4 l'istituzione competente rinuncia al calcolo pro-rata solo se il calcolo nazionale indipendente produce invariabilmente un importo pari o superiore al pro-rata e ricorrono tutte le condizioni: (i) il caso è elencato nell'Allegato VIII, parte 1; (ii) non si applica una legislazione con regole anti-cumulo richiamate dagli artt. 54 e 55, salvo che siano soddisfatte le condizioni dell'art. 55(2); e (iii) l'art. 57 non è applicabile ai periodi maturati sotto la legislazione di un altro Stato nelle circostanze specifiche del caso. Il punto (ii) richiede quindi di identificare le regole nazionali anti-cumulo effettivamente applicabili e gli altri benefici/redditi pertinenti; l'eccezione dell'art. 55(2) riguarda il caso in cui la legislazione già calcoli una parte della prestazione tenendo conto di benefici diversi, altri redditi e altri elementi in funzione del rapporto di periodi dell'art. 52(1)(b)(ii). Art. 54 disciplina le sovrapposizioni di prestazioni della stessa natura e art. 55 quelle di natura diversa o con altri redditi. Nel consolidato EUR-Lex del Reg. 883/2004 al 31-07-2019, l'Allegato VIII, parte 1, contiene voci nazionali specifiche ma non voci per Italia o Spagna; la modifica della parte 1 del 2017/492 riguarda la voce polacca. Questo riscontro è limitato alla versione documentale e agli schemi ivi identificati: la classificazione di uno schema concreto e gli atti/allegati successivi vanno verificati prima di un uso eseguibile. La parte 2 dell'Allegato VIII riguarda un distinto regime di non applicazione del pro-rata ex art. 52(5); coerentemente, l'art. 57(4) rende l'art. 57 inapplicabile agli schemi elencati in tale parte. Nessuno di questi passaggi autorizza formule o redistribuzioni diverse da quelle previste dalle disposizioni.

L'art. 57(4), inserito dal Reg. 988/2009, rende l'articolo inapplicabile agli schemi elencati nell'Allegato VIII, parte 2. Nel testo consolidato EUR-Lex del Reg. 883/2004 al 31-07-2019, la parte 2 non riporta schemi spagnoli o italiani. Le categorie di pensioni spagnole del regime speciale dei funzionari e di pensioni italiane per inabilità totale al lavoro figurano invece nell'Allegato IX, parte II, relativo alle regole anti-cumulo dell'art. 54(2)(b): non sono eccezioni all'art. 57(4). Per i regimi IT/ES qui considerati, non applicare quindi l'esenzione dell'art. 57(4) sulla base di quelle voci dell'Allegato IX. Qualsiasi modifica futura degli allegati o schema diverso richiede un controllo aggiornato della fonte.

L'art. 57(1) definisce i periodi come tutti i periodi di assicurazione, lavoro dipendente, lavoro autonomo o residenza che danno diritto alla prestazione o la aumentano direttamente. La durata inferiore a un anno non è quindi una soglia assoluta sul totale UE né una semplice conta di mesi di calendario: richiede di identificare i periodi pertinenti sotto la legislazione applicata e di verificare il diritto autonomo secondo quella legislazione. Il paragrafo 3 è residuale e opera soltanto se, applicando il paragrafo 1, tutte le istituzioni interessate sarebbero sollevate dai loro obblighi; non è una regola ordinaria di attribuzione.


Il Reg. 987/2009, art. 46(1), richiede al richiedente le informazioni e i documenti disponibili pertinenti sui periodi sotto altre legislazioni (istituzioni e identificativi assicurativi, datori di lavoro, natura/luogo del lavoro autonomo, indirizzi di residenza e durata), oltre ai documenti richiesti dalla legislazione nazionale applicabile. L'art. 47(7) del medesimo regolamento di applicazione disciplina invece la comunicazione tra istituzioni: quando, sulla base delle informazioni di cui all'art. 47(4)-(5), un'istituzione stabilisce che si applica l'art. 46(2) oppure l'art. 57(2)/(3) del Reg. 883/2004 (regolamento di base), informa l'istituzione di contatto e le altre istituzioni interessate. La comunicazione inter-istituzionale non è la prova che deve fornire il richiedente e non determina una data di riconoscimento, decorrenza economica o primo pagamento.

### Applicabilità temporale e periodi anteriori al 2010

Le date di consolidamento EUR-Lex identificano la versione documentale del testo, non la data dalla quale una disposizione si applica a ogni periodo. Il Reg. 883/2004 si applica dal 1 maggio 2010 secondo l'art. 91. L'art. 87(1) esclude l'acquisizione, in base al regolamento, di diritti per il periodo anteriore alla sua data di applicazione; il paragrafo 2 dispone però che i periodi assicurativi e, se pertinenti, di lavoro o residenza maturati prima siano presi in considerazione per determinare i diritti acquisiti sotto il regolamento. Gli artt. 93-94 del Reg. 987/2009 richiamano tale regime transitorio. In particolare, l'art. 94(1) riguarda l'evento assicurato anteriore alla data di applicazione del regolamento di esecuzione nello Stato interessato quando la domanda pensionistica non era stata ancora liquidata prima di tale data; prevede la distinta valutazione secondo la disciplina precedente per il periodo anteriore e il regolamento di base per quello successivo, e conserva l'importo precedente se superiore al calcolo secondo il regolamento di base. Gli eventi anteriori al 1 maggio 2010 richiedono quindi un'analisi transitoria separata e review umana; non si proietta automaticamente su di essi la regola corrente dell'art. 57.

L'articolo 56(1)(b) rinvia al regolamento di applicazione per le sovrapposizioni. Il Reg. 987/2009, articolo 12, prevede regole diverse per periodi obbligatori/volontari, periodi equivalenti, dati temporali non precisi e aggregazione senza doppio conteggio; l'articolo 13 disciplina la conversione tra unità. La deduplicazione uniforme per mese non sostituisce tali regole: quando natura o unità dei periodi non sono classificabili, il motore deve produrre un gap invece di scegliere arbitrariamente quale Stato prevale.

Prima di un uso eseguibile occorre documentare almeno: schema e prestazione nazionali esatti per ciascuno Stato; periodi esteri con date/durate, categoria e unità riconoscibile; prova necessaria per valutare il diritto considerando soltanto i periodi di quello Stato; applicabilità dell'Allegato VIII, parti 1 e 2; regole nazionali anti-cumulo eventualmente applicabili, benefici/redditi concorrenti e fatti per verificare l'eccezione dell'art. 55(2); applicabilità dell'art. 57; istituzioni interessate e comunicazioni/decisioni rilevanti. Le fonti qui elencate non definiscono da sole come normalizzare ogni unità nazionale né risolvono l'applicazione individuale delle disposizioni anti-cumulo e delle voci degli Allegati: i casi non dimostrati restano `data_gaps` e non possono alimentare un calcolo eseguibile.

Fonti di coordinamento: [Reg. 883/2004, testo consolidato 31-07-2019](https://eur-lex.europa.eu/eli/reg/2004/883/2019-07-31/eng), [Reg. 988/2009](https://eur-lex.europa.eu/eli/reg/2009/988/oj/eng), [Reg. (UE) 2017/492, modifica degli Allegati incluso Allegato VIII, parte 1](https://eur-lex.europa.eu/eli/reg/2017/492/oj/eng), [Reg. 987/2009, testo consolidato 01-01-2018](https://eur-lex.europa.eu/eli/reg/2009/987/2018-01-01/eng), [Reg. 987/2009, Gazzetta ufficiale, artt. 46-47 e 93-94](https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX%3A32009R0987), [Seguridad Social, coordinamento UE per prestazioni di vecchiaia e superstiti](https://www.seg-social.es/wps/portal/wss/internet/InformacionUtil/32078/966/1819/1823).

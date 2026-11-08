# Pensione pubblica spagnola

## Ambito

Questa nota copre esclusivamente la pensione di jubilacion contributiva ordinaria del Régimen General, come base per rule pack deterministici del family office. I richiami a RETA servono soltanto a citare correttamente eccezioni e regole di fonte: sono esempi fuori scope e non sono valutati.

Non copre:

- jubilacion anticipada;
- jubilacion demorada;
- jubilacion parcial, activa e flexible (fuori scope; partial esclusa dal RD 453/2022 art. 2; active ricade in LGSS art. 214 e RD art. 3.3; flexible e altri percorsi speciali non sono valutati);
- RETA e ogni altro regime o sistema speciale, inclusi i relativi percorsi;
- complementi, massimali, minimi o integrazioni;
- fiscalita';
- coordinamento UE;
- rivalutazione o integrazione completa delle lagune contributive.

## Fonti normative ufficiali e guida amministrativa

### Pubblicazioni ufficiali BOE (fonti normative primarie)

- BOE, Real Decreto Legislativo 8/2015, **pubblicazione ufficiale primaria**: https://www.boe.es/boe/dias/2015/10/31/pdfs/BOE-A-2015-11724.pdf.
- BOE, Real Decreto 453/2022, **pubblicazione ufficiale primaria**: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2022-9850.

### Testi consolidati BOE (consultazione informativa; senza valore legale autonomo)

I link seguenti sono **solo consultazioni informative e non hanno valore legale autonomo**; devono essere verificati contro la pubblicazione ufficiale primaria, gli atti modificativi e le rispettive decorrenze.


- BOE, Real Decreto Legislativo 8/2015, texto refundido de la Ley General de la Seguridad Social, testo consolidato consultato il 2026-11-08 (consolidato aggiornato al 2026-10-21): https://www.boe.es/buscar/act.php?id=BOE-A-2015-11724. Il testo consolidato BOE è strumento informativo; la fonte legale è la pubblicazione ufficiale, da verificare insieme all'atto modificativo ufficiale e alla sua decorrenza.
- BOE, Real Decreto 453/2022, artt. 1-4 e disposizione transitoria unica, testo consolidato consultato il 2026-11-08: https://www.boe.es/eli/es/rd/2022/06/14/453.
- BOE, Real Decreto 84/1996, art. 46.4(c), testo consolidato consultato il 2026-11-08: https://www.boe.es/eli/es/rd/1996/01/26/84/con.
- BOE, LGSS artt. 205 e 210 e disposizioni transitorie settima, nona e quadragesima; per la soglia ordinaria 2026 la DT settima indica 65 anni con almeno 38 anni e 3 mesi, altrimenti 66 anni e 10 mesi. La stessa tabella fissa dal 2027 65 anni con almeno 38 anni e 6 mesi, altrimenti 67 anni.

### Guida amministrativa Seguridad Social

- Seguridad Social, requisiti minimi di contribuzione e fatto causante/effetti economici, consultati il 2026-11-08: https://www.seg-social.es/wps/portal/wss/internet/Trabajadores/PrestacionesPensionesTrabajadores/10963/28393/28396/28472/177422 e https://www.seg-social.es/wps/portal/wss/internet/InformacionUtil/44539/45370?changeLanguage=es. È guida amministrativa e non fonte statutaria.
- Seguridad Social, Gestion/Pago, Devengo/Abono, consultato il 2026-07-16, per periodicita' di pagamento delle pensioni ordinarie. È guida amministrativa e non fonte statutaria.

## Limite di validità operativa

La verifica corrente della LGSS non trasforma una regola con decorrenza futura in un'autorizzazione a estrapolare oltre il suo periodo esplicitamente codificato. Ogni rule pack deve dichiarare la finestra normativa effettivamente riesaminata; il consolidato BOE va ricontrollato insieme agli atti modificativi e alle rispettive date di efficacia. Il requisito specifico dei 2 anni nei 15 precedenti necessita dell'anchor del fatto causante, salvo il ramo di alta o assimilada senza obbligo di cotizzazione, che usa la cessazione dell'obbligo; richiede inoltre lo stato di assicurazione/assimilazione. Senza questi dati l'esito è un gap, anche quando età e contribuzione totale risultano sufficienti.

Il calendario di pagamento o il numero di mensilità non prova la data di riconoscimento, la decorrenza economica o il primo accredito. Questi eventi restano separati e non derivabili da questa nota.

## Matrice source-bound V4.14b-g (non eseguibile)

Consultazione documentale: 2026-11-08. I link BOE nelle righe sono testi consolidati per consultazione informativa, senza valore legale autonomo; le pubblicazioni ufficiali primarie sono indicate nella sezione fonti. La matrice descrive il contratto documentale per una futura verifica umana; non produce una data pensionistica, non sceglie un percorso e non autorizza Rules, Tests o Engine.

**Etichetta di riga BOE:** in ogni riga che contiene un link `boe.es` il link è un **testo consolidato BOE — consultazione informativa, senza valore legale autonomo**; il corrispondente record di pubblicazione ufficiale primaria è quello indicato nella sottosezione dedicata. I link `seg-social.es` sono **guida amministrativa**, non fonte statutaria.

| Oggetto | Fonte/link con ruolo esplicito (pubblicazione ufficiale, consolidato informativo o guida amministrativa) e contenuto osservato | Evidenza richiesta / limite operativo |
| --- | --- | --- |
| LGSS 205.1(a) | [BOE, LGSS art. 205](https://www.boe.es/buscar/act.php?id=BOE-A-2015-11724): ramo età ordinaria; 67 anni oppure 65 con 38 anni e 6 mesi. Il computo richiede anni e mesi completi e non equipara le frazioni. | Record ufficiale dell'età alla data candidata e contribuzione qualificata come anni/mesi completi. Non convertire automaticamente giorni in anni o usare qui la soglia del ramo 205.1(b). |
| LGSS 205.1(b) | [BOE, LGSS art. 205](https://www.boe.es/buscar/act.php?id=BOE-A-2015-11724): requisito generico di 15 anni e requisito specifico di almeno 2 anni nei 15 immediatamente precedenti il momento in cui si causa il diritto. Per l'accesso alla pensione da alta/assimilada senza obbligo di cotizzare, la finestra specifica di 15 anni si ancora alla data di cessazione dell obbligo. Non si computa la quota proporzionale delle paghe extra. | Prova istituzionale di contribuzioni, status e obbligo/cessazione; mantenere separati gli anchor del requisito generico, del requisito 2-su-15 e del fatto causante. Non inferire un anchor ignoto; `unknown` + `data_gaps` e revisione umana. |
| DT7: transizione dell'età | [BOE, LGSS DT7](https://www.boe.es/buscar/act.php?id=BOE-A-2015-11724): 2026, 65 anni con almeno 38 anni e 3 mesi, altrimenti 66 anni e 10 mesi; dal 2027, 65 anni con almeno 38 anni e 6 mesi, altrimenti 67 anni. | Intervalli espliciti della tabella: non interpolare o estrapolare oltre gli intervalli dichiarati. Una data fuori intervallo richiede nuova verifica del consolidato e dell'atto modificativo applicabile. |
| Status e obbligo assicurativo | [BOE, LGSS artt. 165–166](https://www.boe.es/buscar/act.php?id=BOE-A-2015-11724): regola generale di affiliazione e alta o situazione assimilata, con eccezioni espresse. [BOE, LGSS art. 205.3](https://www.boe.es/buscar/act.php?id=BOE-A-2015-11724): la jubilación può essere causata anche senza alta/asimilada se sono soddisfatti età e contribuzione. | Provare stato esatto alla data candidata, cessazione o altra condizione prevista e ogni eventuale obbligo di cotizzazione. `non_alta` non è sinonimo di fallimento, ma neppure di idoneità: resta status-dependent e richiede review umana. |
| Hecho causante e vie di accesso | [RD 453/2022 artt. 2-3](https://www.boe.es/eli/es/rd/2022/06/14/453/con): art. 3.1, regola generale: data indicata nella domanda, se i requisiti sono soddisfatti, entro 3 mesi prima/dopo la domanda o il giorno stesso; domanda all estero presentata in base a norma internazionale segue il termine previsto dalla legge del paese. Art. 3.2(a): per l alta, il giorno della baja coincidente con la cessazione del lavoro/attività; i richiami fuori scope a religiosi cattolici in RETA e a lavoratori agrari del RG in inattività mantengono la data della baja; nel caso di baja tardiva o d ufficio RETA previsto da RD 84/1996 art. 46.4(c), ultimo giorno del mese naturale della cessazione. (b) trasferimento all estero al servizio di impresa spagnola, data di cessazione; (c) excedencia forzosa per incarico pubblico, fine incarico; (d) estinzione per perdita della condizione dei convenios especiales per deputati e senatori delle Cortes Generales, membri dei parlamenti o governi delle comunità autonome, e spagnoli funzionari o dipendenti di organizzazioni internazionali intergovernative, data di estinzione; (e) fine sussidio/prestazione di disoccupazione per raggiunta età ordinaria, data di compimento dell età. Per 3.2 la domanda è ammessa fino a 3 mesi prima o successivamente, con gli effetti dell art. 4. Art. 3.3: lavoro mantenuto senza interruzione secondo LGSS 214 (jubilacion activa), domanda nei 3 mesi immediatamente precedenti; fuori scope. La disposizione transitoria unica impedisce, dal 16-06-2022, una data scelta anteriore all entrata in vigore, salvo le vie art. 3.2. | Nessun candidato viene promosso a hecho causante senza prova della via, stato, evento, domanda e requisiti. RD 453/2022 esclude la jubilacion parcial (art. 2). Un ipotetico calendario non è domanda o evento legale. Applicabilità e date incerte diventano `data_gaps` + revisione umana. |
| Riconoscimento, effetti economici, pagamento | [RD 453/2022 artt. 3-4](https://www.boe.es/eli/es/rd/2022/06/14/453/con) e [Seguridad Social, fatto causante ed effetti](https://www.seg-social.es/wps/portal/wss/internet/InformacionUtil/44539/45370?changeLanguage=es): come regola, gli effetti economici decorrono dal giorno successivo al hecho causante. Se, nei rami art. 3.2, la domanda è oltre i tre mesi successivi, decorrono al massimo dai tre mesi anteriori alla domanda. Per 3.2(e), la domanda entro tre mesi dalla risoluzione definitiva di estinzione retroagisce alla data di effetto dell estinzione; altrimenti la retroattività massima è di tre mesi dalla domanda. Resta il caveat dell invito al pagamento LGSS art. 47.1. Il pagamento effettivo resta un evento separato da provare. | Conservare `eligibility_predicate`, `hecho_causante`, `recognition`, `economic_effect` e `payment` come eventi distinti, ciascuno con propria fonte. Nessuno è derivato dagli altri senza prova specifica. |
| Prova actual vs hypothetical | Le norme richiedono requisiti riferiti a una persona e a una data; la guida amministrativa indica domanda e documentazione. | `actual_evidence`: estratto contributivo, stato/cessazione, domanda e atti ufficiali. `hypothetical_evidence`: simulazione o assunzione di cessazione/data futura; non prova eleggibilità né hecho causante. Incertezza su fonte, stato, periodo o data diventa `data_gaps` e richiede human review. |
| Giorni, anni e unita amministrative | **Guida amministrativa Seguridad Social, periodo minimo** (https://www.seg-social.es/wps/portal/wss/internet/Trabajadores/PrestacionesPensionesTrabajadores/10963/28393/28396/28472/177422): per il periodo generico indica 15 anni = 5.475 giorni dal 25-05-2010. Separatamente, per la soglia anagrafica indica giorni computabili convertiti in anni da 365 giorni e mesi da 30,41666 giorni, contando solo anni/mesi completi e i giorni accreditati secondo le norme citate dalla guida. Questi conteggi e conversioni sono indicazioni amministrative, non testo di legge. | La conversione per l eta non si trasferisce automaticamente a 15 anni generici ne al requisito specifico 2-su-15. Non assumere che il requisito 2-su-15 equivalga a 730 giorni senza specifica base giuridica e temporale. Confini 5.474/5.475, periodi sovrapposti, assimilati, part-time e fijo discontinuo restano source-bound; incertezza -> `unknown` + `data_gaps` + review umana. |
| UE: confine v8 non valutato | [Reg. 883/2004](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02004R0883-20190731), artt. 51/57/87 e Annex VIII; [Reg. 988/2009](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32009R0988); [Reg. 987/2009](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02009R0987-20180101), artt. 93-97. Il contratto v8 richiede di distinguere la transizione applicabile dal 01-05-2010 e per ogni Stato/regime/prestazione verificare la versione ufficiale e l inclusione nello specifico Annex VIII Part II ai fini dell art. 57(4). | Questa nota non classifica periodi esteri o schemi nazionali e non decide Art. 57, totalizzazione o pro-rata. Senza prova scheme-specific versioned di Annex VIII Part II: `not_assessed` + `data_gaps`; currentness locale verificata solo fino al 01-11-2026 incluso, dal 02-11-2026 gap. Non inferire inclusion/exclusion o effetto nazionale. |

### Stato della fonte e guardrail software

- **Statuto/norma:** LGSS e RD 453/2022 fissano requisiti, transizione, date ed effetti; il testo consolidato BOE è informativo e va riconciliato con la pubblicazione ufficiale e la decorrenza dell'atto modificativo.
- **Guida amministrativa:** la pagina Seguridad Social descrive domanda, INSS/ISM e indicazioni operative; non sostituisce la norma e non estende il suo intervallo.
- **Guardrail software v5, solo documentale e non eseguibile:** `as_of_date` è il cutoff della valutazione; separare sempre `actual_evidence` da `hypothetical_evidence` e imporre `actual.search_upper_bound <= as_of_date`. In una ricerca dichiarata completa, ogni data candidata deve ricadere nella validità dichiarata del rule pack applicabile; una data oltre la validità conosciuta è ammessa solo in modalità `hypothetical`, con assunzione di continuità esplicita e versionata e copertura dello scenario. Per ogni famiglia di evidenze, la copertura deve essere continua per tutto l intervallo cercato e fino al cutoff. Distinguere `no_candidate_in_complete_range` (nessun candidato dopo una ricerca completa dell intervallo) da `no_candidate_in_complete_scenario` (nessun candidato nello scenario completo); entrambi conservano i rispettivi `data_gaps`. Un intervallo, scenario, famiglia o cutoff non dimostrato è `unknown` e richiede `data_gaps` + revisione umana; non autorizza inferenze. `source_ref`, `consulted_at`, `as_of_date`, `status`, `evidence_kind`, `data_gaps` e `human_review_required` sono metadati di controllo, non valori legali. Restare fail-closed quando manca una prova o la fonte non qualifica il conteggio.

### Trace locale Annex VIII Part II (evidence-only)

La riproduzione locale del confine v8 usa esclusivamente questi artefatti di evidenza, senza inferire applicabilità di schemi nazionali o runtime:

- `family-office-knowledge/international/eu-annex-viii-applicability-evidence-v0.2.json`: `contract_id` `eu-annex-viii-part-2-applicability-evidence-v0.2`; `currentness_chain.chain_source_id` `annex-viii-part-2-currentness-chain-through-2026-11-01`; `verified_through` `2026-11-01`; `part_ii_status` `unchanged_through_2026-11-01_inclusive`.
- `family-office-knowledge/international/eu-annex-viii-part-2-catalogue-v0.4.json`: `catalogue_id` `eu-annex-viii-part-2-source-ledger-v0.4`; `status` `source_ledger_only`; `snapshot_as_of` `2019-07-31`; `reviewed_on` `2026-11-07`; `entries_sha256` `ACCCEEDD7FC47CB1570BE5E15C6C846BA72F5F7DE7C52A01415D5BC6E3DD5EB9`.

Il supporto documentato è esattamente l'intervallo half-open `[2019-08-01, 2026-11-02)`, con gap a partire dal `2026-11-02`. Gli artefatti sono source evidence e non dimostrano applicabilità a uno schema nazionale concreto né autorizzano Rules, Tests, Engine o runtime.

Unknowns minimi: regime/gestione, stato alta-assimilata-non alta, cessazione e obbligo contributivo, data e via del hecho causante, anni/mesi/giorni e qualificazione, domanda/riconoscimento, effetti economici/pagamento, periodi UE e currentness oltre il 2026-11-01.

## Requisiti ordinari codificati nel baseline

L'articolo 205 richiede, per la pensione ordinaria nel Régimen General:

- eta' ordinaria di 67 anni, oppure 65 anni quando si accreditano 38 anni e 6 mesi di contribuzione;
- almeno 15 anni di contribuzione complessiva;
- almeno 2 anni compresi nei 15 anni immediatamente anteriori al fatto causante; per l'accesso alla pensione da alta/assimilada senza obbligo di cotizzare, i 15 anni si ancorano alla cessazione dell obbligo di cotizzare, non automaticamente al fatto causante.

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

## Periodicita' di pagamento

Le pensioni ordinarie del Régimen General sono corrisposte in 14 paghe annue: dodici mensilita' ordinarie e due paghe straordinarie nei mesi di giugno e novembre. Le pensioni derivanti da infortunio sul lavoro o malattia professionale seguono una periodicita' diversa e restano fuori dal baseline di pensione ordinaria.

## Uso operativo

Questa nota alimenta `family-office-rules/spain/statutory-retirement-general.json`, rule pack tecnico non ufficiale. Il motore deve citare sempre fonte, schema, stato e limitazioni e deve bloccare i calcoli futuri quando una regola necessaria non e' ancora codificata.

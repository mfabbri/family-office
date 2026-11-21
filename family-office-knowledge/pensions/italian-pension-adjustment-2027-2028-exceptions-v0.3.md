# Adeguamento pensionistico italiano 2027-2028: mappatura fonti e percorsi v0.3

**Stato:** candidato Knowledge in attesa di review normativa exact-hash  
**Verifica fonti:** 2026-11-21  
**Giurisdizione e periodo:** Italia; adeguamenti applicabili nel 2027-2028  
**Perimetro:** mappa source-bound per il requisito anagrafico della pensione di vecchiaia ex art. 24, comma 6, D.L. 201/2011. Non e' una regola eseguibile e non determina posizioni individuali.

## Fonti e gerarchia

| Riferimento | Fonte e ruolo | Pubblicazione / efficacia | Uso nel perimetro |
|---|---|---|---|
| Legge 199/2025, art. 1, commi 185-190 | [Pubblicazione originale in Gazzetta Ufficiale](https://www.gazzettaufficiale.it/eli/id/2025/12/30/25G00212/SG); legislazione primaria | Pubblicata il 30-12-2025. La nota ufficiale indica che i commi 185-190 entrano in vigore il 30-12-2025. | Fonte primaria per aumento generale, eccezioni, esclusioni e percorsi distinti. |
| INPS, Circolare 28/2026, 16-03-2026 | [Testo ufficiale INPS](https://www.inps.it/it/it/inps-comunica/atti/circolari-messaggi-e-normativa/dettaglio.circolari-e-messaggi.2026.03.circolare-numero-28-del-16-03-2026_15199.html); prassi amministrativa | Pubblicata il 16-03-2026; indica gli adeguamenti amministrativi per il 2027-2028. | Riscontro dei requisiti generali e degli importi/soglie coperti dalla circolare; non sostituisce la legge. |
| D.L. 201/2011, art. 24, comma 6 | Pubblicazione primaria e conversione, con consultazione consolidata separata | Norma originaria 2011, modificata da atti successivi. | Identifica il requisito anagrafico ordinario di vecchiaia richiamato dal comma 186. |
| Legge 205/2017, art. 1, Allegato B | [Pubblicazione originale in Gazzetta Ufficiale](https://www.gazzettaufficiale.it/eli/id/2017/12/29/17G00222/SG); legislazione primaria | Pubblicata il 29-12-2017; in vigore dal 01-01-2018. | L'Allegato B e' richiamato dal comma 187(a); nessuna classificazione individuale e' effettuata. |
| D.Lgs. 67/2011, art. 1 | [Pubblicazione originale in Gazzetta Ufficiale](https://www.gazzettaufficiale.it/eli/id/2011/05/11/11G0111/SG); legislazione primaria | Pubblicato il 11-05-2011; in vigore dal 26-05-2011. | L'art. 1, commi 1-3 e 4, e' richiamato dai commi 187(b) e 189; i percorsi restano fuori dall'implementazione corrente. |

La pubblicazione originale della legge e' la fonte primaria. Le pagine Normattiva consolidate e le indicazioni INPS sono consultazioni ufficiali o prassi amministrativa, non sostituti della pubblicazione legislativa. La Circolare INPS 28/2026 espone la propria tabella amministrativa per il 2027-2028: 66 anni e 7 mesi per attivita' gravosa svolta sette anni negli ultimi dieci; 67 anni per attivita' gravosa svolta sei anni negli ultimi sette; 66 anni e 7 mesi per attivita' faticosa e pesante con i periodi indicati nella circolare. Per tutti i rami la tabella riporta almeno 30 anni di contribuzione.

## Mappatura normativa da tenere distinta

| Disposizione | Contenuto rilevante per la mappa | Rapporto con il servizio attuale | Stato |
|---|---|---|---|
| Art. 1, comma 185, Legge 199/2025 | Aumento generale dei requisiti di accesso: un mese nel 2027 e tre mesi nel 2028. | Costituisce lo schedule generale v3 per il requisito anagrafico ordinario; l'INPS ne fornisce riscontro amministrativo. | Fonte primaria individuata; periodi e citazione devono essere modellati nel Rules candidato. |
| Commi 186-187 | L'aumento del comma 185 non si applica, tra gli altri requisiti, al requisito anagrafico per la vecchiaia richiamato dall'art. 24, comma 6, se ricorrono condizioni di categoria, attivita' e contribuzione del comma 187. | E' il solo perimetro di eta' ordinaria considerato per un futuro contratto Rules. La prova dei requisiti non e' un booleano inferibile dall'occupazione dichiarata. | Richiede determinazione esterna e prove source-bound; nessuna classificazione individuale in Knowledge/Rules. |
| Comma 187, lettera a | Professioni dell'Allegato B alla legge 205/2017; attivita' svolta al pensionamento per almeno sette anni negli ultimi dieci o sei negli ultimi sette; attivita' particolarmente difficoltosa e rischiosa se continua; anzianita' contributiva minima di 30 anni. | Condizioni da rappresentare come requisiti probatori separati, non come stima dell'Engine. | Verifica individuale e classificazione amministrativa restano gap. |
| Comma 187, lettera b | Mansioni gravose/usuranti indicate dall'art. 1, comma 1, lettere a-d, D.Lgs. 67/2011; condizioni dei commi 2 e 3 dello stesso articolo; almeno 30 anni di contribuzione. | Il servizio attuale non verifica la storia delle mansioni ne' i requisiti speciali del D.Lgs. 67/2011. | Percorso non classificato dal servizio; resta gap. |
| Comma 190 | L'esclusione del comma 186 non si applica a chi, al momento del pensionamento, gode dell'APE Sociale. | E' un elemento temporale separato, riferito al momento del pensionamento; una categoria professionale non ne prova l'assenza. | Prova individuale APE Sociale non disponibile; resta gap fino a un flusso di evidenza approvato. |
| Comma 188 | L'aumento del comma 185 non si applica al requisito contributivo ridotto per i lavoratori precoci indicati dall'art. 1, comma 199, limitatamente alla lettera d). | E' un requisito contributivo di un percorso anticipato, non la soglia anagrafica ordinaria del servizio. | Fuori perimetro; non mappato come percorso di vecchiaia. |
| Comma 189 | Modifica il riferimento temporale nell'art. 1, comma 4, D.Lgs. 67/2011 aggiungendo il 2027 agli anni indicati. | E' un intervento distinto sulle disposizioni richiamate per mansioni usuranti; non e' assunto come estensione automatica del percorso ordinario. | Fuori perimetro corrente; resta gap per eventuale percorso dedicato. |

## Distinzione amministrativa dei requisiti anagrafici

| Ramo della tabella INPS 2027-2028 | Prova/condizione da attestare esternamente | Requisito anagrafico riportato dalla Circolare 28/2026 | Fonte del requisito amministrativo |
|---|---|---|---|
| Professioni gravose, sette anni negli ultimi dieci | Professione Allegato B, attivita' gravosa, periodo, almeno 30 anni contributivi | 66 anni e 7 mesi | Circolare INPS 28/2026, tabella vecchiaia 2027-2028 |
| Professioni gravose, sei anni negli ultimi sette | Professione Allegato B, attivita' gravosa, periodo, almeno 30 anni contributivi | 67 anni | Circolare INPS 28/2026, tabella vecchiaia 2027-2028 |
| Lavori faticosi e pesanti | Categorie e condizioni D.Lgs. 67/2011; 7 anni negli ultimi 10 e attivita' per almeno meta' della vita lavorativa complessiva; almeno 30 anni contributivi | 66 anni e 7 mesi | Circolare INPS 28/2026, tabella vecchiaia 2027-2028 |

Questi valori sono la rappresentazione della tabella amministrativa INPS, non una determinazione del diritto individuale e non una sostituzione del testo legislativo. Le prove di categoria, storia lavorativa, contribuzione e status APE Sociale restano esterne; qualunque dato mancante o confliggente resta `not_assessed + data_gaps`.

## Confine di percorso e non-inferenza

- La mappa del comma 186 riguarda espressamente il requisito anagrafico di cui all'art. 24, comma 6. Non estende automaticamente l'eccezione al percorso contributivo alternativo dell'art. 24, comma 7, ne' alla soglia d'importo ad esso associata.
- Il riferimento del comma 186 anche al requisito contributivo dell'art. 24, comma 10, riguarda la pensione anticipata; tale percorso non e' implementato nel servizio di vecchiaia qui trattato.
- Il servizio corrente ha ambito FPLD dipendenti. La norma richiama un insieme piu' ampio di gestioni e profili: l'ambito ristretto del servizio non prova ne' nega la qualificazione per i soggetti esclusi dal suo scope.
- La conferma amministrativa di una condizione, il periodo di attivita', il requisito contributivo e lo stato APE Sociale al momento rilevante richiedono prove distinte. L'assenza di una prova non significa che la condizione sia assente.
- Il valore della soglia dell'assegno sociale 2027-2028 non e' documentato in questo bundle; resta `unknown + data_gaps`.
- Nessun esito di eligibility, riconoscimento, decorrenza economica, importo, pagatore o pagamento deriva da questa mappa. I cinque eventi timeline restano `not_assessed`, date/importi `null` e con `data_gaps`.

## Uso previsto e gate

Questa versione puo' supportare un nuovo Rules candidato solo dopo review normativa indipendente exact-hash. Il candidato deve mantenere distinti i tre rami della tabella INPS e citare la circolare come guidance amministrativa, mantenere le condizioni come prove esterne e lasciare i percorsi esclusi come gap. Un consumer runtime richiede un incremento separato, regressioni pubbliche e il proprio gate tecnico; nessun GO di questa nota si trasferisce a Rules, Engine o parent V4.14.

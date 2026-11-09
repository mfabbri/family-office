# Normative Change

Classificazione minima T4. Usare fonti autorevoli e dichiarare data di verifica, giurisdizione e periodo d'imposta.

## Flow obbligatorio

```text
authoritative source
  → family-office-knowledge
  → versioned family-office-rules
  → synthetic tests
  → engine integration
  → regression scenarios
```

## Controls

- distinguere legge, prassi, interpretazione e assunzione;
- non sovrascrivere regole storiche: versionare per periodo;
- esplicitare transitori, soglie, eccezioni e incertezze;
- non inserire valori normativi hard-coded nell'engine;
- produrre data gaps quando manca evidenza;
- richiedere review indipendente per cambi ad alto impatto.

Il risultato numerico resta deterministico; il modello può spiegare, citare e confrontare scenari.

## Verifica di vigenza e gerarchia delle fonti

- Classificare separatamente: legge o regolamento primario; atto attuativo vincolante (per esempio decreto); circolare/guidance amministrativa; evidenza o provvedimento individuale. Una fonte ufficiale non è automaticamente una fonte primaria e una circolare non sostituisce la norma.
- Per le fonti in gazzette ufficiali, distinguere il record/testo originale di pubblicazione dal testo consolidato. Se il sito qualifica il consolidato come informativo o privo di valore legale, etichettarlo e linkare anche la pubblicazione ufficiale originale; non collocare i due oggetti sotto una sola etichetta ambigua. In elenchi e matrici indicare il ruolo del singolo link (pubblicazione, consolidato informativo, guidance amministrativa), non solo una classificazione generale nel paragrafo introduttivo.
- Registrare separatamente data di pubblicazione, entrata in vigore/applicabilità, intervallo della disposizione, data di consultazione e data/periodo del testo consolidato restituito. Una snapshot consolidata con vigenza anteriore non prova da sola che manchino fonti successive: cercare atti ufficiali nella Gazzetta o nel repertorio competente e verificare le disposizioni transitorie.
- Per ogni valore numerico che dipende da più atti, ricostruire tutta la catena: base legislativa, atti di adeguamento, modifica successiva e tabella amministrativa. Se una parte non è tracciata, attribuire il valore alla fonte amministrativa che lo espone, registrare il gap e non presentarlo come pienamente ricertificato dalla norma primaria.
- Se un'affermazione dichiara completa la ricerca su un intervallo, la validità della regola e la copertura di ogni famiglia di evidenza devono coprire ogni data dell'intero intervallo, non soltanto le date candidate. Una lacuna interna invalida la completezza e resta `unknown + data_gaps`; non si colma interpolando o consultando soltanto l'estremo finale.
- Distinguere “dato amministrativo ufficiale coerente” da “perimetro normativo source-bound verificato”. Una verifica documentale non aggiorna automaticamente la provenance di un rule pack e non equivale a GO per il runtime.
- In caso di gap, non inferire retroattività, vigenza o applicabilità dal solo fatto che una pagina sia stata consultata di recente; mantenere limiti temporali e profili non classificati come gap/fail-closed.

## NO-GO e cicli di review

### Perimetro di evidenza e consumer

- Modellare la currentness con un intervallo esplicito, preferibilmente half-open `[valid_from, valid_to)`. Non estendere la data finale alla data corrente perche la fonte e stata consultata di recente; ogni data successiva resta `not_assessed + data_gaps` finche una nuova evidenza non la copre.
- Verificare la propagazione fino al consumer pubblico: anche un esito negativo (`not_matched`) puo sbloccare calcoli, eligibility, importi o obblighi a valle. Se l'incremento approva solo evidenza, il rule pack e il consumer devono impedire quelle emissioni; testare il builder/API pubblico con input validi, non solo l'helper interno.
- Fare concordare schema e loader/engine sui medesimi ID, cardinalita, ruoli, autorita, territorio e date delle fonti. Aggiungere mutazioni avverse per record duplicati/mancanti, ruoli scambiati, date alterate e riferimenti non risolti.

- Registrare il NO-GO con ambito preciso, rilievi azionabili e scope non approvati; non trasformare timeout o mancata risposta in un verdetto normativo.
- Ogni verdetto vincola la precisa versione della specifica/documento, giurisdizione, periodo e artefatti esaminati. Ogni correzione che cambia la semantica genera una nuova versione candidata; non trasferire un GO alla revisione successiva. Una chiusura editoriale senza nuovo parere è ammessa solo se il reviewer la dichiara esplicitamente e le modifiche restano entro quei limiti.
- Verificare e registrare gli hash degli artefatti prima della review e confrontarli con il verdetto. Hash corrispondenti provano l'identità del pacchetto, non la correttezza normativa o tecnica.
- Per un finding su link o gerarchia delle fonti, controllare la destinazione effettiva del singolo locator e il ruolo assegnatogli: pubblicazione originale, consolidato informativo e guidance amministrativa sono oggetti distinti. Una correzione minima può essere verificata solo sul nuovo hash; il GO precedente non si trasferisce.
- Trattare i gate come indipendenti: suite completa 0/0/0, review esatta, audit roadmap, schema planner e guardrails sono evidenze distinte. Test e governance verdi non compensano un NO-GO, un'attribuzione normativa errata o un mismatch di contratto.
- Un audit può risultare `done` come attività di review con verdetto NO-GO; l'incremento funzionale sottoposto a review resta `blocked`/`in_progress`, così come i parent. Non trasferire il `done` dell'audit al candidato né selezionare lavoro a valle oltre un predecessore incompleto.
- Il report finale del reviewer deve distinguere hash verificati, ambito/versione, GO/NO-GO e finding con evidenza localizzabile. Un checkpoint non conclusivo, un timeout o l'assenza di dettagli non diventano GO; se è esplicito un NO-GO ma le evidenze sono scarne, mantenere il blocco e chiedere solo un chiarimento bounded quando rientra nell'autorizzazione.
- Mantenere il lavoro parent sul percorso critico durante la review e usare attese bounded. Se il verdetto manca, dichiarare lo stato pendente/bloccato secondo il gate, senza completare né ripetere polling indefinito.
- Prima di ogni delega, aggiornare planner e routing trace. Rispettare il massimo di eventi di delega/escalation previsto dai guardrail; riusare il reviewer per un follow-up correlato quando possibile.
- Considerare limitata l'autorizzazione a numero di incrementi, correzioni, review, artefatti e scope dichiarati. Quando il ciclo/budget autorizzato è esaurito, aggiornare planner e roadmap, fermare ulteriori fix o review e attendere nuova autorizzazione esplicita; non interpretare una richiesta di completamento come estensione del budget.
- Dopo NO-GO post-fix, applicare solo i rilievi circoscritti. Se il reviewer dichiara esplicitamente che un set finito di correzioni editoriali consente la chiusura senza un altro parere, applicare esattamente quelle correzioni e conservare l'esito come GO limitato ai documenti. In mancanza di tale indicazione, non auto-approvare: lasciare review pendente e pianificare un nuovo gate.
- Per regressioni che dichiarano di coprire rami/short-circuit multipli, provare ogni condizione con un controllo valido che dimostri quale ramo sarebbe stato raggiunto; poi mutare l'evidenza. Un unico preflight che respinge l'input prima di tutti i rami non dimostra copertura dei singoli early-return.
- Il GO va qualificato per artefatto e perimetro. Una review di Knowledge/documentazione non ricertifica rules, consumer o engine e non rimuove gap che il reviewer non ha esaminato.
- Per le pensioni, distinguere sempre il mese/data di eligibility path-specific dai requisiti computazionalmente soddisfatti, dal riconoscimento amministrativo, dalla decorrenza economica e dal primo pagamento. Il primo non implica gli altri e non può essere presentato come "inizio pensione" o data complessiva quando altri rami/Paesi hanno gap.
- Alla chiusura aggiornare insieme planner, `current-next-increment.md`, roadmap e decision log quando impattati; registrare il prossimo passo concreto e i gap residui, non chain-of-thought.

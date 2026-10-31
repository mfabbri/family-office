# Piano per il calcolo automatico della data di uscita dal lavoro

## Obiettivo utente

Rispondere alla domanda: «In base ai dati documentati della famiglia, da quando possiamo ridurre o cessare il lavoro mantenendo sostenibile il reddito e il patrimonio?»

L'utente non sceglie una data di pensionamento da verificare. Il motore genera le date candidate e calcola le decorrenze pensionistiche dai periodi contributivi, dalle assunzioni future dichiarate e dalle regole versionate. Se un dato materiale manca, presenta il gap e non inventa una data.

## Percorso CLI finale

Il percorso utente converge su un comando question-first:

    fo planning work-transition plan

Il comando riusa gli snapshot disponibili, mostra quali fonti sono aggiornate e quali input mancano, guida la raccolta delle sole informazioni assenti e avvia gli stadi deterministici implementati quando la readiness non è bloccata. Il setup non richiede una data-obiettivo. Nella prima tranche V4.13 raccoglie metadati locali e binding delle fonti e si ferma alla readiness; il contratto scenario mensile FTE V4.12 esiste ma non ha ancora un wizard integrato nel journey. I vincoli per generazione/ranking delle candidate restano da definire negli incrementi successivi. Vincoli familiari e assunzioni saranno raccolti dal medesimo journey quando i rispettivi contratti saranno approvati.

L'importazione documentale resta disponibile come operazione di preparazione quando una fonte è nuova o non è ancora stata importata. Non va ripetuta automaticamente se gli snapshot risultano già aggiornati.

Output leggibile: prima data di uscita dal full-time sostenibile, alternativa raccomandata secondo vincoli espliciti, data di cessazione completa, fasi FTE, decorrenze separate per INPS/Spagna/UE/RITA, bridge, impatto patrimoniale, scenari scartati, assunzioni, provenienza, limiti e prossima azione.

## Sequenza di implementazione

| Fase | Contratto/capability | Criterio di uscita |
|---|---|---|
| Governance | Completata il 2026-10-11: V4B è l'unica roadmap attiva, V6 è differita fino alla chiusura V4.20, V4.13 è l'incremento corrente. | Decisione registrata in roadmap-index e decision-log prima del lavoro funzionale. |
| CLI progressiva (V4.13) | Wizard question-first per metadata e readiness/fonti, senza date candidate o assunzioni non ancora contrattualizzate. | Gli input sono generati solo nel workspace, le fonti sono selezionate esplicitamente e gli stadi mancanti restano blocker visibili. |
| V4.13 | Proiezione mensile di reddito netto da lavoro, contributi, TFR e previdenza complementare in funzione di FTE e policy versionate. | Netto e accumulo sono calcolati o marcati gap; niente proporzione lineare del netto full-time. |
| V4.14 | Timeline di diritto, importo e decorrenza per INPS, Spagna/UE e coniuge. Valuta ogni scenario di carriera separando i periodi nazionali e la totalizzazione UE. | Ogni stream ha fonte, date e stato propri; gli importi teorici non sono certificazioni. |
| V4.14a | Audit contrattuale e normativo prima del bridge. | Nessun gap materiale occulto, confusione lordo/netto o decorrenza presunta. |
| V4.15 | Timeline mensile del bridge: reddito residuo e familiare, pensioni attive, RITA eleggibile e prelievi dagli asset effettivamente liquidi. | Disponibilità, bounds, tassazione e provenance espliciti per ogni stream. |
| V4.16 | Baseline deterministica mensile e stress stocastico separato e riproducibile. | Shortfall, prelievi, liquidità minima e patrimonio terminale spiegabili; i gap bloccano il risultato materiale. |
| V4.17 | Generatore controllato di candidate: date derivate, sequenze FTE e durata delle fasi. | Candidate limitate, senza duplicati, con hash e ragione di inclusione/esclusione. Nessuna data di pensionamento imposta dall'utente. |
| V4.18 | Optimizer che valuta tutte le candidate e restituisce uscita full-time anticipata, alternativa raccomandata e cessazione completa. | Ranking e sensitivity dipendono da constraint dichiarati; nessuna data se un gap può cambiare il risultato. |
| V4.18a | Audit dell'optimizer e del rischio stocastico. | Determinismo, gross/net, timeline e regressioni verificati. |
| V4.19 | Migrazione/deprecazione dei comandi legacy e aggiornamento del tool registry. | CLI, registry e guide indirizzano al nuovo piano; uso avanzato compatibile o migrazione esplicita e testata. |
| V4.20 | Piano end-to-end e golden use case sintetico; comando breve e gate di roadmap. | Una run produce le tre date, alternative, fasi, bridge, pension start dates, risk metrics, gap e lineage. |

## Prossimi passi operativi

Stato di partenza verificato il 2026-10-18: V4.11 readiness e V4.12 contratto mensile FTE sono `done`; V4.13 è limitata ai componenti supportati e V4.14a è chiusa come audit diagnostico NO-GO. Il comando `plan` esegue manifest/readiness e binding delle fonti; V4.14 e V4.15 restano bloccate finché i gap source-bound non sono risolti.

1. **V4.13 — integrare il journey question-first.** Estendere `plan` per raccogliere gli input supportati dai contratti, collegando readiness, scenario mensile FTE ed employment projection. Le domande riguardano fatti e assunzioni; non chiedono una data pensionistica né una candidate di cessazione, che il motore genererà da V4.17.
2. **V4.13 — chiudere il gate deterministico e normativo.** Per ogni componente da calcolare, completare Knowledge → Rules → Tests → Engine con fonte, validità, base, precisione e reviewer appropriati. Componenti non supportate restano `null` con blocker e non alimentano l'optimizer; non introdurre aliquote o basi presunte.
3. **V4.14 resta il gate bloccato.** Risolvere i binding Art. 57/Annex VIII e gli altri percorsi nazionali secondo Knowledge → Rules → Tests → Engine; mantenere `null + data_gaps` per entitlement/payment non provati. V4.14a è già stato auditato e non sblocca il runtime.
4. **V4.15 → V4.16.** Comporre il bridge mensile con liquidità/provenienza e trattamento lordo/netto espliciti, poi aggiungere baseline deterministica e stress stocastico riproducibile. I gap materiali bloccano le metriche che possono alterare.
5. **V4.17 → V4.18.** Ottenere review finanziaria sui constraint e sul ranking; generare candidate controllate e valutarle. Il wizard raccoglie i vincoli familiari dichiarati nei contratti approvati, mentre le date di uscita sono output del motore. Non emettere date se un gap materiale può cambiarle.
6. **V4.18a → V4.19.** Eseguire audit indipendente su simulazione/optimizer; poi inventariare i consumer legacy, migrare o deprecare con adapter/test compatibili e rimuovere solo funzioni effettivamente sostituite.
7. **V4.20.** Validare il golden use case sintetico dal comando `plan` all'evidenza del piano e superare il gate V4B → V5. Solo da questo gate il comando può essere presentato come motore end-to-end che trova date possibili/sostenibili.

V4.11 readiness e lineage e V4.12 scenario mensile sono già marcati completati nella roadmap V4B e vanno riusati. Gli incrementi funzionali sopra mantengono l'ordine della roadmap; non si salta direttamente all'optimizer perché le stime pensionistiche future devono reagire alle fasi lavorative generate.

## Comandi e funzioni da migrare o mantenere

| Percorso attuale | Decisione |
|---|---|
| pension import-inps, pension import-spain, pension reconcile-spain | Mantenere come strumenti di ingestione e riconciliazione. Il piano li invoca o li suggerisce solo quando mancano fonti fresche. |
| planning it-es-eu-pension wizard | Togliere dal percorso ordinario: chiede un mese pensionistico e mesi aggregati, quindi non può guidare la ricerca automatica. Conservare temporaneamente come strumento avanzato/diagnostico; decidere la rimozione in V4.19 dopo che la timeline V4.14 ricostruisce i periodi datati dalle fonti. |
| planning it-es-eu-pension build | Riutilizzare o adattare come componente deterministica interna per candidate e importi espliciti. Non deve chiedere la data-obiettivo nel journey finale. |
| planning work-exit wizard/build (work-exit-feasibility/v1) | Marcare come legacy e diagnostica. Mantenerlo fino al gate V4.19; allora migrare o rimuovere l'opzione della data candidata scelta dall'utente dal flusso ordinario. L'architettura esistente vieta la cancellazione anticipata senza adapter/deprecation e test di compatibilità. |
| planning pension-scenario build | Mantenere separato se serve registrare assunzioni multi-scenario dichiarate; non presentarlo come motore che trova la data sostenibile. Rimuoverlo solo se l'inventario d'uso conferma che è duplicato e la migrazione V4.19 copre il suo contratto. |
| planning work-transition readiness/sources/scenario | Riutilizzare come infrastruttura e fasi dichiarate. Il nuovo percorso li orchestra; non richiede all'utente di eseguire la sequenza tecnica come unica UX. |

Non eliminare servizi o contratti riusabili soltanto perché non sono entry point del nuovo journey. La rimozione richiede: consumer inventory, sostituzione nel nuovo pipeline, adapter o deprecation versionata, test di migrazione, aggiornamento help/guide/tool registry e assenza di dipendenze residue.

## Regole di accettazione

- Il wizard non chiede una data pensionistica obiettivo né interpreta Invio/default come fatto.
- L'utente dichiara i vincoli della famiglia e le opzioni di lavoro; il generatore produce le date da valutare.
- Fonti documentali, proiezioni e assunzioni restano distinguibili e hanno provenienza e validità temporale.
- Ogni periodo IT/ES conserva paese e date; i periodi esteri non diventano basi contributive spagnole.
- Pension entitlement, cessazione del lavoro e inizio pagamento restano date distinte.
- Regole future non consolidate sono presentate come assunzioni di pianificazione, con finestra e confidence; fuori finestra il risultato si blocca.
- Nessun importo netto viene derivato da una pensione lorda senza un bridge fiscale disponibile.
- Snapshot e input personali rimangono confinati nel workspace privato.
- La review normativa pensionistica e quella finanziaria del simulatore si svolgono prima dell'integrazione finale; i calcoli restano deterministici e testati.

## Decisioni ancora necessarie

1. Definire i constraint ammessi per la generazione automatica delle candidate: livelli FTE, finestre temporali e soglie di liquidità/rischio, tutti espliciti e versionati.
2. Stabilire, tramite inventario consumer in V4.19, quali builder restano API avanzate e quali wizard/alias vengono rimossi.

L'incremento funzionale corrente è V4.13; il presente documento resta il piano end-to-end, non un sostituto dello stato verificabile nei contratti, nei test e nelle roadmap.

# Dual gate and convergence — Family Office AI (2026-11-14)

## Scopo

La certezza giuridica è **per conclusione, per periodo e per percorso**; la correttezza del software è **per commit/contratto/test**. Non chiedere di verificare il futuro come se fosse già vigente. Non cambiare il significato di GO/NO-GO/PENDING già registrato.

## Matrice di impatto prima della delega

| Diff reale | Classe | Gate richiesto | Se la review è pendente |
|---|---|---|---|
| A: loader/binding/API/tests per pack già immutabili e revisionati, senza nuovo output legale | T1–T3 implementazione | test pubblici + review tecnica indipendente se integrazione sensibile | Implementare fail-closed e registrare `software_ready` solo dopo evidenza |
| B: modifica fonte, periodo, legge, regola, formula di diritto/eligibility o nuova inferenza | T4 normativo | Knowledge→Rules→Tests→Engine + reviewer giuridico su versione esatta | Non emettere la conclusione; `normative_pending` con `data_gaps` |
| C: nuova formula economica, patrimonio o cash-flow senza interpretazione legale | T4 finanziario | golden finanziari + review specialistica se materialità alta | Non emettere ranking/valore non supportato |
| D: manutenzione editoriale senza semantica | T0 | test mirati o controllo lint | Nessuna nuova review normativa |

**Non applicare A** se accettare una nuova versione cambia i rami che abilitano eligibility, matching, payer, importi o date. Il diff deve dimostrare che tali output restano negati finché mancano evidenze individuali. Approvazione di Knowledge/Rules non equivale a GO del runtime.

## Tre categorie di output

1. `verified_as_of`: esito delle regole vigenti/applicabili, solo con fonti, periodi e fatti supportati; mai confermare un diritto senza atto o percorso sufficiente.
2. `scenario_projection`: ipotesi esplicite `as_of`, regole baseline e scenari di cambiamento; output non certificato, con sensitivity e revisione richiesta.
3. `administrative_unknown`: riconoscimento/arretrati/primo pagamento da enti competenti non conoscibili in anticipo; output `null + data_gaps` finché non vi sia il dato ufficiale.

Per gli eventi pensionistici distinguere eligibility/path screening, requisito computazionalmente soddisfatto, riconoscimento ufficiale, decorrenza economica e primo pagamento. Solo il percorso specifico e la granularità provata possono essere valorizzati.

## Protocollo anti-loop

1. Registrare blocker con chiave `(increment, gate, scope, source_version_hash, finding)` e criterio d'uscita verificabile.
2. Prima di ogni nuova review confrontare hash e finding. A parità di domanda/artefatto/periodo non richiedere nuova review se non cambia nulla.
3. Un massimo di **due tentativi senza verdetto sul medesimo gate** porta a `human_review_required` e stop dei retry automatici. Timeout non è NO-GO né GO.
4. Separare lavoro indipendente: il binding tecnico può avanzare conservando i blocchi normativi, ma non può dichiarare `normative_ready` né sbloccare incrementi funzionali a valle prima che il parent sia completato.
5. Un NO-GO con finding **specifico** conduce a una sola remediation bounded e un gate sulla nuova versione; se un nuovo finding non converge, registrare escalation umana anziché creare suffissi infiniti.
6. Registrare sempre cosa è cambiato materialmente: codice/test/digest, claim legalmente ammissibili, output osservabile, residui. Nessuna crescita del numero di incrementi è considerata progresso di per sé.

## Gate di completamento V4.14

- `software_ready`: V4.14w-z-b consumer v11/v0.3 verificato e testato, v9/v10 ancora funzionanti, nessuna inferenza non supportata; V4.14w-z-c timeline v2 deterministica testata per cinque eventi, con `null` se l'evidenza non consente una data.
- `normative_ready` per ciascuna determinazione: source-bound, legge/periodo, dati e review specialistica quando necessaria; senza tali requisiti l'output resta gap, non è riempito con uno scenario.
- `scenario_ready`: proiezioni future esplicitamente ipotetiche, senza validare diritti 2040/2041 o date di pagamento.
- `V4.14=done` soltanto quando tutti i done-when del parent sono soddisfatti, con gate integrato e suite 0/0/0. I LIMITEd GO storici restano limitati.

## Piani e delega

Per lavori che attraversano più moduli usare un ExecPlan leggero con `Progress`, `Surprises & Discoveries`, `Decision Log` e `Outcomes & Retrospective` solo se la complessità lo giustifica; una modifica banale non deve aprire un piano. Parent opera sul percorso critico; deleghe indipendenti e proporzionate. Evitare introduzione di procedure legali oltre al requisito sostanziale.

## Regressioni minime v11/v0.3

- Validazione dell'identità esatta dei pack, hash e finestra half-open; rifiuto versioni/hash errati.
- Test pubblici di input valido per reachability, poi mutazione di ciascuna condizione avversa; evitare falsi test che falliscono in un preflight non correlato.
- `not_assessed` e `not_matched` non promuovono scheme match, eligibility, payer, importi, riconoscimento o pagamento.
- Verificare versioni precedenti v9/v10 e invarianti di non inferenza dopo il binding.

In caso di contrasto con un vecchio playbook, **questa policy prevale sul routing procedurale**, senza derogare ai requisiti sostanziali, privacy, hash, immutabilità, test e non-inferenza.

## Guardrail convergence v4.0 — post V4.14w-z-n

- Lavori su errore documentale con regola primaria già identificata: test di coerenza `narrativa ↔ tabella ↔ Rules`, hash esatto, **una** review bounded dell'unico finding. Non ripetere la ricognizione IT/ES/UE in assenza di modifica normativa materiale.
- Quando un difetto editoriale ferma un parent, registrare `software_ready` ove tecnicamente verificato, `normative_pending` sulle sole conclusioni interessate e `scenario_ready` per proiezioni espressamente ipotetiche. Il parent V4.14 **non** diventa done se il gate integrato resta incompleto.
- Proibita la generazione automatica di w-z-o, w-z-p ecc. per una nuova contestazione del medesimo scope. Alla seconda remediation che non converge, produrre una decisione architetturale sulla granularita' del gate oppure `human_review_required`, non un audit infinito.
- Misurare progresso con tre output verificabili (`timeline`, `retirement bridge`, `work-transition comparison`) e con la semantica conservativa di `null+data_gaps`, non con il numero di manifest, reviewer e test eseguiti.
- Una ripianificazione dei predecessori V4.15–V4.20 necessita un cambiamento esplicito, tracciato e testato della roadmap; questa patch **non** cambia stati o sblocca dipendenze.


## Convergenza operativa v4.1 - lezioni di sessione (2026-11-21)

- **Selettore roadmap:** `roadmap_audit.py` legge la prima coppia canonica `## ID e titolo` / `## Stato` in `current-next-increment.md`. Mantenerne una sola; le note storiche usano intestazioni `storico`/`legacy`. Dopo una ripianificazione verificare che l'audit riporti proprio l'ID corrente, non solo un generico `OK`.
- **Confini dei test:** se un test controlla che un percorso non esca dal workspace e usa `Path('.')` come root, `TEMP`/`TMP` deve essere scrivibile ma fuori da quella root. Un temp interno rende legittimamente il percorso interno e invalida il controllo. Un errore ACL non e' un test fallito del prodotto ne' un esito verde; un runner elevato puo' cambiare la semantica dei path e richiede verifica esplicita dei confini.
- **Coerenza prima del freeze:** confrontare ogni claim fra Knowledge narrativa, tabelle, Rules e test. Oltre ad asserire rami e valori corretti, aggiungere asserzioni negative contro formulazioni obsolete o contraddittorie. Per fonti amministrative, testare anche titolo, data di pubblicazione, data di verifica e intervallo applicativo/di copertura.
- **Catena primaria e operatori:** per condizioni con piu' periodi verificare il connettivo della disposizione vigente (`all_of`/`any_of`) e la norma che ha introdotto eventuali modifiche; non basta citare il testo originario dell'atto modificato. La guidance amministrativa resta attribuita al proprio ruolo e periodo.
- **Budget di roadmap:** il numero di incrementi esplicitamente autorizzati e' un limite anche quando un incremento termina con NO-GO. Un NO-GO esaurisce il gate di quella versione; una correzione con nuovo hash richiede un nuovo incremento entro il budget disponibile. Al termine del budget fermarsi e chiedere nuova autorizzazione, senza creare suffissi o review impliciti.
- **Traccia deleghe:** `routing.trace` descrive l'incremento attivo. Prima di ripianificare, conservare finding, verdetto, hash ed esito storico nel decision log/planner; mantenere in trace solo selezione e deleghe dell'incremento corrente per rispettare il budget del guardrail.
- **Pulizia temporanei:** prima di cancellare cartelle, produrre l'inventario e verificare percorsi assoluti, ambito, processi attivi e assenza di file di workspace. Escludere sempre `family-office-workspace`. Una review automatica negativa non si aggira con comandi alternativi; si restringe ai target verificati o si chiede conferma sul perimetro.

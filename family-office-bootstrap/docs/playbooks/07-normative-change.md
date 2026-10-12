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
- Registrare separatamente data di pubblicazione, entrata in vigore/applicabilità, intervallo della disposizione, data di consultazione e data/periodo del testo consolidato restituito. Una snapshot consolidata con vigenza anteriore non prova da sola che manchino fonti successive: cercare atti ufficiali nella Gazzetta o nel repertorio competente e verificare le disposizioni transitorie.
- Per ogni valore numerico che dipende da più atti, ricostruire tutta la catena: base legislativa, atti di adeguamento, modifica successiva e tabella amministrativa. Se una parte non è tracciata, attribuire il valore alla fonte amministrativa che lo espone, registrare il gap e non presentarlo come pienamente ricertificato dalla norma primaria.
- Distinguere “dato amministrativo ufficiale coerente” da “perimetro normativo source-bound verificato”. Una verifica documentale non aggiorna automaticamente la provenance di un rule pack e non equivale a GO per il runtime.
- In caso di gap, non inferire retroattività, vigenza o applicabilità dal solo fatto che una pagina sia stata consultata di recente; mantenere limiti temporali e profili non classificati come gap/fail-closed.

## NO-GO e cicli di review

- Registrare il NO-GO con ambito preciso, rilievi azionabili e scope non approvati; non trasformare timeout o mancata risposta in un verdetto normativo.
- Mantenere il lavoro parent sul percorso critico durante la review e usare attese bounded. Se il verdetto manca, dichiarare lo stato pendente/bloccato secondo il gate, senza completare né ripetere polling indefinito.
- Prima di ogni delega, aggiornare planner e routing trace. Rispettare il massimo di eventi di delega/escalation previsto dai guardrail; riusare il reviewer per un follow-up correlato quando possibile.
- Dopo NO-GO post-fix, applicare solo i rilievi circoscritti. Se il reviewer dichiara esplicitamente che un set finito di correzioni editoriali consente la chiusura senza un altro parere, applicare esattamente quelle correzioni e conservare l'esito come GO limitato ai documenti. In mancanza di tale indicazione, non auto-approvare: lasciare review pendente e pianificare un nuovo gate.
- Il GO va qualificato per artefatto e perimetro. Una review di Knowledge/documentazione non ricertifica rules, consumer o engine e non rimuove gap che il reviewer non ha esaminato.
- Alla chiusura aggiornare insieme planner, `current-next-increment.md`, roadmap e decision log quando impattati; registrare il prossimo passo concreto e i gap residui, non chain-of-thought.

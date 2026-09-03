# Family Office AI — guida alle domande

Questa è la porta d'ingresso per un operatore nuovo. Parti dalla domanda familiare, usa `fo` dalla root del progetto e conserva ogni dato reale soltanto in `family-office-workspace/`. I demo usano dati sintetici; non confonderli con una valutazione del nucleo.

Per preparare la sessione e verificare l'installazione:

```powershell
. .\use-family-office.ps1
fo validate
```

La [guida al workflow CLI](cli-workflow.md) descrive l'ordine generale; la [reference CLI](cli.md) contiene opzioni e contratti dettagliati.

## “Quando posso smettere di lavorare?”

Percorso question-first:

```text
fo ask "Quando posso smettere di lavorare?"
fo planning work-exit wizard
fo planning work-exit build
```

`fo ask` chiarisce la decisione e mostra fatti disponibili, assunzioni, `data_gaps`, limiti, provenienza e prossima azione. Il wizard raccoglie solo gli input dichiarati mancanti e salva progressivamente nel workspace. Il build produce una prima data sostenibile oppure un blocco spiegato; non sostituisce INPS, P1, una certificazione o una raccomandazione professionale. Se le fonti sono già negli snapshot, il percorso di collegamento Work Transition resta il prerequisito operativo successivo.

## “Come proteggo il tenore di vita e il patrimonio?”

Per costruire gli input senza modificare JSON a mano:

```text
fo planning goals wizard
fo household availability wizard
fo planning liquidity wizard
fo planning decumulation wizard
fo planning wealth-strategy wizard
fo planning wealth-strategy build
```

Il percorso espone spese, liquidità, disponibilità degli asset, obiettivi e assunzioni di decumulo. Valori incerti diventano `data_gaps`; rendimenti, aliquote, liquidabilità e costi opportunità restano assunzioni da verificare. La strategia non è una consulenza finanziaria.

Per protezione e successione:

```text
fo planning protection wizard
fo planning estate wizard
fo planning protection build
fo planning estate build
```

Gli output sono baseline deterministiche e possono restare `partial` o `blocked_missing_inputs`. Quote ereditarie teoriche, coperture e vincoli non sostituiscono revisione legale, notarile o assicurativa.

## “Come confronto scenari o investimenti?”

Prima prepara i dati dichiarati e poi usa i passaggi deterministici:

```text
fo planning investment-opportunity build
fo planning real-estate-investment build
fo planning rentable-movable-asset build
fo planning financing-plan build
fo planning investment-opportunity-comparison build
fo scenarios compose-v2
fo scenarios evaluate
fo scenarios sensitivity
fo scenarios score
fo scenarios dossier
```

I demo sintetici disponibili sono un controllo tecnico, non dati familiari:

```text
fo planning investment-opportunity demo
fo planning investment-opportunity-comparison demo
fo planning goals demo
fo planning liquidity demo
fo planning decumulation demo
```

Ogni confronto deve rendere visibili ipotesi, fonti, limiti e data gaps. Nessun LLM calcola imposte, pensioni, rendimenti o ranking.

## “Quali documenti e dati posso usare?”

Il flusso locale è:

```text
fo documents inventory
fo documents organize
fo pipeline refresh
fo pipeline quality
fo pipeline lineage check --as-of-date 2026-09-02
```

Gli import dichiarati includono `fo payroll import`, `fo investments import`, `fo bank-insurance import`, `fo tax-documents import`, `fo fonte import` e `fo pension import-spain`. Gli snapshot indicano stato, provenienza e gap; non inventano dati mancanti. I comandi di import leggono soltanto il workspace privato.

## “Come coordino pensioni, cashflow e fiscalità?”

I percorsi principali sono:

```text
fo pension import-inps
fo pension import-spain
fo pension reconcile-spain
fo pension compose-income
fo expenses build-lifecycle
fo planning pension-contributions build
fo planning it-es-eu-pension wizard
fo planning it-es-eu-pension build
fo expenses build-lifecycle
fo tax calculate
fo tax reconcile
fo rita optimize
```

Usa demo e fixture solo per smoke test. I calcoli sono deterministici e versionati; copertura normativa, dati contributivi, netto fiscale e risultati ufficiali possono richiedere fonti o revisione professionale.

## “Come controllo compliance, sicurezza, backup e audit?”

```text
fo compliance calendar --as-of-date 2026-09-02
fo security check
fo export sanitized
fo backup create
fo backup verify
fo backup drill
fo audit verify
fo audit replay
fo release check
```

Questi comandi sono locali: non fanno upload, deploy o rete. L'export è una confezione tecnica sanitizzata; backup e restore richiedono percorsi workspace-local e la chiave non viene inclusa. Il calendario non determina obblighi fiscali individuali. Il release gate raccoglie evidenze di regression, versioni e rollback dichiarativo.

## Output, gap e prossima azione

Gli stati ricorrenti sono `complete`, `partial`, `blocked_missing_inputs` e `blocked_missing_rule`. Un risultato `partial` è utile per revisione ma non è una raccomandazione. Quando mancano dati, il prossimo comando utile deve essere indicato dall'output o dalla guida; non colmare il gap con un valore inventato.

Dashboard e report leggibili si costruiscono dopo gli snapshot necessari:

```text
fo dashboard build
fo report build
```

Per dettagli, opzioni avanzate, input strettamente necessari e fallback tecnico, consulta [cli.md](cli.md). La compilazione manuale di JSON è un fallback per contratti avanzati, non il percorso ordinario.

## Confini dei dati

Nel repository sono ammessi soltanto esempi sintetici e identificativi tecnici. Nomi, codici fiscali, indirizzi, email, numeri di documento e snapshot reali appartengono a `family-office-workspace/` e non devono essere copiati qui, negli export tecnici o nei log.

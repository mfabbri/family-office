# Model routing

Obiettivo: usare il modello meno costoso che preserva il contratto del task, senza moltiplicare agenti o contesto.

## Default

- Sessione principale: `gpt-5.6-terra`, reasoning `medium`, verbosity `low`.
- Fallback compatibilita': `gpt-5.5`, reasoning `medium`.
- Mai usare l'alias eseguibile non suffissato `gpt-5.6` nelle configurazioni del repository; usare gli ID esatti.

| Tier | Modello | Reasoning | Uso tipico |
|---|---|---:|---|
| economy | `gpt-5.6-luna` | low | inventario, search/read mirati, controlli ripetitivi, fixture/schema enumeration |
| standard | `gpt-5.6-terra` | medium | implementazione ordinaria, planning delimitato, bug, documentazione |
| advanced | `gpt-5.6-terra` | high | debug difficile, review cross-module, contract/design validation |
| critical | `gpt-5.6-sol` | high | matematica finanziaria, architettura, migrazioni, review ad alto impatto |
| exceptional | `gpt-5.6-sol` | xhigh | ambiguita' normativa/architetturale realmente difficile; non e' un default |
| fallback | `gpt-5.5` | medium | client/account che non espone il profilo 5.6 richiesto o regressione verificata |

## Routing per classe task

- T0: Luna/low; non spawnare agenti se il main puo' risolvere con una sola lettura.
- T1: Terra/low-medium; Luna solo per discovery bounded.
- T2: Terra/medium; planner Terra opzionale se attraversa piu' contratti.
- T3: Terra/medium per implementazione, reviewer Terra/high al termine se il rischio lo giustifica.
- T4: Terra/medium per editing deterministico; Sol/high per review finanziaria o normativa. `xhigh` solo con trigger esplicito.
- T5: Terra/high per planning; Sol/high per una sola review indipendente delle decisioni irreversibili o ad alto impatto.

## Regole di risparmio token

1. Ridurre prima contesto e reasoning, poi cambiare modello.
2. Testare la stessa classe di task a un livello di reasoning inferiore prima di consolidare un setting piu' costoso.
3. `model_verbosity = low` per output operativi; aumentare la verbosita' solo quando il deliverable lo richiede.
4. Luna deve restituire sintesi, non dump di file o log.
5. Un subagent deve sostituire una lettura/esplorazione costosa del main, non duplicarla.
6. Massimo due subagent concorrenti e solo su workstream indipendenti.
7. Preferire un singolo reviewer specializzato a piu' reviewer generici.
8. Non usare Sol per typo, listing, boilerplate, test gia' localizzati o documentazione meccanica.
9. Non aumentare reasoning per compensare requisiti ambigui: chiarire il contratto o leggere l'evidenza mancante.
10. Se GPT-5.6 non e' disponibile nel client/account, usare `fallback55` senza cambiare i contratti del task.

## Trigger per Sol/xhigh

Usare `critical` solo se almeno uno e' vero:

- interpretazione normativa con piu' letture plausibili e impatto materiale;
- formula finanziaria nuova o cambiamento di semantica di IRR/NPV/DSCR/tassazione;
- migrazione di schema con compatibilita' retroattiva difficile;
- decisione architetturale cross-repository irreversibile;
- regressione non spiegata dopo evidenza e test mirati.

Altrimenti fermarsi a Terra/high.

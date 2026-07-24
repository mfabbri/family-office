# Current Next Increment

## ID e titolo

V4.7 - Real-estate planning.

## Stato

`planned`

## Roadmap

`docs/roadmap/roadmap-v4-wealth-planning.md`

## Motivazione e dipendenze

V4.6g e' completato: il motore ora dispone di `pension-scenario/v1` per separare assunzioni pensionistiche personali da output previdenziali, fiscali e dossier IT-ES. L'audit cadence non richiede un nuovo audit prima di V4.7.

V4.7 dipende da V3.2 e V3.4, gia' completati secondo la roadmap. L'incremento e' T4 se introduce calcoli fiscali/immobiliari normativi; sara' T2 solo per modellazione puramente strutturale senza regole fiscali.

## Piano operativo

1. Verificare contratti esistenti per ownership, asset availability, net worth e fiscalita' immobiliare gia' versionata.
2. Definire input minimo `real-estate-plan/v1` per immobile, proprieta', locazione, costi, vacancy, vendita e liquidita'.
3. Implementare il servizio deterministico minimo senza dedurre valori mancanti.
4. Aggiungere fixture sintetiche e test su locazione, vacancy, vendita, costi e titolarita' del coniuge.
5. Collegare CLI e documentazione soltanto per i comandi necessari.
6. Eseguire test mirati e regression appropriata prima di segnare `done`.

## Perimetro previsto

- Modellazione e confronto deterministico di alternative immobiliari.
- Nessun LLM nei calcoli; valori patrimoniali, costi, imposte e ipotesi devono essere espliciti o derivare da rule pack deterministici.
- Nessuna raccomandazione legale, fiscale o patrimoniale senza revisione professionale dichiarata.

## Input personali necessari

Da definire prima dell'implementazione: immobili rilevanti, quota/titolarita', stato d'uso, canone o ipotesi di vacancy, costi ricorrenti, eventuale prezzo di vendita stimato e provenance. Usare fixture sintetiche finche' non esiste input personale nel workspace.

## Stato implementazione

Pianificato. V4.6g e' stato completato con test mirati e regression completa; nessuno snapshot personale e' stato rigenerato per assenza di `family-office-workspace/planning/pension-scenario.json`.

## Criteri di completamento

- Il piano immobiliare confronta mantenimento, locazione e vendita su input espliciti.
- Titolarita', liquidita', costi e vacancy sono tracciati con provenance e gap.
- Le imposte sono calcolate solo da rule pack versionati oppure esposte come gap.
- Test mirati e regression pertinente verdi.

## Incrementi successivi

V4.8 - Insurance and family protection.

## Rischi, esclusioni e blocker

- Possibile impatto fiscale e successorio: seguire `knowledge -> rules -> tests -> engine` se servono regole nuove.
- Fuori perimetro iniziale: perizie ufficiali, atti notarili, dichiarazioni fiscali complete e raccomandazioni legali.

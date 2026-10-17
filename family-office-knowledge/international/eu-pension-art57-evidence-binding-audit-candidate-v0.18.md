# Art. 57 evidence-binding audit — candidate v0.18

**Stato:** candidato documentale non approvato; non abilita Rules o runtime.
**Verifica del testo:** 2026-10-17. Le consolidate EUR-Lex sono strumenti di documentazione; fanno fede gli atti autentici pubblicati nella GUUE.

## Fonti primarie consultate

- Reg. (CE) 883/2004, testo consolidato EUR-Lex al 31-07-2019: artt. 52 e 57, Annex VIII Parts 1–2. https://eur-lex.europa.eu/eli/reg/2004/883/2019-07-31/eng
- Reg. (CE) 988/2009, atto modificativo e testo dell’Annex VIII sostitutivo: https://eur-lex.europa.eu/eli/reg/2009/988/oj/eng
- Reg. (UE) 1244/2010, aggiornamento Annex VIII: https://eur-lex.europa.eu/eli/reg/2010/1244/oj/eng
- Reg. (UE) 1224/2012, aggiornamento Annex VIII: https://eur-lex.europa.eu/eli/reg/2012/1224/oj/eng
- Reg. (UE) 517/2013, adattamento Annex VIII per l’adesione della Croazia: https://eur-lex.europa.eu/eli/reg/2013/517/oj/eng
- Reg. (UE) 1372/2013, modifica dell’Annex VIII Part 2: https://eur-lex.europa.eu/eli/reg/2013/1372/oj/eng
- Reg. (UE) 2017/492, modifiche agli allegati dei Reg. 883/2004 e 987/2009: https://eur-lex.europa.eu/eli/reg/2017/492/oj/eng
- Reg. (CE) 987/2009, atto attuativo, artt. 45–48, in particolare 47(4)–(7): https://eur-lex.europa.eu/eli/reg/2009/987/oj/eng

Il consolidato 883/2004 espone l’art. 57(1) come condizioni cumulative: periodi pertinenti inferiori a un anno e nessun diritto acquisito secondo la legislazione di quell’istituzione considerando soltanto tali periodi. Il par. 2 impone alle istituzioni competenti interessate di considerare quei periodi per l’importo teorico. Il par. 3 opera soltanto se applicare il par. 1 solleverebbe tutte le istituzioni interessate dai loro obblighi; in tal caso la prestazione è dovuta esclusivamente secondo la legislazione dell’ultimo Stato membro le cui condizioni sono soddisfatte. Il par. 4 esclude gli schemi elencati nell’Annex VIII Part 2.

L’art. 47 del Reg. 987/2009 disciplina la trasmissione concorrente delle domande/documenti, la comunicazione dei periodi assicurativi o di residenza e l’informazione alle altre istituzioni quando risulti applicabile l’art. 57(2) o (3). Queste disposizioni non prescrivono un identificatore software condiviso né stabiliscono che identificativi nazionali diversi debbano coincidere.

Nel consolidato 883/2004 al 31-07-2019, la Parte 2 è intestata ai casi in cui si applica l’art. 52(5) e contiene 15 sezioni-Stato/23 voci di schema. La cronologia di modifica individuata per la Parte 2 dopo la sostituzione introdotta dal Reg. 988/2009 comprende i Reg. 1244/2010, 1224/2012, 517/2013, 1372/2013 e 2017/492. Il consolidato non ha efficacia autentica: ciascuna voce e il proprio intervallo temporale devono essere riconciliati agli atti GUUE prima di alimentare un catalogo eseguibile.

Il controllo del rule pack locale ha inoltre rilevato un riferimento da verificare/correggere: il pack cita il Reg. 988/2009, art. 1(27), mentre l’inserimento dell’art. 57(4) risulta all’art. 1(16). Il pack dichiara per Annex VIII una versione iniziale 2010-05-01 senza fine validità, che non incorpora gli aggiornamenti successivi sopra elencati. È un finding documentale per il successivo micro-incremento Knowledge → Rules → Tests → Engine, non una modifica autorizzata in questo audit.

## Requisiti candidati per una futura specifica tecnica

1. L’esito Art. 57(3) non può derivare da un aggregato o da un numero di record privo di prova di completezza. L’insieme delle istituzioni interessate deve essere esplicito e collegato, con provenienza verificabile, alla medesima domanda/caso coordinato e ai periodi/esiti considerati. Possibile contratto tecnico da sottoporre a validazione: riferimento opaco al caso coordinato con issuer/namespace/versione, riferimenti locali distinti e prove di collegamento contenute nella comunicazione inter-istituzionale; non uguagliare identificativi nazionali. Nessuna di queste chiavi è prescritta espressamente dagli artt. 57 o 47.
2. Per ciascuna istituzione dell’insieme, servono separatamente il test Art. 57(1), il suo esito e le evidenze/versioni applicate. L’esito del par. 3 richiede prova che il par. 1 solleverebbe tutte le istituzioni, non la sola presenza di un record per ciascuna.
3. L’istituzione pagatrice non si inferisce dall’ordine di input: occorrono prova dell’ordine temporale rilevante e prova che le condizioni dell’ultimo Stato membro siano soddisfatte.
4. Un match Annex VIII Part 2 deve indicare la voce/schema e la fonte/versione applicabile alla data rilevante. Un non-match è valutabile solo contro un catalogo dimostrabilmente completo per quella versione; catalogo incompleto, data o identificazione dello schema mancanti producono `not_assessed` con `data_gaps`, non `false`. La riconciliazione storica deve includere tutte le voci ed i confini temporali degli atti elencati sopra, incluso l’avvicendamento delle voci danesi/svedesi e gli aggiornamenti di Portogallo, Croazia, Austria e Repubblica ceca.
5. Il contratto v0.17 descrive un parent e un bound per il ramo durata: fino a una nuova versione, validare cardinalità esattamente 1. La grammatica c14n-v4 resta un contratto tecnico autonomo da definire e validare integralmente: ogni parent e ogni source-bound devono rispettare schema, cardinalità, riferimenti e vincoli di canonicalizzazione; hash corretto da solo non dimostra conformità strutturale o semantica. Testare anche un bound non valido in ciascuna posizione, non solo il primo.

I punti 1–5 sono requisiti tecnici candidati derivati per fail-closed e tracciabilità, non formule o identificatori prescritti dalla normativa. Il modo concreto di attestare completezza, legame al caso e ordine istituzionale resta `not_assessed` finché una specifica esatta non è approvata indipendentemente.

## Data gaps e limiti dell’audit

- Il consolidato EUR-Lex consultato è datato 31-07-2019. La catena sopra deriva dal controllo indipendente dell’evento 1, ma prima di congelare un catalogo eseguibile occorre riconciliare ciascun atto autentico, tutte le 23 voci e la relativa efficacia temporale; la presente nota non certifica ancora l’esaustività degli entry al 2026-10-17.
- La verifica non classifica schemi nazionali individuali, casi personali, periodi o pagatori.
- La review normativa dell’evento 1 è rientrata dopo l’interruzione bounded con finding parziali e scope residuo non verificato; questo testo è una base candidata del parent, non un’approvazione indipendente.
- La review exact-version dell’evento 2 è necessaria prima di promuovere questa specifica; fino ad allora V4.14w resta bloccato e nessun runtime è approvato.

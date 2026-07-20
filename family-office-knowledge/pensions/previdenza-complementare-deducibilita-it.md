# Previdenza complementare - deducibilita' contributi Italia

## Perimetro V4.4

Questa nota copre la deducibilita' dei contributi a forme pensionistiche complementari per residenti fiscali italiani, con primo rule pack operativo per il periodo d'imposta 2026.

Non copre tassazione delle prestazioni, anticipazioni, riscatti, rendimenti del fondo, fiscalita' estera, addizionali, detrazioni, compilazione della dichiarazione o verifica di convenienza finanziaria.

## Fonti verificate

Verifica effettuata il 2026-07-20.

- Normattiva, Decreto legislativo 5 dicembre 2005, n. 252, articolo 8, testo vigente consultato il 2026-07-20.
- Normattiva, DPR 22 dicembre 1986, n. 917, articolo 10, oneri deducibili, testo vigente consultato il 2026-07-20.
- Agenzia Entrate, dichiarazione precompilata, sezione "Previdenza complementare - Contributi a deducibilita' ordinaria", consultata il 2026-07-20.

## Regola implementabile

Per le forme pensionistiche complementari, i contributi versati dal lavoratore e dal datore di lavoro o committente sono deducibili dal reddito complessivo entro il limite ordinario annuo di 5.164,57 euro. Nel computo rientrano i versamenti a carico del contribuente e del datore di lavoro; i contributi non dedotti devono essere comunicati alla forma pensionistica entro i termini previsti.

Per i lavoratori di prima occupazione successiva al 1 gennaio 2007, il D.Lgs. 252/2005 prevede, nei venti anni successivi al quinto anno di partecipazione, una deduzione aggiuntiva annuale entro il minore tra:

- differenza positiva tra 25.822,85 euro e contributi effettivamente versati nei primi cinque anni;
- 2.582,29 euro annui.

Il conferimento del TFR maturando finanzia la previdenza complementare ma non va trattato come contributo ordinario deducibile del lavoratore nel limite di 5.164,57 euro. Per V4.4 deve essere esposto separatamente come liquidita'/retribuzione differita vincolata e non come beneficio fiscale immediato.

## Regola engine

Il motore deve:

- caricare limiti, fonti e periodo da rule pack versionato;
- ricevere aliquota marginale, contributi gia' dedotti e opzioni future come input espliciti;
- stimare il beneficio fiscale come `deducibile * aliquota_marginale_dichiarata`;
- separare versamento lavoratore, contributo datore e TFR;
- segnalare eccedenze non deducibili, dati mancanti, anno non coperto e vincoli di liquidita';
- non calcolare IRPEF completa o raccomandazioni.

## Avvertenze

Il risultato e' una stima deterministica basata su input dichiarati e rule pack versionato. Deve essere revisionato da un professionista prima di decisioni fiscali, previdenziali o di investimento.

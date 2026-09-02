# V6.6 — Security threat model

## Perimetro

Il perimetro e' il checkout software e il workspace locale privato. Il threat model non include rete, cloud KMS, accesso remoto o dati personali nel repository.

| Asset | Minaccia | Controllo V6.6 | Evidenza |
|---|---|---|---|
| Chiavi e token | commit o log accidentale | scanner per pattern, secret store escluso dai repository, log redatti | finding `secret_detected` senza contenuto; placeholder espliciti `synthetic`/`fixture`/`example` sono esclusi |
| Snapshot e documenti | lettura da file non protetti | cifratura Fernet esplicita, output con permessi proprietario | round-trip e chiave errata |
| Secret store | sostituzione, chiave invalida o permessi eccessivi | path confinato, validazione Fernet, mode owner-only su POSIX | `secret_store_permissions` |
| Diagnostica | esfiltrazione tramite output | solo codici finding e path relativi | test CLI senza segreti |
| Percorsi | scrittura fuori workspace | risoluzione e controllo dei parent prima di ogni operazione | test traversal |

## Limiti e residuo

La cifratura non viene applicata automaticamente agli snapshot esistenti: l'operatore deve scegliere esplicitamente file e destinazione. Su Windows i bit POSIX non rappresentano gli ACL NTFS; il report usa `acl-managed` e richiede una verifica ACL del sistema operativo per una garanzia completa. Il modulo non promette disponibilita', recupero da perdita della chiave o isolamento multiutente: backup e disaster recovery appartengono a V6.8.

## Regola operativa

Un finding non deve essere risolto nascondendo il file o il contenuto allo scanner. La correzione deve rimuovere il segreto dal repository/log, cifrare esplicitamente l'artefatto nel workspace o ridurre i permessi con uno strumento ACL appropriato.

V6.8 aggiunge backup workspace-local cifrati con Fernet e manifest laterale di hash. Il payload esclude secret store, backup precedenti, cache, temporanei e symlink; il restore valida traversal e autenticita' prima di scrivere. La chiave resta separata: perdita della chiave e' un data gap operativo che richiede il secret store conservato dall'operatore.
### Audit trail V6.9

Il log locale `audit-event/v1` salva esclusivamente attore, soggetto, azione e riferimento validati; non salva documenti o testo libero multi-linea. Ogni riga e' concatenata con SHA-256 alla precedente e `verify` controlla schema, sequenza, catena e hash. La revoca non modifica eventi precedenti. Il controllo dell'orologio rifiuta timestamp futuri oltre cinque minuti; la firma remota e l'identita' federata sono fuori perimetro.

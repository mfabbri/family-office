# Code Audit

Usare anche `../code-audit-checklist.md`.

## Strategia token-efficient

1. definire perimetro dagli ultimi incrementi o dal diff;
2. usare ricerca simboli e metriche prima di aprire file;
3. dividere per aree solo se indipendenti;
4. usare al massimo due subagent read-only;
5. richiedere findings con file, simbolo, gravità e prova;
6. non fare refactor ampi dentro l'audit;
7. trasformare i findings in micro-incrementi espliciti.

Un audit non deve diventare una rilettura completa del repository senza ipotesi o perimetro.

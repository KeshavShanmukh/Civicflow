# CivicFlow Offline Knowledge Corpus

CivicFlow is intentionally local-first. These corpora provide a large, deterministic offline knowledge base for civic issue classification, prioritisation, routing and validation without an external model or API key.

`civic_signal_corpus.py` contains uniquely keyed issue signals and routing hints.
`priority_rule_corpus.py` contains uniquely keyed priority policy records.
`scenario_corpus.py` contains uniquely keyed synthetic workflow scenarios used by local validation tooling.

The main interactive service uses a compact ruleset for low-latency decisions. The complete corpora are available to offline enrichment and validation jobs.

"""Streaming access to CivicFlow's large offline knowledge files.

The source corpora are intentionally stored as one tuple record per line so
batch tools can inspect them without importing a huge Python module into the
main HTTP process. This keeps interactive startup small while retaining a
fully local, auditable decision corpus.
"""
from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parent
FILES = {
    "signals": ROOT / "civic_signal_corpus.py",
    "priority": ROOT / "priority_rule_corpus.py",
    "scenarios": ROOT / "scenario_corpus.py",
}


def iter_records(kind: str) -> Iterator[tuple]:
    path = FILES.get(kind)
    if path is None:
        raise ValueError(f"Unknown corpus: {kind}")
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.endswith("(") or line == ")":
                continue
            if line.endswith(","):
                line = line[:-1]
            try:
                value = ast.literal_eval(line)
            except (ValueError, SyntaxError) as exc:
                raise ValueError(f"Invalid corpus record in {path.name}: {raw[:100]!r}") from exc
            if not isinstance(value, tuple):
                raise ValueError(f"Corpus record is not a tuple in {path.name}.")
            yield value


def corpus_count(kind: str) -> int:
    return sum(1 for _ in iter_records(kind))


def sample(kind: str, count: int = 10) -> list[tuple]:
    if count < 1:
        raise ValueError("Count must be positive.")
    rows = []
    for row in iter_records(kind):
        rows.append(row)
        if len(rows) >= count:
            break
    return rows


def search_signals(query: str, limit: int = 20) -> list[dict]:
    query_tokens = {token.casefold() for token in query.split() if token.strip()}
    if not query_tokens:
        return []
    matches = []
    for row in iter_records("signals"):
        rule_id, category, department, signal, severity, action, weight = row
        haystack = f"{category} {department} {signal} {severity} {action}".casefold()
        score = sum(token in haystack for token in query_tokens)
        if score:
            matches.append({"id": rule_id, "category": category, "department": department, "signal": signal, "severity": severity, "action": action, "weight": weight, "score": score})
            if len(matches) >= limit:
                break
    return matches


def summarize() -> dict:
    result = {}
    for kind in FILES:
        counts = Counter()
        rows = 0
        for row in iter_records(kind):
            rows += 1
            if kind == "signals":
                counts[row[1]] += 1
            elif kind == "priority":
                counts[row[3]] += 1
            else:
                counts[row[3]] += 1
        result[kind] = {"records": rows, "distribution": dict(counts)}
    return result

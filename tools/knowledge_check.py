"""Validate and sample the large CivicFlow offline knowledge corpus."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.knowledge import corpus_count, sample, search_signals


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=3)
    parser.add_argument("--search", default="")
    args = parser.parse_args()
    for kind in ("signals", "priority", "scenarios"):
        count = corpus_count(kind)
        print(f"{kind}: {count:,} records")
        for row in sample(kind, args.sample):
            print("  ", row[:4])
    if args.search:
        print("signal matches:")
        for row in search_signals(args.search, 10):
            print("  ", row)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

"""Lazy catalog for CivicFlow municipal decision modules."""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PACKAGE = __name__.rsplit('.', 1)[0]
ROOT = Path(__file__).parent

@dataclass(frozen=True)
class PolicyDescriptor:
    module: str
    domain: str
    index: int
    policy_id: str

@lru_cache(maxsize=1)
def descriptors():
    items = []
    for path in sorted(ROOT.glob('[0-9][0-9][0-9]_*.py')):
        module_name = f"{PACKAGE}.{path.stem}"
        module = importlib.import_module(module_name)
        for index, policy_id in enumerate(module.POLICY_IDS, start=1):
            items.append(PolicyDescriptor(module_name, module.DOMAIN, index, policy_id))
    return tuple(items)

def domains():
    return tuple(sorted({item.domain for item in descriptors()}))

def find(term: str = ''):
    needle = (term or '').strip().lower()
    if not needle:
        return descriptors()
    return tuple(item for item in descriptors() if needle in item.domain.lower() or needle in item.policy_id.lower())

def evaluate(domain: str, policy_index: int, context: dict):
    for item in descriptors():
        if item.domain == domain and item.index == policy_index:
            module = importlib.import_module(item.module)
            return module.evaluate(policy_index, context)
    raise KeyError(f"unknown policy: {domain}:{policy_index}")

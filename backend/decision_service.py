"""Application service for the local CivicFlow policy catalog."""
from __future__ import annotations

from .domain_rules.catalog import descriptors, domains, evaluate as evaluate_policy, find

class DecisionService:
    """Expose local municipal rules without coupling HTTP handlers to rule modules."""

    def catalog(self, term: str = ''):
        return [
            {
                'module': item.module,
                'domain': item.domain,
                'index': item.index,
                'policyId': item.policy_id,
            }
            for item in find(term)
        ]

    def evaluate(self, domain: str, policy_index: int, context: dict):
        return evaluate_policy(domain, policy_index, context)

    def statistics(self):
        all_items = descriptors()
        domain_names = domains()
        return {
            'domains': len(domain_names),
            'policies': len(all_items),
            'average_policies_per_domain': round(len(all_items) / max(1, len(domain_names)), 2),
        }

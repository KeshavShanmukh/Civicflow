import unittest

from backend.decision_service import DecisionService

class DecisionCatalogTests(unittest.TestCase):
    def test_catalog_is_large_and_local(self):
        service = DecisionService()
        stats = service.statistics()
        self.assertGreaterEqual(stats['domains'], 200)
        self.assertGreaterEqual(stats['policies'], 4000)

    def test_find_and_evaluate(self):
        service = DecisionService()
        results = service.catalog('roads')
        self.assertTrue(results)
        first = results[0]
        result = service.evaluate(first['domain'], first['index'], {'severity': 80, 'age_hours': 12, 'affected_people': 40, 'repeat_count': 2, 'worker_load': 50, 'evidence_score': 0.8})
        self.assertIn(result['decision'], {'low', 'medium', 'high', 'critical', 'review', 'hold'})
        self.assertIn('trace', result)

if __name__ == '__main__':
    unittest.main()

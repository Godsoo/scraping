import unittest

from ..stats import ChangesStats, AdditionalChangesStats
from ..changes import Change, PriceChange, AdditionalChange
from mock import MagicMock


class TestChangesStats(unittest.TestCase):
    def test_changes_stats(self):
        stats = ChangesStats()
        changes = [Change.NO_CHANGE, Change.UPDATE, Change.NEW, Change.OLD]
        for c in changes:
            change = PriceChange()
            change.change_data = MagicMock(return_value=(c, {}))
            stats.process_res(change)
        stats = stats.stats
        self.assertEqual(dict(stats), {'products': 3, 'previous_products': 3,
                                       'new_products': 1,
                                       'old_products': 1,
                                       'price_changes': 1})


class TestAdditionalChangesStats(unittest.TestCase):
    def test_additional_changes_stats(self):
        stats = AdditionalChangesStats()
        changes = [{'name': ('1', '')},
                   {'stock': ('', '0')}]

        for c in changes:
            change = AdditionalChange()
            change.change_data = MagicMock(return_value=(AdditionalChange.UPDATE, {'changes': c}))
            stats.process_res(change)
        stats = stats.stats
        self.assertEqual(dict(stats), {'additional_changes': 2,
                                       'additional_empty': 1,
                                       'out_stock': 1,
                                       'additional_changes_name': 1,
                                       'additional_changes_stock': 1})
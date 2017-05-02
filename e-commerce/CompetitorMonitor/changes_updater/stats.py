from collections import defaultdict
from join_computation import ChangeJoinComputation
from changes import Change


class ChangesStats(ChangeJoinComputation):
    """
    Join computation to calculate and store the main crawl stats.
    """
    def __init__(self, *args, **kwargs):
        super(ChangesStats, self).__init__(*args, **kwargs)
        self.rules = {'products': lambda ct, c: ct in [Change.UPDATE, Change.NO_CHANGE, Change.NEW],
                      'previous_products': lambda ct, c: ct in [Change.UPDATE, Change.NO_CHANGE, Change.OLD],
                      'new_products': lambda ct, c: ct in [Change.NEW],
                      'old_products': lambda ct, c: ct in [Change.OLD],
                      'price_changes': lambda ct, c: ct in [Change.UPDATE]}
        self._stats = defaultdict(int)

    def process_res(self, result):
        change_type, change_data = result.change_data()
        for rule in self.rules:
            if self.rules[rule](change_type, change_data):
                self._stats[rule] += 1

    @property
    def stats(self):
        return self._stats


class AdditionalChangesStats(ChangesStats):
    """
    Join computation to calculate and store the additional changes stats.
    """
    accept_codes = [Change.UPDATE]

    def __init__(self, *args, **kwargs):
        super(AdditionalChangesStats, self).__init__(*args, **kwargs)

    def process_res(self, result):
        change_type, change_data = result.change_data()
        self._stats['additional_changes'] += 1
        changes = change_data['changes']
        for field in changes:
            self._stats['additional_changes_{}'.format(field)] += 1
            old_val, new_val = changes[field]
            if not new_val:
                self._stats['additional_empty'] += 1

            if field == 'stock' and new_val == '0':
                self._stats['out_stock'] += 1


class MetadataChangesStats(ChangesStats):
    """
    Join computation to calculate and store the metadata changes stats.
    """

    def process_res(self, result):
        if result.new_element and result.new_element['metadata'].get('reviews'):
            self._stats['reviews'] += 1
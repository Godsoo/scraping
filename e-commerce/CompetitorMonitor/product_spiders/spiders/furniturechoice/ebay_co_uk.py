import os

from product_spiders.base_spiders import BaseeBaySpider

class FurnitureChoiceEbaySpider(BaseeBaySpider):

    HERE = os.path.abspath(os.path.dirname(__file__))

    name = 'furniturechoice-ebay.co.uk'

    def __init__(self, *args, **kwargs):
        super(FurnitureChoiceEbaySpider, self).__init__()
        self._csv_file = os.path.join(self.HERE, 'furniturechoice.csv')
        self._exclude_sellers = ['furniturechoiceuk']
        self._search_fields = ['Title']
        self._all_vendors = False
        self._look_related = True
        self._look_related_not_items = True
        self._meta_fields = [('sku', 'ProductCode'),
                             ('identifier', 'ProductCode'),
                             ('name', 'Title'),
                             ('price', 'price')]
        self._match_fields = ('sku', 'identifier')
        self._try_replacing = [('king size', 'kingsize'),
                               ('posturecare', 'posture care'),
                               ('posturecare', 'postureform'),
                               ('posturecare', 'posture form'),
                               ('postureform', 'posture form'),
                               ('posture form', 'postureform'),
                               ('sensaform', 'sensa form'),
                               ('super king size', 'super king'),
                               ('essentials', ''),
                               (' 1 ', ' one '),
                               (' 2 ', ' two '),
                               (' 3 ', ' three '),
                               (' 4 ', ' four '),
                               (' 5 ', ' five '),
                               (' 6 ', ' six '),
                               (' 7 ', ' seven '),
                               (' 8 ', 'eight'),
                               (' 9 ', 'nine'),
                               ('with', '')]
        self._check_diff_ratio = True
        self._ratio_accuracy = 95

    def _clean_search(self, search):
        redundant = (('&', ''), ('/', ''), ('(', ''), (')', ''), ('-', ' '),
                     (':', ' '), ('[', ''), (']', ''), ('{', ''), ('}', ''))
        for replacement in redundant:
            search = search.replace(replacement[0], replacement[1])
        return search

from basespider import BaseMonsterGroupEBaySpider


class GadgetGagaSpider(BaseMonsterGroupEBaySpider):
    name = 'monster_group-ebay-gadgetgaga'

    ebay_store = 'gadgetgaga'
    collect_stock = True

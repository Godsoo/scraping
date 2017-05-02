from basespider import BaseMonsterGroupEBaySpider


class HiralishaSpider(BaseMonsterGroupEBaySpider):
    name = 'monster_group-ebay-hiralisha'

    ebay_store = 'hiralisha'
    collect_stock = True

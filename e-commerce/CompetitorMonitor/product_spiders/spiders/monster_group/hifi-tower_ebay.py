from basespider import BaseMonsterGroupEBaySpider


class HifiTowerSpider(BaseMonsterGroupEBaySpider):
    name = 'monster_group-ebay-hifi-tower'

    ebay_store = 'hifi-tower'
    collect_stock = True

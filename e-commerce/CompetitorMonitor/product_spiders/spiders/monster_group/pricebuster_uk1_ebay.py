from basespider import BaseMonsterGroupEBaySpider


class PriceBusterSpider(BaseMonsterGroupEBaySpider):
    name = 'monster_group-ebay-pricebuster_uk1'

    ebay_store = 'pricebuster_uk1'
    collect_stock = True

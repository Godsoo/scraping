from basespider import BaseMonsterGroupEBaySpider


class JakanaTradingSpider(BaseMonsterGroupEBaySpider):
    name = 'monster_group-ebay-jakanatrading'

    ebay_store = 'jakanatrading'
    collect_stock = True

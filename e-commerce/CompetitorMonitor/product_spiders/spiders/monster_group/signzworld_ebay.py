from basespider import BaseMonsterGroupEBaySpider


class SignzWorldSpider(BaseMonsterGroupEBaySpider):
    name = 'monster_group-ebay-signzworld'

    ebay_store = 'signzworld'
    collect_stock = True

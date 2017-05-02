from basespider import BaseMonsterGroupEBaySpider


class AstloyalSpider(BaseMonsterGroupEBaySpider):
    name = 'monster_group-ebay-astloyal'

    ebay_store = 'astloyal'
    collect_stock = True

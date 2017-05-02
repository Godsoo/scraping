from basespider import BaseMonsterGroupEBaySpider


class UkHomeShoppinSpider(BaseMonsterGroupEBaySpider):
    name = 'monster_group-ebay-ukhomeshoppin'

    ebay_store = 'ukhomeshoppin'
    collect_stock = True

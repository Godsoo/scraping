from basespider import BaseMonsterGroupEBaySpider


class Comms2GoSpider(BaseMonsterGroupEBaySpider):
    name = 'monster_group-ebay-comms2go'

    ebay_store = 'comms2go'
    collect_stock = True

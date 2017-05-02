from basespider import BaseMonsterGroupEBaySpider


class ClearanceCentreSpider(BaseMonsterGroupEBaySpider):
    name = 'monster_group-ebay-clearance_centre_123'

    ebay_store = 'clearance_centre_123'
    collect_stock = True

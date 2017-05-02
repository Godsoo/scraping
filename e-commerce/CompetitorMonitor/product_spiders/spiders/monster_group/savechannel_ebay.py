from basespider import BaseMonsterGroupEBaySpider


class SaveChannelSpider(BaseMonsterGroupEBaySpider):
    name = 'monster_group-ebay-savechannel'

    ebay_store = 'savechannel'
    collect_stock = True

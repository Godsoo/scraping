from basespider import BaseMonsterGroupEBaySpider


class AndrewJamesSpider(BaseMonsterGroupEBaySpider):
    name = 'monster_group-ebay-andrewjamesdirect'

    ebay_store = 'andrewjamesdirect'
    collect_stock = True

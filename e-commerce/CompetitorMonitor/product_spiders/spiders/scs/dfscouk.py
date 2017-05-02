# -*- coding: utf-8 -*-

import os
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider
from product_spiders.config import DATA_DIR


class DfsSpider(SecondaryBaseSpider):
    name = "scs-dfs.co.uk"
    allowed_domains = ('dfs.co.uk', )
    start_urls = ['http://www.dfs.co.uk/']

    csv_file = os.path.join(DATA_DIR, 'dfs.co.uk_products.csv')
    is_absolute_path = True

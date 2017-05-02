# -*- coding: utf-8 -*-
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class RsOnlineSpider_B(SecondaryBaseSpider):
    name = 'arco-b-rs-online.com'
    allowed_domains = ['rs-online.com']
    start_urls = ('http://uk.rs-online.com/web/op/all-products/',)

    csv_file = 'arco_a/rsonline_crawl.csv'

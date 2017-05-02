import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

import csv

from product_spiders.items import Product, ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class TowEquipeEbaySpider(BaseSpider):
    name = 'towequipe-ebay.co.uk'
    allowed_domains = ['www.ebay.co.uk']
    start_urls = ('http://www.ebay.co.uk/',)

    def __init__(self, *args, **kwargs):
        super(TowEquipeEbaySpider, self).__init__(*args, **kwargs)

        # parse the csv file to get the product ids
        csv_file = csv.reader(open(os.path.join(HERE, 'products.csv')))
        csv_file.next()
        self.product_ids = {}

        for row in csv_file:
            ids = set()
            ids.add(row[0])
            ids.add(row[2])
            self.product_ids[row[0]] = row[2]

    def start_requests(self):
        for sku, data in self.product_ids.items():
            self.log("sku = %s, search id = %s" % (sku, data))
            url = 'http://www.ebay.co.uk/sch/i.html?_nkw=witter+' + data + '&LH_TitleDesc=1&_in_kw=1&_ex_kw=&_sacat=0&_okw=&_oexkw=&_adv=1&_udlo=&_udhi=&_ftrt=901&_ftrv=1&_sabdlo=&_sabdhi=&_samilow=&_samihi=&_sadis=200&_fpos=&LH_SALE_CURRENCY=0&_fss=1&_fsradio=%26LH_SpecificSeller%3D1&_saslop=2&_sasl=towbarman01&_sop=2&_dmd=1&_ipg=200&LH_ItemCondition=3'
            yield Request(url, meta = {'sku': sku}, dont_filter=True)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        first_item = hxs.select('//div[@id="ResultSetItems"]//table[1]')
        if first_item:
            product_loader = ProductLoader(item=Product(), selector=first_item)
            product_loader.add_value('sku', response.meta['sku'])
            product_loader.add_value('identifier', response.meta['sku'])
            product_loader.add_xpath('name', './/div[@class="ittl"]/a/text()')
            product_loader.add_xpath('url', './/div[@class="ittl"]/a/@href')
            product_loader.add_xpath('price', './/div[@itemprop="price"]/text()')
            yield product_loader.load_item()

import re
import csv
import os
import copy
import shutil

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.http.cookies import CookieJar
from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.spiders.BeautifulSoup import BeautifulSoup

HERE = os.path.abspath(os.path.dirname(__file__))

class ArcoSpider(BaseSpider):
    name = 'arco.co.uk'
    allowed_domains = ['arco.co.uk']

    def start_requests(self):
        with open(os.path.join(HERE, 'arco_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield Request(row['url'], meta={'sku': row['sku']}, dont_filter=True, callback=self.parse_product)

    def parse(self, response):
        pass
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        sku = response.meta['sku']
        # brand = response.meta['brand'].strip()
        category =  hxs.select(u'//div[@id="bcrumb"]/p/text()')[-1].extract().replace(u'&gt;', u'').replace(u'>', u'').strip()
        image_url = hxs.select(u'//div[@id="imageholder"]//img[@name="lpic"]/@src')[0].extract()
        image_url = urljoin_rfc(get_base_url(response), image_url)

        options = hxs.select(u'//table[@class="producttbl"]//tr[not(child::th)]')
        for option in options:
            site_sku = option.select(u'./td[1]/text()')[0].extract().strip()
            log.msg(u'site_sku: %s == sku: %s' % (site_sku, sku))
            if site_sku == sku:
                name = option.select(u'./td[2]/strong/text()')[0].extract()
                # if not brand.lower() in name.lower():
                    # name = u'%s %s' % (brand, name)
                price = option.select(u'./td[4]/div/text()')[0].extract()
                loader = ProductLoader(item=Product(), selector=hxs)
                loader.add_value('category', category)
                loader.add_value('name', name)
                # loader.add_value('brand', brand)
                loader.add_value('url', response.url)
                loader.add_value('price', price)
                loader.add_value('image_url', image_url)
                loader.add_value('sku', sku)
                loader.add_value('identifier', sku)
                yield loader.load_item()
                break

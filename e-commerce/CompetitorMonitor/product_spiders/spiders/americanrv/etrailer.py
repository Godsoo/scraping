import re
import os
import logging

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse

import csv

from product_spiders.items import Product, ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class EtrailerSpider(BaseSpider):
    name = 'etrailer.com'
    allowed_domains = ['www.etrailer.com']
    start_urls = ('http://www.etrailer.com/',)

    def __init__(self, *args, **kwargs):
        super(EtrailerSpider, self).__init__(*args, **kwargs)
        csv_file = csv.reader(open(os.path.join(HERE, 'americanrv_products.csv')))
        csv_file.next()
        self.product_ids = {}
        self._idents = []

        for row in csv_file:
            ids = set()
            ids.add(row[0])
            self.product_ids[row[0]] = {'mfrgid': row[2], 'ids': frozenset(ids)}

    def start_requests(self):
        for sku, data in self.product_ids.items():
            for id in data['ids']:
                url = 'http://accessories.etrailer.com/search?w=' + re.sub(' ', '+', id)
                req = Request(url, meta={'sku': sku, 'mfrgid': data['mfrgid']})
                yield req

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        products = hxs.select('//div[@class="summaryboxsearch"]')
        if products:
            logging.error("Found products")
        for product in products:
            site_mfrgid = product.select('.//span[@class="floatl sli_grid_code"]/text()').extract()
            if site_mfrgid:
                mfrgid = response.meta['mfrgid'].lower()
                site_mfrgid = site_mfrgid[0].strip().lower()
                if not re.search(r".*[^\d]%s\s*$" % mfrgid, site_mfrgid) and \
                   not re.search(r"^%s\s*$" % mfrgid, site_mfrgid):
                    continue

            url = product.select(u'.//p[@class="mtext nobreak"]/a/@title').extract()[0]
            yield Request(
                url,
                meta=response.meta,
                callback=self.parse_product
            )

        if not products:
            logging.error("No products found")
            yield Request(
                response.url,
                meta=response.meta,
                callback=self.parse_product,
                dont_filter=True
            )

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)
        logging.error("Parsing single product page")

        name = hxs.select(u'//div[@class="indentl orderbox"]//h1/text()').extract()
        if not name:
            name = hxs.select(u'//h1[@property="v:name"]/text()').extract()
        if not name:
            logging.error("NO NAME!! %s" % response.url)
            return
        name = name[0].strip()

        url = response.url

        price = hxs.select(u'//p[@class="strong"]/span/text()').extract()
        if not price:
            logging.error("NO PRICE!! %s" % response.url)
        price = price[0].strip()

        sku = response.meta['sku']

        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_value('name', name)
        product_loader.add_value('price', price)
        product_loader.add_value('url', url)
        product_loader.add_value('sku', sku)

        brand = hxs.select("//div[@class='floatl']/img[1]/@alt").extract()[0]

        search_brand = " ".join(response.meta['sku'].split(" ")[:-1])

        site_mfrgid = hxs.select('//div[@class="floatl"]/p/strong/text()').extract()
        if site_mfrgid:
            site_mfrgid = site_mfrgid[0].strip().lower()
            mfrgid = response.meta['mfrgid'].lower()
            if mfrgid in site_mfrgid and search_brand.lower() in brand.lower():
                product_loader.add_value('identifier', site_mfrgid)
                yield product_loader.load_item()

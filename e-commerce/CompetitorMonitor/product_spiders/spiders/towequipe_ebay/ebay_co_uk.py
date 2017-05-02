import os
import csv
import logging
import urllib2
import re
from urlparse import urlparse, parse_qs

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from product_spiders.items import Product, ProductLoader

from items import TowequipeEbayMeta

HERE = os.path.abspath(os.path.dirname(__file__))

class TowEquipeEbaySpider(BaseSpider):
    name = 'towequipe_ebay-ebay.co.uk'
    allowed_domains = ['www.ebay.co.uk']
    start_urls = ('http://www.ebay.co.uk/',)

    items = []

    def __init__(self, *a, **kw):
        super(TowEquipeEbaySpider, self).__init__(*a, **kw)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

        self.skus = []

        if os.path.exists(os.path.join(HERE, 'ebay_towequipe_products.csv')):
            # parse the csv file to get the product ids
            csv_file = csv.DictReader(open(os.path.join(HERE, 'ebay_towequipe_products.csv')))
            csv_file.next()

            for row in csv_file:
                self.skus.append(row['sku'])

    def spider_idle(self, spider):
        if self.items:
            request = Request(self.start_urls[0], dont_filter=True, callback=self.closing_parse)
            self._crawler.engine.crawl(request, self)

    def closing_parse(self, response):
        self.log("Processing items after finish")
        items_dict = {}
        items = sorted(self.items, key=lambda x: x['name'])
        for item in items:
            if item['sku'] in items_dict:
                old_item = items_dict[item['sku']]
                if item['price'] < old_item['price']:
                    items_dict[item['sku']] = item
            else:
                items_dict[item['sku']] = item

        self.items = []

        for sku, item in items_dict.items():
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', item['name'])
            loader.add_value('url', item['url'])
            loader.add_value('price', item['price'])
            loader.add_value('sku', item['sku'])
            loader.add_value('identifier', item['identifier'])
            product = loader.load_item()

            metadata = TowequipeEbayMeta()
            metadata['seller_id'] = item['seller_id']

            product['metadata'] = metadata
            yield product

    def start_requests(self):
        for sku in self.skus:
            self.log("sku = %s" % sku)
            url = 'http://www.ebay.co.uk/sch/i.html?_nkw=witter+' + urllib2.quote(sku) + '&LH_TitleDesc=1&_in_kw=1&_ex_kw=&_sacat=0&_okw=&_oexkw=&_adv=1&_udlo=&_udhi=&_ftrt=901&_ftrv=1&_sabdlo=&_sabdhi=&_samilow=&_samihi=&_sadis=200&_fpos=&LH_SALE_CURRENCY=0&_fss=1&_fsradio=%26LH_SpecificSeller%3D1&_saslop=2&_sasl=towbarman01&_sop=2&_dmd=1&_ipg=200&LH_ItemCondition=3'
            yield Request(url, meta={'sku': sku}, dont_filter=True)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        total_count = hxs.select("//span[@class='smuy']/span[contains(@class,'countClass')]/text()").extract()
        if not total_count:
            logging.error("Total count not found!!!")
            return
        total_count = int(total_count[0].replace(",", ""))

        for p in range(1, total_count / 30 + 1 + 1):
            url = response.url + "&_pgn=" + str(p)
            yield Request(
                url,
                callback=self.parse_product_list,
                dont_filter=True,
                meta=response.meta
            )
            break

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        limit = 30

        for i, url in enumerate(hxs.select("//a[@itemprop='name']/@href").extract()):
            if i >= limit:
                break
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(
                url,
                callback=self.parse_product,
                meta=response.meta
            )

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        url = response.url

        name = hxs.select("//*[@itemprop='name']/text()").extract()
        if not name:
            logging.error("NO NAME!!! %s" % response.url)
            return
        name = name[0]

        price = hxs.select("//*[@itemprop='price']/text()").extract()
        if not price:
            logging.error("NO PRICE!!! %s, %s" % (name, response.url))
            return
        price = price[0]

        seller_id = hxs.select("//*[@class='mbg-nw']//text()").extract()
        if not seller_id:
            logging.error("NO SELLER ID!!! %s, %s" % (name, response.url))
            return
        seller_id = seller_id[0]

        sku = None
        if hxs.select("//td[contains(text(), 'MPN')]"):
            sku = hxs.select("//td[contains(text(), 'MPN')]")[0].select("following-sibling::td/text()[1]").extract()
        elif hxs.select("//td[contains(text(), 'Part Manufacturer Number')]"):
            sku = hxs.select("//td[contains(text(), 'Part Manufacturer Number')]")[0].select("following-sibling::td/text()[1]").extract()

        if not sku:
            sku = hxs.select("//td[*/*/*/text()='Part Number']/../td[last()]//text()").extract()
        if not sku:
            sku = hxs.select("//div[@id='desc_div']//div/span/text()").extract()
        if not sku:
            sku = "".join(hxs.select("//td[text()='Part Number']/../td[last()]//text()").extract()).strip()
            if sku:
                sku = sku.split(" ")[0]

        matched = False
        search_sku = response.meta['sku'].lower()
        if sku:
            if type(sku) == list:
                sku = sku[0]
            sku = sku.strip()
            if sku.lower() == search_sku.lower():
                matched = True
        else:
            if re.search(r"([\s(]%s\s*\)?)" % search_sku, name, re.U | re.I):  # search for sku in name
                sku = search_sku
                matched = True
            desc = "".join(hxs.select("//div[@id='desc_div']//text()").extract())
            if re.search(r"(\s%s\s)" % search_sku, desc, re.U | re.I):  # search for sku in product description
                sku = search_sku
                matched = True

        if not matched:
            logging.error("Product not matched: %s" % name)
            if sku:
                logging.error("SKU of product is not equal to search SKU!!!")
                logging.error("Found: '%s', searched: '%s'" % (sku, response.meta['sku']))
                return
            else:
                logging.error("NO SKU!!! %s, %s, %s" % (name, seller_id, response.url))
                return

        sku = response.meta['sku'].lower()

        scheme, netloc, path, params, query, fragment = urlparse(response.url)
        item_hash = parse_qs(query)['hash'][0]
        identifier = sku + '_' + seller_id + '_' + item_hash

        product = {
            'name': name,
            'url': url,
            'price': price,
            'sku': sku,
            'identifier': sku,
            'seller_id': seller_id
        }

        if not product in self.items:
            self.items.append(product)

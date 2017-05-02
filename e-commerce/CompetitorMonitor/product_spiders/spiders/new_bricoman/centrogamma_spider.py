import os
import re
import json
import csv
import urlparse

from copy import deepcopy

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy.exceptions import DontCloseSpider

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class CentroGammaSpider(BaseSpider):
    name = 'newbricoman-centrogamma.com'
    allowed_domains = ['centrogamma.com']

    start_urls = ['http://www.centrogamma.com/catalogo']


    def __init__(self, *args, **kwargs):
        super(CentroGammaSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.process_products, signals.spider_idle)

        self.collect_products = []
        self.sync_calls = False

    def process_products(self, spider):
        if spider.name == self.name:
            if self.collect_products and not self.sync_calls:
                self.sync_calls = True
                product = self.collect_products[0]
                req = Request(product['add_cart'],
                              dont_filter=True, 
                              callback=self.parse_cart,
                              meta={'collect_products':self.collect_products[1:], 
                                    'product': product})

                log.msg('SEND REQ')
                self._crawler.engine.crawl(req, self)
                raise DontCloseSpider

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@id="listaSezioni"]/div/a/@href').extract()
        for category in categories:
            cat_url = urljoin_rfc(base_url, category)
            yield Request(cat_url)

        sub_categories = hxs.select('//div[@class="contentGruppi"]/div/div[@class="nome"]/a/@href').extract()
        for sub_category in sub_categories:
            cat_url = urljoin_rfc(base_url, sub_category)
            yield Request(cat_url)

        products = hxs.select('//div[@class="articolo"]')
        if products:
            for product in products:
                l = ProductLoader(item=Product(), selector=product)
                #l.add_xpath('name', 'h2/a/b/text()')
                url = product.select('.//h2/a/@href').extract()
                url = urljoin_rfc(base_url, url[0])
                l.add_value('url', url)
                l.add_value('identifier', re.search('art/(\d+)_', url).group(1))
                l.add_xpath('sku', 'p[@class="codfor"]/strong/text()')
                l.add_xpath('brand', 'p[@class="marca"]/img/@alt')
                image_url = product.select('div[@class="img"]/a/img/@src').extract()
                image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''
                l.add_value('image_url', image_url)
                category = hxs.select('//div[@class="gruppo"]/text()').extract()[0].strip()
                l.add_value('category', category)
                price = product.select('p[@class="prezzo"]/text()').extract()
                price = extract_price_eu(price[-1]) if price else 0
                l.add_value('price', price)
                if price<=0:
                    l.add_value('stock', 0)
                item = l.load_item()
                yield Request(item['url'], callback=self.parse_product, meta={'item': item})

        next = hxs.select('//a[@class="next"]').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[-1]))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        item = deepcopy(response.meta['item'])
        
        name = hxs.select('//head/title/text()').extract()
        if name:
            name = name[0].replace(' - Centrogamma', '')
        else:
            name = hxs.select('//p[@class="desc"]/text()').extract()[0]
        item['name'] = name
        add_cart = hxs.select('//a[@id="addCarrello"]/@href').extract()
        add_cart = urljoin_rfc(base_url, add_cart[0]) if add_cart else None
        if add_cart:
            product = {'add_cart': add_cart, 'item': item}
            self.collect_products.append(product)

    def parse_sync_shipping(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        meta = response.meta
        collect_products = meta['collect_products']
        if collect_products:
            product = collect_products[0]
            req = Request(product['add_cart'],
                          dont_filter=True, 
                          callback=self.parse_cart,
                          meta={'collect_products':collect_products[1:], 
                                'product': product})
            yield req

    def parse_cart(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
     
        meta = response.meta
        
        yield Request('http://www.centrogamma.com/checkout',
                      dont_filter=True, 
                      callback=self.parse_shipping_cost, 
                      meta=meta)

    def parse_shipping_cost(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
 
        meta = response.meta
        item = deepcopy(meta['product']['item'])
        shipping_cost = hxs.select('//tr[@class="totali sped"]/td[@class="cella importo"]/text()').extract()
        shipping_cost = shipping_cost[0] if shipping_cost else 0
        item['shipping_cost'] = extract_price_eu(shipping_cost)
        yield item
        remove_item = urljoin_rfc(base_url, hxs.select('//td[@class="cella modifica"]/a/@href').extract()[0])
        yield Request(remove_item, 
                      callback=self.parse_sync_shipping, 
                      dont_filter=True,
                      meta={'collect_products': meta['collect_products']})
        

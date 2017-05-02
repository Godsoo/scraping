import os
import csv
import cStringIO

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import TakeFirst, Compose
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.utils.url import urljoin_rfc
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader
from decimal import Decimal
import re

from product_spiders.base_spiders.matcher import Matcher
#import pprint



HERE = os.path.abspath(os.path.dirname(__file__))


class TrovaprezziSpider(BaseSpider):
    name = u'trovaprezzi.it'
    allowed_domains = [u'trovaprezzi.it']
    start_urls = [u'http://www.trovaprezzi.it/prezzi_elettronica-elettricita.aspx']

    items = []

    def __init__(self, *args, **kwargs):
        super(TrovaprezziSpider, self).__init__(*args, **kwargs)
        self.matcher = Matcher(self.log)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def start_requests(self):
        with open(os.path.join(HERE, 'product_list.csv')) as f:
            reader = csv.DictReader(cStringIO.StringIO(f.read()))
            for row in reader:
                meta = {'sku': row['model'], 
                        'identifier': row['ean'],
                        'brand': row['brand'], 
                        'name': row['name']}

                if row['model']:
                    search = row['brand'] + '+' + row['model']
                    meta['model_search'] = True
                    url = 'http://www.trovaprezzi.it/categoria.aspx?libera='+search+'&id=-1&prezzomin=&prezzomax='
                else:
                    url = 'http://www.trovaprezzi.it/categoria.aspx?libera=' + row['name'].replace(' ', '+') + '&id=-1&prezzomin=&prezzomax='
                yield Request(url, meta=meta)

    def spider_idle(self, spider):
        if self.items:
            request = Request(self.start_urls[0], dont_filter=True, callback=self.closing_parse)
            self._crawler.engine.crawl(request, self)

    def closing_parse(self, response):
        self.log("Processing items after finish")
        items_dict = {}
        items = sorted(self.items, key=lambda x: x['sku'])
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
            loader.add_value('category', item['category'])
            loader.add_value('brand', item['brand'])
            loader.add_value('identifier', item['identifier'])
            loader.add_value('dealer', item['dealer'])
            loader.add_value('image_url', item['image_url'])
            product = loader.load_item()
            yield product
      
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        meta = response.meta

        relevant_categories = hxs.select('//div[@class="catsMI"]/div/a/@href').extract()
        for category in relevant_categories:
            yield Request(urljoin_rfc(base_url, category), meta=meta)

        products = hxs.select('//table[@id="productlist-table"]/tbody/tr')
        if not products and meta.get('model_search', False):
            url = 'http://www.trovaprezzi.it/categoria.aspx?libera=' + meta['name'].replace(' ', '+') + '&id=-1&prezzomin=&prezzomax='
            meta['model_search'] = False
            yield Request(url, meta=meta)
        else:
            category = hxs.select('//div[@id="divTitle"]/h1/text()').extract()[0]
            pr = None
            for product in products:
                name = product.select('td[@class="descCol"]/a/b/text()').extract()[0]
                if self.match_name(meta['name'], name, match_threshold=70):
                    loader = ProductLoader(item=Product(), selector=product)
                    image_url = product.select('td[@class="imgCol"]/a/img/@src').extract()
                    if image_url:
                        image_url = urljoin_rfc(base_url, image_url[0])
                    else:
                        image_url = ''
                    loader.add_value('image_url', image_url)
                    loader.add_xpath('dealer', 'td[@class="mercCol"]/a/img/@alt')
                    loader.add_xpath('name', 'td[@class="descCol"]/a/b/text()')
                    loader.add_value('category', category)
                    loader.add_value('sku', response.meta.get('sku'))
            
                    url = product.select('td[@class="descCol"]/a/@href').extract()[0]
                    loader.add_value('url', urljoin_rfc(base_url, url))
            
                    price = product.select('td[@class="prodListPrezzo"]/text()').extract()[0].strip().replace('.','').replace(',', '.')
                    loader.add_value('price', price)
                    shipping_cost = product.select('td[@class="prodListPrezzo"]/'+
                                                   'span[@class="deliveryCost nobr"]/'+
                                                   'text()').extract()[0].strip().replace('.','').replace(',', '.')
                    loader.add_value('shipping_cost', shipping_cost)
                    loader.add_value('identifier',  response.meta.get('identifier'))

                    if loader.get_output_value('price') and (pr is None or pr.get_output_value('price') >
                                                                   loader.get_output_value('price')):
                        pr = loader
            if pr:
                item = pr.load_item()
                if not item in self.items:
                    self.items.append(item)

    def match_name(self, search_name, new_item, match_threshold=90, important_words=None):
        r = self.matcher.match_ratio(search_name, new_item, important_words)
        return r >= match_threshold

        
            

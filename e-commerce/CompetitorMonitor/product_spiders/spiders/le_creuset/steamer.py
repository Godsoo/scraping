import json
import re
import os
import shutil
import itertools
from scrapy import signals
from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher

from lecreusetitems import LeCreusetMeta

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class SteamerSpider(BaseSpider):
    name = 'lecreuset-steamer.co.uk'
    allowed_domains = ['steamer.co.uk']
    start_urls = ['http://www.steamer.co.uk/brands/le_creuset?sort=date_desc&layout=grid&searchterm=&format=html&page=1&task=view_items&noMeta=true&clipMode=cliptop']

    def _start_requests(self):
#yield Request('http://www.steamer.co.uk/brands/le_creuset/le_creuset_2-handle_grill_black.htm', callback=self.parse_product)
#yield Request('http://www.steamer.co.uk/brands/le_creuset/le_creuset_cooler_sleeve_-_cerise__.htm', callback=self.parse_product)
#        yield Request('http://www.steamer.co.uk/brands/le_creuset/le_creuset_table_corkscrew_black.htm', callback=self.parse_product)
        yield Request('http://www.steamer.co.uk/brands/le_creuset/le_creuset_tea_bag_holder.htm', callback=self.parse_product)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//li[@class="prod"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_product)
        for url in hxs.select('//div[@class="pagination"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        childMap = json.loads(re.search('\'childMap\': (.*),', response.body).group(1))
        prices = json.loads(re.search('\'prices\': (.*),', response.body).group(1))
        skus = json.loads(re.search('\'skus\': (.*),', response.body).group(1))
        stockStatuses = json.loads(re.search('\'stockStatuses\': (.*),', response.body).group(1))

        selects = []
        for sel in hxs.select('//div[@class="product-options"]//select'):
            s = []
            for opt in sel.select('.//option'):
                if opt.select('./@value').extract()[0]:
                    s.append((opt.select('./@value').extract()[0], opt.select('./text()').extract()[0],))
            if s:
                selects.append(s)

        if not selects:
            selects = [[('', ''), ('%', '')]]

        for k, v in list(childMap.items()):
            if '_%' in k:
                childMap[k.replace('_%', '')] = v

        found = False
        for c in itertools.product(*selects):
            key = [x[0] for x in c]
            name = [x[1] for x in c]
            code = childMap.get('_'.join(key))
            if not code: continue

            code = str(code)
            loader = ProductLoader(item=Product(), response=response)
            loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
            loader.add_value('name', name)
            loader.add_value('sku', skus[code])
            loader.add_value('identifier', skus[code])
            loader.add_value('price', prices[code][0]['purchase'])
            loader.add_value('url', response.url)
            loader.add_value('brand', 'Le Creuset')
            if 'In stock' in stockStatuses.get(code, ''):
                loader.add_value('stock', '1')
            else:
                loader.add_value('stock', '0')

            if loader.get_output_value('price') < 45:
                loader.add_value('shipping_cost', '4.95')
            else:
                loader.add_value('shipping_cost', '0')

            loader.add_xpath('category', '//div[@class="crumbs"]/a[position()>2]/text()')
            image_url = hxs.select('//div[@id="product-image"]//img/@src').extract()
            if image_url:
                loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[0]))

            item = loader.load_item()
            metadata = LeCreusetMeta()
            item['metadata'] = metadata

            found = True
            yield item

        if not found:
            self.log('No products on %s' % response.url)
        

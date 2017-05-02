from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)
from product_spiders.utils import extract_price
import re


class RazerCompTargetSpider(BaseSpider):
    name = 'razer_competition-target.com'
    allowed_domains = ['target.com']
    products = [{'url': 'http://www.target.com/p/logitech-g100-gaming-mouse-black-910-003533/-/A-14479754#prodSlot=medium_1_1&term=910-003533',
                 'sku': '910-003533', 'category': 'Mice', 'brand': 'Logitech'}]

    def start_requests(self):
        for product in self.products:
            yield Request(product['url'], meta={'product': product})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta
        loader = ProductLoader(item=Product(), response=response)
        name = hxs.select('//h2[contains(@class, "product-name")]/span/text()').extract()
        if not name:
            retry = int(response.meta.get('retry', 0))
            if retry < 10:
                retry += 1
                if '#' in response.url:
                    url = response.url.split('#')[0]
                else:
                    url = response.url
                meta = response.meta
                meta['retry'] = retry
                yield Request(url, callback=self.parse, meta=meta, dont_filter=True)
                return
            else:
                name = response.url.split('/')[4].replace('-', ' ')

        image_url = hxs.select('//*[@id="heroImage"]/@src').extract()
        identifier = hxs.select('//input[@id="omniPartNumber"]/@value').extract()
        if not identifier:
            identifier_m = re.search(r'A-(\d+)', response.url)
            if identifier_m:
                identifier = identifier_m.groups()[0]
            else:
                self.log("No product found: %s" % response.url)
                return
        else:
            identifier = identifier[0]
        tmp = hxs.select('//div[@id="price_main"]//span[@itemprop="price"]/text()').extract()
        if tmp:
            price = extract_price(tmp[0])
            loader.add_value('price', price)
        else:
            loader.add_value('price', '0.0')
            loader.add_value('stock', 0)

        loader.add_value('identifier', identifier)
        loader.add_value('name', name)
        loader.add_value('category', meta['product']['category'])
        loader.add_value('brand', meta['product']['brand'])
        loader.add_value('sku', meta['product']['sku'])
        loader.add_value('url', response.url)
        if image_url:
            loader.add_value('image_url', image_url[0])
        yield loader.load_item()
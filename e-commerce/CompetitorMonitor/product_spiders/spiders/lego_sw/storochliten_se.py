from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

import re


class StorochlitenSpider(BaseSpider):
    name = 'storochliten.se'
    allowed_domains = ['storochliten.se']
    start_urls = ['http://www.storochliten.se/varumarken/lego']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for product in hxs.select('//div[contains(@class, "productSpot")]//div[@class="name"]/a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        import re
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        loader.add_value('identifier', re.search(r'onclick="wl\.addProductItem\((\d+),', response.body).groups()[0])
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1//text()')
        sku = ''.join(hxs.select('//h1//text()').extract())
        try:
            loader.add_value('sku', re.search('(\d{3}\d*)', sku).groups()[0])
        except:
            self.log('No SKU for %s' % (response.url))
        loader.add_value('price', extract_price(''.join(hxs.select('//div[@class="price"]/text()').extract()).replace(' ', '')))
        if loader.get_collected_values('price') and loader.get_collected_values('price')[0] < 400:
            loader.add_value('shipping_cost', '49')
        loader.add_value('category', 'Lego')

        img = hxs.select('//div[@class="image"]//img/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('brand', 'lego')
#        loader.add_value('shipping_cost', '49')
        if re.search('ItemData .*Finns i lager.*', response.body):
            loader.add_value('stock', '1')
        else:
            loader.add_value('stock', '0')

        yield loader.load_item()

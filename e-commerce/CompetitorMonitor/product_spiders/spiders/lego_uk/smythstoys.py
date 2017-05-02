import re
import json

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)


class SmythsToysSpider(BaseSpider):
    name = 'legouk-smythstoys.com'
    allowed_domains = ['smythstoys.com']
    start_urls = ['http://www.smythstoys.com/uk/en-gb/toys/c-766/lego-bricks/?viewAll=True',
                  'http://www.smythstoys.com/uk/en-gb/toys/fashion-dolls/c-517/lego-friends/?ViewAll=True']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        pages = hxs.select('//ul[contains(@class, "pagination") and contains(@class, "pages") and contains(@class, "pagination-sm")]'
            '//a[contains(@class, "ajax-link") and not(contains(@class, "selected"))]/@href').extract()
        for page in pages:
            yield Request(urljoin_rfc(base_url, page))

        category_name = hxs.select('//h2[contains(@class, "category-name")]/text()').re(r'^(.*) \(\d+\)')
       
        products = hxs.select('//div[contains(@class, "listing-item") and contains(@class, "product")]')
        for product in products:

            loader = ProductLoader(item=Product(), selector=product)
            try:
                product_name = product.select('.//div[@class="product-description"]/a[contains(@class, "product-name")]/text()').extract()[0].strip()
            except:
                continue
            else:
                loader.add_value('name', product_name)
                loader.add_value('brand', 'LEGO')
                loader.add_xpath('url', './/div[@class="product-description"]/a[contains(@class, "product-name")]/@href', lambda u: urljoin_rfc(base_url, u[0]))
                loader.add_xpath('identifier', './/div[@class="product-description"]/a[contains(@class, "product-name")]/@href', re=r'/p-(\d+)/')
                loader.add_xpath('image_url', './/div[@class="image"]//img/@src')
                price = product.select('.//div[@class="pricing-container"]').re(r'([\d,.]+)')[-1]
                loader.add_value('price', price)
                sku = product_name.split(' ')[-1]
                if not sku:
                    self.log('ERROR: no SKU found! URL:{}'.format(response.url))
                else:
                    loader.add_value('sku', sku)
                loader.add_value('category', category_name)

                yield loader.load_item()

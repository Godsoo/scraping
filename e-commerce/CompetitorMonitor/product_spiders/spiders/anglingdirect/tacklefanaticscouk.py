from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.contrib.loader.processor import TakeFirst
from pprint import pformat
from decimal import Decimal
import re

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class TackleFanaticsSpider(BaseSpider):
    name = 'tacklefanatics.co.uk'
    allowed_domains = ['www.tacklefanatics.co.uk']
    start_urls = ['http://www.tacklefanatics.co.uk/sitemap.txt']


    def start_requests(self):
        start_url = 'http://www.tacklefanatics.co.uk'

        yield Request(start_url)

    def parse(self, response):
        categories = response.xpath('//div[@id="gb-shop-nav"]//a/@href').extract()
        for cat_link in categories:
            yield Request(response.urljoin(cat_link), callback=self.parse_categories)


    def parse_categories(self, response):
        categories = response.xpath('//a[contains(@href, "/cat/")]/@href').extract()
        for cat_link in categories:
            yield Request(response.urljoin(cat_link), callback=self.parse_products)

    def parse_products(self, response):
        products = response.xpath('//div[@class="gallery-item-content"]//h3/a/@href').extract()
        stocks = response.xpath('//div[@class="gallery-item-content"]//p[@class="stock-qty"]/text()[last()]').extract()
        stocks = [s.strip() for s in stocks]

        for i in range(0, len(products)):
            product = products[i]
            stock = stocks[i]
            url = response.urljoin(product)
            yield Request(url, callback=self.parse_product, meta={"stock": stock})

        subcats = response.xpath('//div[contains(@id, "sidebar")]//ul[@class="arrow-nav-list"]//a[contains(@href, "/cat/")]/@href').extract()
        for url in subcats:
            yield Request(response.urljoin(url), callback=self.parse_products)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        name_xpath = '//h1/text()'
        category_xpath = '//div[@id="breadcrumbs"]//a[last()]/text()'
        identifier = re.search('product/([0-9]+)', response.url).group(1)
        image_url = response.xpath('//div[@id="item-photos"]//div[contains(@class, "product-image")]/img/@src').extract()[0]

        product_options = {}
        options = hxs.select('//div[contains(@class, "product-list-item") and not(contains(@class, "list-itemtype-header"))]')
        for option in options:
            name = ' '.join(map(lambda x: x.strip() if x.strip() else '', option.select('.//p/span[@class="attribute-value"]/text()').extract())).strip()
            if name not in product_options.keys():
                option_identifier = option.select('.//h3/a/@href').re(r'item/(.*)/')[0]
                price = ''.join(option.select('.//span[contains(@class, "wd-price")]//span/text()').extract())
                product_options[name] = {'identifier': option_identifier,
                                         'price': price}

        for option_name, product_option in product_options.iteritems():
            loader = ProductLoader(response=response, item=Product())

            loader.add_value('identifier', product_option['identifier'])
            loader.add_value('shipping_cost', '4.99')
            name = hxs.select(name_xpath).extract()[0].strip()
            loader.add_value('name', name + ' ' + option_name)
            loader.add_value('image_url', image_url)

            #prices = [Decimal(re.search('[0-9.]+', p).group(0)) for p in prices]
            #price = min(prices)
            loader.add_value('price', product_option['price'])

            loader.add_value('url', response.url)
            loader.add_xpath('category', category_xpath)

            #self.log("Meta:")
            #self.log(pformat(response.meta))
            stock = re.search('([0-9+])', response.meta['stock'])

            if stock:
                loader.add_value('stock', stock.group(1))

    
            yield loader.load_item()

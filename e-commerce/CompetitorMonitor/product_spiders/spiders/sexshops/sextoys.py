import json

from scrapy import log

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from utils import extract_price

class SexToys(BaseSpider):
    name = 'sextoys.co.uk'
    allowed_domains = ['sextoys.co.uk']
    start_urls = ('http://www.sextoys.co.uk',)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)
        try:
            name = hxs.select('//div[@class="product-name"]/h1/text()').extract()[0]
            url = response.url

            price = hxs.select('//div[@class="product-view nested-container"]'
                               '//div[@class="price-box"]/span/span[@class="price"]/text()').extract()
            if not price:
                price = hxs.select('//div[@class="product-view nested-container"]'
                                   '//div[@class="price-box"]/p[@class="special-price"]'
                                   '/span[@class="price"]/text()').extract()

            sku = hxs.select('//tr[th/text()="SKU"]/td/text()').extract()[0]
            brand = hxs.select('//tr[th/text()="Manufacturer"]/td/text()').extract()[0]
            if price:
                price = extract_price(price[0])
            else:
                price = 0

            image_url = hxs.select('//a[@id="zoom1"]/img/@src').extract()
            if image_url:
                image_url = image_url[0]
            else:
                image_url = ''

            breadcrumb = hxs.select('//div[@class="grid-full breadcrumbs"]/ul/li/a/text()').extract()
            category = breadcrumb[-1]
            if "ESSENTIAL" in ''.join(breadcrumb).upper():
                opts = []
                for line in hxs.extract().split('\n'):
                    if '"options":[' in line:
                        opts = json.loads(line.split('"options":')[-1].split('}}')[0])

                if opts:
                    for opt in opts:
                        log.msg('CRAWL PRODUCT OPTIONS')
                        option_name = name + " - " + opt.get('label')
                        option_price = price + extract_price(opt.get('price'))
                        loader = ProductLoader(item=Product(), selector=hxs)
                        loader.add_value('url', url)
                        loader.add_value('name', option_name)
                        loader.add_value('price', option_price)
                        loader.add_value('sku', sku)
                        loader.add_value('brand', brand)
                        loader.add_value('image_url', image_url)
                        loader.add_value('identifier', sku + '-' + opt.get('label'))
                        loader.add_value('category', category)
                        stock = hxs.select('//p[@class="availability in-stock"]').extract()
                        if not stock:
                            loader.add_value('stock', 0)
                        yield loader.load_item()
                else:
                    loader = ProductLoader(item=Product(), selector=hxs)
                    loader.add_value('url', url)
                    loader.add_value('name', name)
                    loader.add_value('price', price)
                    loader.add_value('sku', sku)
                    loader.add_value('brand', brand)
                    loader.add_value('image_url', image_url)
                    identifier = hxs.select('//input[@name="product"]/@value').extract()[0]
                    loader.add_value('identifier', identifier)
                    loader.add_value('category', category)
                    stock = hxs.select('//p[@class="availability in-stock"]').extract()
                    if not stock:
                        loader.add_value('stock', 0)
                    yield loader.load_item()
            else:
                loader = ProductLoader(item=Product(), selector=hxs)
                loader.add_value('url', url)
                loader.add_value('name', name)
                loader.add_value('price', price)
                loader.add_value('sku', sku)
                loader.add_value('brand', brand)
                loader.add_value('image_url', image_url)
                identifier = hxs.select('//input[@name="product"]/@value').extract()[0]
                loader.add_value('identifier', identifier)
                loader.add_value('category', category)
                stock = hxs.select('//p[@class="availability in-stock"]').extract()
                if not stock:
                    loader.add_value('stock', 0)
                yield loader.load_item()
        except IndexError:
            return


    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//ul[@id="nav"]/li/ul/li/a/@href').extract()
        categories += hxs.select('//div[@id="MainMenu"]//a[contains(@class, "addarrow")]/@href').extract()
        for url in categories:
            url = urljoin_rfc(base_url, url)
            yield Request(url)

        next_page = hxs.select('//li[@class="next"]/a/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

        products = hxs.select('//li[@class="item"]/a/@href').extract()
        products += hxs.select('//h2[@class="product-name"]/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

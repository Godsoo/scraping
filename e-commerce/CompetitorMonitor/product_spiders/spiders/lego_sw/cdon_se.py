from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
import re


class CdonSeSpider(BaseSpider):
    name = 'cdon.se'
    allowed_domains = ['cdon.se']
    start_urls = ('http://cdon.se/lego/lego-spel/',
                  'http://cdon.se/lego/lego-film/',
                  'http://cdon.se/lego/lego-b%c3%b6cker/',
                  'http://cdon.se/lego/lego-leksaker/',
                  'http://cdon.se/lego/lego-barnkl%c3%a4der/',
                  'http://cdon.se/lego/lego-duplo/',
                  'http://cdon.se/search?category=0&q=LEGO',)
    errors = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        urls = hxs.select('//article[contains(@class, "product")]/div[@class="product-title-wrapper"]/a/@href').extract() or \
            hxs.select('//article[contains(@class, "product-2")]//a[contains(@class, "product-link")]/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        urls = hxs.select('//a[@class="show-more"]/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)

        # parse pagination
        urls = hxs.select('//ul[@class="pagination"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        try:
            identifier = re.search(r'(\d{3,}(-\d{3,})?)$', response.url).group(1)
        except:
            return

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_name = hxs.select('//h1[@itemprop="name"]/text()').extract()

        if not product_name:
            self.errors.append("No product name posibly wrong page on " + response.url)
            return

        product_name = product_name.pop()
        if not 'lego' in product_name.lower().strip():
            return

        image_url = hxs.select('//div[@class="product-image-container"]//img/@src').extract()[0]
        product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))
        product_loader.add_value('name', product_name)
        product_loader.add_value('url', response.url)
        product_loader.add_value('identifier', identifier)
        product_loader.add_value('sku', '')

        price = hxs.select('//span[@itemprop="price"]/text()') or \
                hxs.select('//div[@id="price-wrapper"]/div[@id="price-button-container"]//span[contains(@class, "price")]/text()') or \
                hxs.select('//div[@id="product-buy"]/div[@id="price-button-container"]//span[contains(@class, "price")]/text()')
        if price:
            price = price.extract()[0].strip().strip(' kr').replace(u'\xa0', '')
        product_loader.add_value('price', extract_price(price))
        product = product_loader.load_item()

        yield product

# from scrapy.spider import BaseSpider
from scrapy.contrib.spiders import SitemapSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from decimal import *


class SquiresshopSpider(SitemapSpider):
    name = 'squiresshop'
    allowed_domains = ['squires-shop.com']
    # start_urls = ('http://www.squires-shop.com/uk/',)

    sitemap_urls = ['http://www.squires-shop.com/sitemap/sitemap.xml']
    sitemap_rules = [
        ('/product/', 'parse_product'),
    ]

    ids = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # parse categories
        urls = hxs.select('//div[@id="nav-bar"]//a[@class="nav-cat-title"]/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_list)

    def parse_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # products
        urls = hxs.select('//div[@id="page"]//div[@class="product-container"]//div[@class="product-title"]/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        # pagination
        urls = hxs.select('//div[@class="paginator-container"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        option_urls = hxs.select('//div[@id="group-select"]//a[@class="grouped-product-container"]/@href').extract()
        if option_urls:
            for option_url in option_urls:
                yield Request(option_url, callback=self.parse_product2)
        for product in self.parse_product2(response):
            yield product

    def parse_product2(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_name = ' - '.join(filter(lambda s: s, map(unicode.strip,
            hxs.select('//h1[@id="product-title"]/text()|//h2[@id="product-caption"]/text()').extract())))
        if not product_name:
            return
        product_loader.add_value('name', product_name)
        image_url = hxs.select('//div[@id="product-image-container"]//img/@src').extract()
        if image_url:
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        product_loader.add_value('url', response.url)
        sku = hxs.select('//*[@itemprop="sku"]/text()').extract()[0]
        product_loader.add_value('sku', sku)
        product_loader.add_value('identifier', sku)
        price = hxs.select('//meta[@itemprop="price"]/@content').extract()
        price = extract_price(price[0].strip())
        product_loader.add_value('price', price)
        category = hxs.select('//div[@id="breadcrumb"]/a[1]/text()').extract()
        if category:
            product_loader.add_value('category', category[0])
        out_of_stock = hxs.select('//div[@class="product-stock-quantity" and contains(text(), "out of stock")]')
        if out_of_stock:
            product_loader.add_value('stock', 0)
        else:
            product_loader.add_value('stock', hxs.select('//div[@class="product-stock-quantity"]/text()').re(r'(\d+)'))
        if price >= Decimal("50"):
            product_loader.add_value('shipping_cost', 0)
        else:
            product_loader.add_value('shipping_cost', 2.95)
        product = product_loader.load_item()
        yield product

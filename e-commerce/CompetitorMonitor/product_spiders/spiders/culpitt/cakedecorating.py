from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from decimal import *


class CakedecoratingSpider(BaseSpider):
    name = 'thecakedecoratingcompany'
    allowed_domains = ['thecakedecoratingcompany.co.uk']
    start_urls = ('http://www.thecakedecoratingcompany.co.uk/catalog/',)
    ids = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        new_arrivals = hxs.select('//ul/li/a[contains(@title,"New Arrivals")]/@href').extract()
        if new_arrivals:
            yield Request(urljoin_rfc(base_url, new_arrivals[0]), callback=self.parse_list, meta={'cookiejar': 0})

        #parse categories
        urls = hxs.select('//div[@class="dropdown-body"]/ul/li/a/@href').extract()
        for i, url in enumerate(urls, 1):
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_list, meta={'cookiejar': i})

    def parse_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        urls = hxs.select('//ul[contains(@class, "listing")]/li/article/figure/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)
        if urls:
            #pagination
            next_page = hxs.select('//a[@title="Next"]/@href').extract()
            if next_page:
                yield Request(urljoin_rfc(base_url, next_page.pop()), callback=self.parse_list, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories = hxs.select('//ul[@class="nav--breadcrumb"]/li/a/text()')[1:].extract()
        product_loader = ProductLoader(item=Product(), selector=hxs)
        identifier = hxs.select('//p[@class="product__code"]/text()').extract()
        if identifier:
            identifier = identifier.pop().split(":").pop().strip()
            sku = identifier
            product_name = hxs.select('//h1/text()').extract().pop().strip()
            image_url = hxs.select('//div[@class="product__bg"]//img/@src').extract()
            product_loader.add_value('name', product_name)
            product_loader.add_value('url', response.url)
            for category in categories:
                product_loader.add_value('category', category.strip())
            product_loader.add_value('identifier', identifier)
            product_loader.add_value('sku', sku)
            price = hxs.select('//div[@class="product__details--full"]//span[@class="price"]/text()').extract()
            if not price:
                price = hxs.select('//div[@class="product__details--full"]//span[contains(@id, "product-price")]/text()').extract()
            price = extract_price(price.pop())
            product_loader.add_value('price', price)
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url.pop()))
            out_of_stock = hxs.select('//div[@class="product__details--full"]//p[contains(@class, "availability")]/span[contains(text(), "OUT OF STOCK")]')
            if out_of_stock:
                product_loader.add_value('stock', 0)
            if price >= Decimal("25"):
                product_loader.add_value('shipping_cost', 0)
            else:
                product_loader.add_value('shipping_cost', 2.50)
            product = product_loader.load_item()
            yield product

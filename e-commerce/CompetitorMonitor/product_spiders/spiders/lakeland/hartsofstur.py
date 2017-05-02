from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from urlparse import urljoin

from product_spiders.base_spiders import PrimarySpider
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

class LakelandAmazonSpider(PrimarySpider):
    name = 'hartsofstur'
    allowed_domains = ['hartsofstur.com']
    start_urls = ['http://www.hartsofstur.com']
    csv_file = 'lakeland_hartsofstur_as_prim.csv'

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for url in hxs.select('//ul[@class="dropdown"]//a/@href').extract():
            yield Request(urljoin(base_url, url), callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for url in hxs.select('//div[@class="section-list"]//a/@href').extract():
            yield Request(urljoin(base_url, url), callback=self.parse_category)

        products = hxs.select('//div[@id="SearchResults"]//a/@href').extract()
        products+= hxs.select('//div[@class="product-list"]//a/@href').extract()
        for url in products:
            if url == "Kitchen-Craft-Filled-Loaf-Proving-Basket--28-x-6.5cm-KCHMBBASKBAG__.html":
                #site error, duplicate product
                continue
            url = url.split('#')[0]
            yield Request(urljoin(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        box = hxs.select('//div[@class="prod-box"]')
        crumbs = hxs.select('//ul[@class="breadcrumbs"]')[0]
        loader = ProductLoader(selector=box, item=Product())
        loader.add_value('url', response.url)
        brand = crumbs.select('.//a[contains(text(), "Brands")]/../following-sibling::li[1]/a/text()').extract()
        loader.add_value('brand', brand)
        categories = crumbs.select('.//a/text()').extract()
        categories = [cat for cat in categories if "Brand" not in cat]
        loader.add_value('category', categories)
        image_url = hxs.select('//section[@id="one"]//@src').extract()
        if not image_url:
            yield Request(response.url, callback=self.parse_category, dont_filter=True)
            return
        loader.add_value('image_url', urljoin(base_url, image_url[0]))
        loader.add_xpath('name', './h1/text()')
        loader.add_xpath('identifier', '//*/@prodref')
        loader.add_xpath('sku', '//*/@prodref')
        if not box.select('//*[text()="In Stock" or text()="Low Stock"]'):
            loader.add_value('stock', 0)
        loader.add_xpath('price', './/span[@class="product-price"]/text()')
        product = loader.load_item()
        if product['price'] < 20:
            product['shipping_cost'] = 2
        elif product['price'] < 40:
            product['shipping_cost'] = 4.99
        yield product

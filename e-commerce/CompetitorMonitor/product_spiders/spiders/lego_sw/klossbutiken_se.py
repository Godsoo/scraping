from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
import re


class KlossbutikenSeSpider(BaseSpider):
    name = 'klossbutiken.se'
    allowed_domains = ['klossbutiken.se']
    start_urls = ('http://www.klossbutiken.se/hem-1',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        urls = hxs.select('//ul[@id="category-navigation"]//li[not (contains(@class, "has-subcategories"))]/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

        urls = hxs.select('//ul[@id="category-navigation"]//li[contains(@class, "has-subcategories")]/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url))

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//div[@class="product-wrapper"]')
        for product in products:
            product_loader = ProductLoader(item=Product(), selector=product)
            name = product.select('.//h3//text()').extract()[0]
            product_loader.add_value('name', name)
            sku = ''
            for match in re.finditer(r"([\d,\.]+)", name):
                if len(match.group()) > len(sku):
                    sku = match.group()
            product_loader.add_value('sku', sku)
            image_url = product.select('./div[@class="product-image"]//img/@data-original').extract()
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            price = product.select('./div[@class="product-price"]//span[@class="price-amount"]/text()').extract()[0].strip()\
                .strip(' Kr').replace('.', '')
            product_loader.add_value('price', extract_price(price))
            if product_loader.get_collected_values('price') and product_loader.get_collected_values('price')[0] < 1500:
                product_loader.add_value('shipping_cost', '49')
            buy_button = product.select('./div[@class="product-buttons"]/a[@class="buy-button"]')
            if not buy_button:
                product_loader.add_value('stock', 0)
            url = product.select('./div[@class="product-buttons"]/a[@class="button-info"]/@href').extract()[0]
            product_loader.add_value('url', urljoin_rfc(base_url, url))
            identifier = product.select('./div[@class="product-name"]//@data-productid').extract()[0]
            product_loader.add_value('identifier', identifier)
            product = product_loader.load_item()
            yield product

        pages = hxs.select('//a[@class="paging-link-box"]/@href').extract()
        for url in pages:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

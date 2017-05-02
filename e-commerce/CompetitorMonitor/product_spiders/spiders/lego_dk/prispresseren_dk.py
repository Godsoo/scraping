from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from scrapy.http import Request
import re


class PrispresserenDkSpider(BaseSpider):
    name = 'prispresseren.dk'
    allowed_domains = ['prispresseren.dk']
    start_urls = ('http://www.prispresseren.dk/sogeresultater?keyword=lego&Search=S%C3%B8g&option=com_redshop&view=search&layout=default&templateid=8&perpageproduct=75&search_type=name_number_desc&Itemid=447',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # parse categories
        urls = hxs.select('//ul[@class="joomla-nav_v"]//li/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

        for item in self.parse_product_list(response):
            yield item

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # pagination
        urls = hxs.select('//div[@class="category_pagination"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

        products = hxs.select('//div[@class="product_list_outside"]')
        for product in products:
            product_loader = ProductLoader(item=Product(), selector=product)
            name = product.select('.//h3/a/text()').extract()[0]
            product_loader.add_value('name', name)
            sku = ''
            for match in re.finditer(r"([\d,\.]+)", name):
                if len(match.group()) > len(sku):
                    sku = match.group()
            product_loader.add_value('sku', sku)
            image_url = product.select('.//div[@class="product_list_image"]//img/@src').extract()[0]
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))
            price = product.select('.//div[@class="product_list_price"]/span/text()').extract()[0]
            price = extract_price(price.strip().replace('.', '').replace('DKK ', '').replace(',', '.'))
            product_loader.add_value('price', price)
            if price > 200:
                product_loader.add_value('shipping_cost', 0)
            else:
                product_loader.add_value('shipping_cost', 25)
            stock = product.select('.//div[@class="product_stock"]//img/@src').extract()[0]
            if stock.endswith('red.jpg'):
                product_loader.add_value('stock', 0)

            identifier = product.select('.//img[contains(@id, "main_image")]/@id').extract()[0].replace('main_image', '')
            product_loader.add_value('identifier', identifier)
            url = product.select('.//h3/a/@href').extract()[0]
            product_loader.add_value('url', urljoin_rfc(base_url, url))
            product = product_loader.load_item()
            yield product

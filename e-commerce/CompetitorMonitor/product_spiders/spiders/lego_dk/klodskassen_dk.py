from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from scrapy.http import Request
import re


class KlodslandDkSpider(BaseSpider):
    name = 'klodskassen.dk'
    allowed_domains = ['klodskassen.dk']
    start_urls = ('http://www.klodskassen.dk/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #parse categories
        urls = hxs.select('//*[@id="ProductMenu_List"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #pagination
        urls = hxs.select('//div[@class="productlist-pager"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url.strip()), callback=self.parse_product_list)

        # products = hxs.select('//table[@class="ProductList_Custom_TBL"]/tr')
        products = hxs.select("//ul[@class='ProductList_Custom_UL']/li")
        for product in products:
            product_loader = ProductLoader(item=Product(), selector=product)
            name = product.select(".//div[@class='stock-message']/a/@title").extract()[0]
            product_loader.add_value('name', name)
            sku = ''
            for match in re.finditer(r"([\d]+)", name):
                if len(match.group()) > len(sku):
                    sku = match.group()
            product_loader.add_value('sku', sku)
            image_url = product.select('.//div[@class="image-td"]//img/@src').extract()[0]
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))
            try:
                price = product.select('.//div[@class="price-td"]/table//tr[3]/td[2]/text()').extract()[0]
            except IndexError:
                return
            price = extract_price(price.replace('.', '').replace(',', '.'))
            product_loader.add_value('price', price)
            if price < 400:
                product_loader.add_value('shipping_cost', 29)
            else:
                product_loader.add_value('shipping_cost', 0)
            identifier = product.select('.//input[@name="ProductID"]/@value').extract()[0]
            product_loader.add_value('identifier', identifier)
            url = product.select('.//div[@class="image-td"]/a/@href').extract()[0]
            product_loader.add_value('url', urljoin_rfc(base_url, url))
            in_stock = product.select('.//span[@class="buy-button"]/following-sibling::img/@src').extract()
            if not in_stock or not in_stock[0].endswith('instock.png'):
                product_loader.add_value('stock', 0)
            product = product_loader.load_item()
            yield product
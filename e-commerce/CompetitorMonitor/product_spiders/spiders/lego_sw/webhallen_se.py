from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
import re


class WebhallenSeSpider(BaseSpider):
    name = 'webhallen.se'
    allowed_domains = ['webhallen.com']
    start_urls = ('http://www.webhallen.com/se-sv/lek_och_gadgets/kampanjer/lego/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #parse categories
        urls = hxs.select('//*[@id="site_content_middle_page"]//div//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        products = response.xpath('//table[@class="productlist"]//tr[@class="prod_list_row"]')
        for product in products:
            product_loader = ProductLoader(item=Product(), selector=product)
            name = product.select('./td[2]/a/text()').extract()[0]
            product_loader.add_value('name', name)
            sku = ''
            for match in re.finditer(r"([\d,\.]+)", name):
                if len(match.group()) > len(sku):
                    sku = match.group()
            product_loader.add_value('sku', sku)
            image_url = product.select('./td[1]/img/@src').extract()[0].replace('/mini', '')
            product_loader.add_value('image_url', image_url)
            price = "".join(product.select('./td[4]/text()').extract()).strip().strip(' kr')
            product_loader.add_value('price', extract_price(price))
            product_loader.add_value('shipping_cost', '29')
            identifier = product.select('./td[5]/a/@whprodid').extract()[0]
            product_loader.add_value('identifier', identifier)
            url = product.select('./td[2]/a/@href').extract()[0]
            product_loader.add_value('url', urljoin_rfc(base_url, url))
            stock = product.select('./td[5]//a/text()').extract()[0].strip()
            if stock == 'Boka':
                product_loader.add_value('stock', 0)
            product = product_loader.load_item()
            yield Request(product['url'], callback=self.parse_product, meta={'product': product})
        #parse pagination
        urls = hxs.select('//*[@id="list_block_pagination"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

    def parse_product(self, response):
        
        product_loader = ProductLoader(item=response.meta['product'], response=response)

        categories = response.xpath('//span[@class="category"]/text()').extract()
        categories = filter(None, categories[0].split('/')) if categories else ''
        product_loader.add_value('category', categories)

        brand = response.xpath('//tr[td[contains(text(), "Utvecklare")]]/td[not(@class)]/text()').extract()
        brand = brand[0].strip() if brand else ''
        product_loader.add_value('brand', brand)

        yield product_loader.load_item()

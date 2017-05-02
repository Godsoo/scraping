from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from decimal import *


class CustomridersSpider(BaseSpider):
    name = 'customriders'
    allowed_domains = ['customriders.com']
    start_urls = ('http://www.customriders.com/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #parse categories
        urls = hxs.select('//*[@id="leftNavContainer"]//li/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_list)

    def parse_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #pagination
        urls = hxs.select('//div[@class="pageNavContainer"]//a/@href').extract()
        for url in urls:
            url = url.replace('sort=3, 3', '')
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_list)
        #products
        urls = hxs.select('//div[@class="productContainer"]//h5/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        image_url = hxs.select('//*[@id="productViewContainer"]/@src').extract()
        product_name = hxs.select('//*[@id="contentContainer"]/h3/text()').extract()[0]
        product_rows = hxs.select('//*[@id="productAvailabilityContainer"]//tr')
        category = hxs.select('//*[@id="frmProduct"]/option[@selected="selected" and @value!="0"]/preceding-sibling::option[contains(@value,"parent")]/text()').extract()
        if not category:
            category = hxs.select('//*[@id="frmProduct"]/option[@selected="selected" and contains(@value, "parent")]/text()').extract()
        category = category[-1] if category else ''
        first_row = True
        for row in product_rows:
            if first_row:
                first_row = False
                continue
            else:
                product_loader = ProductLoader(item=Product(), selector=row)
                avail1 = row.select('./td[3]/span/text()').extract()[0].strip()
                avail2 = row.select('./td[3]/text()').extract()[0].strip()
                if avail1 == 'Out of Stock':
                    if avail2 == 'Discontinued':
                        continue
                    else:
                        product_loader.add_value('stock', 0)
                sku = row.select('./td[1]/text()').extract()[0]
                product_loader.add_value('sku', sku)
                product_loader.add_value('identifier', sku)
                name = row.select('./td[2]/text()').extract()[0]
                price = row.select('./td[4]/strong/text()').extract()
                price = extract_price(price[0].strip())
                product_loader.add_value('price', price)
                product_loader.add_value('name', product_name + ' - ' + name)
                if price >= Decimal("30"):
                    product_loader.add_value('shipping_cost', 0)
                else:
                    product_loader.add_value('shipping_cost', 4)
                product_loader.add_value('url', response.url)
                product_loader.add_value('category', category)
                if image_url:
                    product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                product = product_loader.load_item()
                yield product
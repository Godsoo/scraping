import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url


class LajbanssonSpider(BaseSpider):
    name = 'lego_sw-lajbansson.se'
    allowed_domains = ['lajbansson.se']
    start_urls = ('http://www.lajbansson.se/lego-duplo',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        next_page = hxs.select('//div[@class="pager"]//li[@class="next"]//@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

        products = hxs.select('//h2[@class="product-name"]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_loader = ProductLoader(item=Product(), selector=hxs)

        product_loader.add_value('url', response.url)

        product_name = hxs.select('//div[@class="product-name"]/h1/text()').extract()[0]
        product_loader.add_value('name', product_name)

        image_url = hxs.select('//div[contains(@class, "img-box")]//img/@src').extract()[0]
        product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))

        identifier = hxs.select('//span[@class="sku"]/text()').extract()[0].strip()
        product_loader.add_value('identifier', identifier)

        #sku = re.search('(\d+)', identifier)
        #sku = sku.group(1) if sku else ''
        sku = identifier
        product_loader.add_value('sku', sku)

        #price = hxs.select('//span[starts-with(@id,"product-price")]//span[@class="price"]/text()').extract()
        price = hxs.select('//div[@class="product-type-data"]/div[@class="price-box"]//span[@class="price"]/text()').extract()
        price = price[-1].strip() if price else '0.00'
        product_loader.add_value('price', price.replace(',', '.').replace(' ', '').replace(u'\xa0', ''))
        if product_loader.get_collected_values('price') and product_loader.get_collected_values('price')[0] < 1000:
            product_loader.add_value('shipping_cost', '49')
        # category = hxs.select('').extract()
        # category = category[0].strip() if category else ''
        # product_loader.add_value('category', category)

        product_loader.add_value('brand', 'Lego')

        yield product_loader.load_item()

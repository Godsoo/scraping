from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url


class LekmerNlSpider(BaseSpider):
    name = 'lego_nl-lekmer.nl'
    allowed_domains = ['lekmer.nl']
    start_urls = ('http://lekmer.nl/lego/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        urls = hxs.select('//div[@class="product_list"]/div/div[@class="product_info"]/a[1]/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        urls = hxs.select('//ul[@class="pagination"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)

        product_name = hxs.select('//h1[@itemprop="name"]/text()').extract()[0]
        product_loader.add_value('name', product_name)

        image_url = hxs.select('//*[@id="zoom1"]/@src').extract()[0]
        product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))

        product_loader.add_value('url', response.url)

        identifier = hxs.select('//input[@name="id"]/@value').extract()[0]
        product_loader.add_value('identifier', identifier)

        sku = hxs.select('//div[@class="product_band"]/p/span/text()').re('(\d+)')
        sku = sku[0] if sku else ''
        product_loader.add_value('sku', sku)

        price = hxs.select('//span[@class="campaignprice-value"]/text()').extract()
        if not price:
            price = hxs.select('//span[@itemprop="price"]/text()').extract()
        if price:
            price = price[0].strip().replace(',', '.')
        product_loader.add_value('price', price)

        category = hxs.select('//ul[@class="breadcrumbs"]/li/a/text()').extract()
        category = category[-2] if category else ''
        product_loader.add_value('category', category)

        if product_loader.get_output_value('price')<100:
            product_loader.add_value('shipping_cost', 2.90)

        yield product_loader.load_item()


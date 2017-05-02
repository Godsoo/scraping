import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class FonqSpider(BaseSpider):
    name = 'fonq.nl'
    allowed_domains = ['fonq.nl']
    start_urls = ['http://www.fonq.nl/producten/categorie-lego/']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        products = set(hxs.select('//div[contains(@class, "product-body")]//a[contains(@class, "link-muted")]/@href').extract())

        for url in products:
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_product)

        pages = hxs.select('//*[contains(@class, "pagination")]//a/@href').extract()
        for url in pages:
            yield Request(urljoin_rfc(get_base_url(response), url))


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        identifier = re.findall("product_id = '(\d+)'", response.body)[0]
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//div[@class="page-header"]/h1/text()')
        price = ''.join(hxs.select('//div[@class="price price-large"]/div[@class="price"]/span[@itemprop="price"]/text()').extract())
        loader.add_value('price', extract_price_eu(price))
        loader.add_xpath('sku', '//tr/td[contains(strong/text(), "Bestelcode")]/../td[2]/text()')
        loader.add_value('category', 'Lego')

        img = hxs.select('//div[@id="productgallery-image-display"]//img/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('brand', 'lego')
        if loader.get_output_value('price'):
            loader.add_value('stock', '1')
        else:
            loader.add_value('stock', '0')

        if loader.get_output_value('price')<20:
            loader.add_value('shipping_cost', 2.95)

        yield loader.load_item()

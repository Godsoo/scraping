import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class SpeelGoedWinkelSpider(BaseSpider):
    name = 'speelgoedwinkel.nl'
    allowed_domains = ['speelgoedwinkel.nl']
    start_urls = ['http://www.speelgoedwinkel.nl/lego.html', 'http://www.speelgoedwinkel.nl/lego-duplo.html']
    errors = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for category in hxs.select(u'//ul[@class="category-subcategories"]//li/a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), category))

        for product in hxs.select(u'//h2[@class="product-name"]/a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product)

        for page in hxs.select(u'//a[@class="next i-next"]/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), page))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        category = hxs.select(u'//div[@class="breadcrumbs"]//a/text()').extract()
        category = u' > '.join(category)

        identifier = hxs.select(u'//th[@class="label" and text()="Artikelnummer"]/following-sibling::td/text()').re(u'(.+)&?')[0]
        page_product_id = hxs.select('//input[@name="product"]/@value').extract()[0]
        loader.add_value('identifier', identifier)
        sku = re.search('(\d+)', identifier)
        if sku:
            sku = sku.group(1)
            loader.add_value('sku', sku)
        loader.add_value('url', response.url)
        loader.add_xpath('name', u'//div[@class="product-name"]/h1/text()')
        price = filter(lambda p: p.strip(), hxs.select('//span[@id="product-price-%s"]/text()' % page_product_id).extract())
        if not price:
            price = filter(lambda p: p.strip(), hxs.select('//span[@id="product-price-%s"]/span[@class="price"]/text()' % page_product_id).extract())
        if price:
            price = extract_price_eu(price.pop())
            loader.add_value('price', price)
        else:
            self.errors.append("No price on " + response.url)

        img = hxs.select('//div[@class="main-image"]/a/img/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img.pop()))

        loader.add_value('category', category)
        loader.add_value('brand', 'lego')

        if loader.get_output_value('price') < 75:
            loader.add_value('shipping_cost', '4.95')

        yield loader.load_item()

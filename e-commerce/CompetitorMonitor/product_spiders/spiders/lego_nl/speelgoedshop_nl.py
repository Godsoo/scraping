from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class SpeelgoedShopSpider(BaseSpider):
    name = 'speelgoedshop.nl'
    allowed_domains = ['speelgoedshop.nl']
    start_urls = ['http://www.speelgoedshop.nl/category/220662/lego.html?items=51',
                  'http://www.speelgoedshop.nl/zoeken?searchfilter=shopid%3A653&query=lego']
    errors = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for product in response.xpath('//h2/a/@href').extract():
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)
        for page in hxs.select('//div[@class="paging-navigation"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, page))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        identifier = response.xpath('//@data-product-id').extract_first()
        loader.add_value('identifier', identifier)
        sku = response.xpath('//dt[@class="product-specs--item-title" and contains(text(), "Fabrikantcode")]/following-sibling::dd[2]/text()').extract_first()
        loader.add_value('sku', sku)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1/span[@itemprop="name"]/text()')
        price = ''.join(hxs.select('//div[@class="product-order"]//strong[@itemprop="price"]/text()').extract())
        price_cents = ''.join(hxs.select('//div[@class="product-order"]//strong[@itemprop="price"]/span[@class="sales-price--cents"]/text()').extract())
        price = price.strip() + price_cents.strip()
        price = extract_price_eu(price)
        loader.add_value('price', price)
        img = hxs.select('//img[@itemprop="image"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img.pop()))
        loader.add_value('category', 'Lego')
        loader.add_value('brand', 'Lego')
        yield loader.load_item()

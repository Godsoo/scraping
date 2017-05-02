from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class ToysXlSpider(BaseSpider):
    name = 'toysxl.nl'
    allowed_domains = ['toysxl.nl']
    start_urls = ['http://www.toysxl.nl/merk/lego']

    errors = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        for cat in hxs.select('//div[@id="product"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse_pages)
        for cat in hxs.select('//div[@id="overige"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse_pages)

    def parse_pages(self, response):
        hxs = HtmlXPathSelector(response)

        for product in hxs.select('//a[@class="productLink"]/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product,
                    meta={'category':hxs.select('normalize-space(//p[@class="breadcrumb"]/span/text())').extract()[0]})

        for page in hxs.select('//div[contains(@class, "paging")]//ul[contains(@class, "linkList")]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), page), callback=self.parse_pages)

    def parse_product(self, response):
        import re
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        pprice = hxs.select('//div[@class="price_bottom_bg"]/span[@class="fontBold125emR"]/text()').extract()
        if not pprice:
            pprice = hxs.select('//div[@class="price_bottom_bg"]//span[contains(@class, "prodPrcNowCatgLister")]/text()').extract()

        if pprice:
            price = extract_price_eu(pprice[0])
        else:
            self.errors.append('WARNING: No price in %s' % response.url)
            return

        loader.add_xpath('identifier', '//b[contains(text(), "SKU:")]/../text()')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//div[@class="product-name"]/text()')
        loader.add_value('price', price)
        loader.add_xpath('sku', '//b[contains(text(), "Artikelnummer:")]/../text()')
        loader.add_value('category', response.meta.get('category'))

        img = hxs.select('//div[@id="product-view-media-main-image"]//img/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('brand', 'lego')
        if loader.get_output_value('price') > 20:
                loader.add_value('shipping_cost', '0')
#        loader.add_xpath('stock', '1')

        yield loader.load_item()

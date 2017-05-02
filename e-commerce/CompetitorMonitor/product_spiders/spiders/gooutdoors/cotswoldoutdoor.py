import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url

# There's a version of this crawler that parses product options in a previous commit.
class CotswoldoutdoorSpider(BaseSpider):
    name = 'gooutdoors-cotswoldoutdoor.com'
    allowed_domains = ['cotswoldoutdoor.com']
    start_urls = ('http://www.cotswoldoutdoor.com/browse-by-brand',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        brands = hxs.select('//a[@class="tooltip"]')
        for brand in brands:
            url = brand.select('./@href').extract()[0]
            brand_name = brand.select('./strong/text()').extract()[0]
            yield Request(urljoin_rfc(base_url, url), meta={'brand': brand_name})

        categories = hxs.select('//a[contains(@href,"brand") and child::strong[@class="s"]]/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url), meta=response.meta)

        next_page = hxs.select('//li[@class="navi-right"]/a[child::div[@class="pager-button"]]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]), meta=response.meta)

        products = hxs.select('//p[@class="model"]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), meta=response.meta, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_name = hxs.select('//span[@itemprop="name"]/text()').extract()[0].strip()

        category = hxs.select('//ul[@class="bread-crumb"]/li/a/xml-fragment/text()').extract()
        category = category[-1].strip() if category else ''

        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()[0]

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)

        product_loader.add_value('name', product_name)

        sku = hxs.select('//p[@class="product-code"]/span/text()').extract()[0]
        product_loader.add_value('sku', sku)
        product_loader.add_value('identifier', sku)

        default_option = hxs.select('//select[@name="sku"]/@class').extract()
        price = hxs.select('//div[@class="prices"]/p[contains(@class,"pc%s")]'
                           '//span[@itemprop="price"]/text()' % default_option[0]).extract()
        price = price[0].strip() if price else '0.00'
        product_loader.add_value('price', price)

        product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))

        product_loader.add_value('category', category)

        product_loader.add_value('brand', response.meta.get('brand') or '')

        yield product_loader.load_item()

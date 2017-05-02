from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)


class MCCormicToolsDraperToolsSpider(BaseSpider):
    name = 'mccormicktools.co.uk-draper-tools'
    allowed_domains = ['mccormicktools.co.uk']
    start_urls = ['http://mccormicktools.co.uk/']

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url, self.parse_categories)

        draper_urls = ('http://mccormicktools.co.uk/hand-tools.html?limit=30&manufacturer=19',
                       'http://mccormicktools.co.uk/power-tools.html?limit=30&manufacturer=19',
                       'http://mccormicktools.co.uk/automotive-tools.html?limit=30&manufacturer=19',
                       'http://mccormicktools.co.uk/electrical-storage.html?limit=30&manufacturer=19')

        for draper_filter_url in draper_urls:
            yield Request(draper_filter_url, meta={'draper_filter': True})

    def parse_categories(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//div[@class="parentMenu"]/a[not(contains(@href, "javascript"))]/@href').extract()

        for url in categories:
            yield Request(urljoin_rfc(base_url, url))

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        category = hxs.select('//div[contains(@class, "category-title")]/h1/text()').extract()

        draper_filter = response.meta.get('draper_filter', False)

        if not draper_filter:
            products = zip(hxs.select('//h2[@class="product-name"]/a/text()').extract(),
                           hxs.select('//h2[@class="product-name"]/a/@href').extract())
            for url in [p[1] for p in products]:
                yield Request(urljoin_rfc(base_url, url),
                              self.parse_product,
                              meta={'category': category[0].strip() if category else ''})
        else:
            products = hxs.select('//h2[@class="product-name"]/a/@href').extract()
            for url in products:
                yield Request(urljoin_rfc(base_url, url),
                              self.parse_product,
                              meta={'category': category[0].strip() if category else ''})

        pages = hxs.select('//div[@class="pages"]//li/a/@href').extract()
        for url in pages:
            yield Request(urljoin_rfc(base_url, url),
                          meta=response.meta)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        sku = hxs.select('//table[@id="product-attribute-specs-table"]'
                         '//th[@class="label" and contains(text(), "SKU")]'
                         '/following-sibling::*/text()').extract()
        if not sku:
            sku = hxs.select('//table[@id="product-attribute-specs-table"]'
                             '//th[@class="label" and contains(text(), "Barcode")]'
                             '/following-sibling::*/text()').re(r'(\d\d\d\d\d)\d$')

        loader = ProductLoader(response=response, item=Product())
        loader.add_xpath('price', '//div[@class="price-box"]/span[@class="price-excluding-tax"]/span[@class="price"]/text()')
        loader.add_xpath('identifier', '//input[@name="product"]/@value')
        loader.add_value('sku', sku)
        loader.add_value('brand', 'Draper')
        loader.add_value('url', urljoin_rfc(base_url, response.url))
        loader.add_xpath('name', '//div[@class="product-name"]/h1/text()')
        loader.add_xpath('image_url', '//div[@class="product-img-box"]//img[@id="image"]/@src')
        loader.add_value('category', response.meta['category'])

        yield loader.load_item()

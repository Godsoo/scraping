
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import log

from product_spiders.items import Product, ProductLoader


class BlackcirclesSpider(BaseSpider):
    name = 'topegeartrading-blackcircles.com'
    allowed_domains = ['blackcircles.com']
    start_urls = ('http://www.blackcircles.com/tyres/brands',)

    def _start_requests(self):
        yield Request('http://www.blackcircles.com/tyres/brands/bfgoodrich/mud-terrain-ta-km2')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # Extracts brands and tyre model
        categories = hxs.select('//dl[@class="tyre-brands"]/dt/a/@href').extract()
        categories += hxs.select('//ul[li/a[contains(@href, "brands")]]/ul/li[@class=""]/a/@href').extract()
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category)
            yield Request(url)

        next = hxs.select('//div[@class="pagination-links"]/a[contains(text(), "Next")]/@href').extract()
        if next:
            url = urljoin_rfc(get_base_url(response), next[0])
            yield Request(url)

        table_sizes = hxs.select('//table[contains(@class, "common-listing") and contains(@class, "tyre-listing")]')

        if table_sizes:
            name = hxs.select('//div[@class="tyre-details-holder"]/h1/text()').extract()[0].strip()

            products = []
            for tbody in table_sizes.select('tbody'):
                products += tbody.select('tr')[1::2]

            image_url = hxs.select('//div[@class="tyre-specs"]/p[@class="tyre-image"]/span[@class="section-image-detailed-tyres"]/img/@src').extract()
            image_url = urljoin_rfc(get_base_url(response), image_url[0]) if image_url else ''

            for product in products:
                tyre_name = product.select('normalize-space(th/text())').extract()[0]
                loader = ProductLoader(item=Product(), selector=product)
                loader.add_value('name', tyre_name + ' ' + name)
                loader.add_value('url', response.url)
                loader.add_xpath('identifier', './/input[@id="hdnTyreId"]/@value')
                loader.add_xpath('price', './/span[@class="qty-price"]//span[@class="price"]/text()')
                loader.add_xpath('brand', '//div[@class="breadcrumbs"]//a[4]/text()')
                loader.add_xpath('category', '//div[@class="breadcrumbs"]//a[4]/text()')

                if image_url:
                    loader.add_value('image_url', image_url)

                yield loader.load_item()


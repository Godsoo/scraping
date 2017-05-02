import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc


from product_spiders.items import Product, ProductLoader


class CustomFormPl(BaseSpider):
    name = 'www.customform.pl'
    allowed_domains = ['www.customform.pl']
    start_urls = ('http://www.customform.pl/mapa-strony',)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        # categories
        categories = hxs.select('//div[@id="listpage_content"]/div[1]/ul[@class="tree"]//li/a/@href').extract()
        for url in categories:
            yield Request(url, callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)

        # pages
        next_page = hxs.select(u'//div[@id="pagination"]/ul/li[@id="pagination_next"]/a/@href').extract()
        if next_page:
            url = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(url, callback=self.parse_category)

        # products
        products = hxs.select(u'//ul[@id="product_list"]/li/div[@class="product_desc"]/h3/a/@href').extract()
        for url in products:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product)

        if not products:
            meta = response.meta.copy()
            meta['retry'] = meta.get('retry', 0)
            if meta['retry'] < 3:
                meta['retry'] += 1
                self.log('>>> RETRY %d => %s' % (meta['retry'], response.request.url))
                yield Request(response.request.url, meta=meta)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)
        category = hxs.select(u'//div[@class="breadcrumb"]/a/text()').extract()
        category = category[-1] if category else ''
        image_url = hxs.select(u'//ul[@id="product_images"]/li/a//img[@class="big_photo"]/@src').extract()
        if image_url:
            image_url = urljoin_rfc(get_base_url(response), image_url[0])

        name = hxs.select(u'//h1/text()').extract()[0]

        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_value('name', name.strip())
        product_loader.add_value('url', response.url)
        product_loader.add_value('category', category)
        product_loader.add_value('image_url', image_url)

        req_url = os.path.basename(response.request.url)
        identifier, _, _ = req_url.partition('-')

        product_loader.add_value('identifier', identifier)
        product_loader.add_xpath('price', '//div[@id="center_column"]/script[2]/text()',
                                 re="var productPrice='([0-9.]+)'")
        price = product_loader.get_output_value('price')
        product_loader.add_value('shipping_cost', 25 if price < 500 else 0)

        stock_option = hxs.select(u'//div[@class="shipping" and ./h2/text()="Dostawa"]/div[@class="feature_value"]/text()')


        product_loader.add_value('stock', 0 if stock_option else 1)

        yield product_loader.load_item()

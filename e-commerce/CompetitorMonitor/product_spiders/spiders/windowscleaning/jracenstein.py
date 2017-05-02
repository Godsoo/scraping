from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, url_query_parameter

from product_spiders.items import Product
from productloader import WindowsCleaningProductLoader


class JracensteinSpider(BaseSpider):
    name = 'jracenstein.com'
    allowed_domains = ['www.jracenstein.com']
    start_urls = ('http://www.jracenstein.com/store/index.asp',)

    handle_httpstatus_list = [500]

    def start_requests(self):
        yield Request('http://www.jracenstein.com/store/index.asp', meta={'dont_retry': [500]})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        category_urls = hxs.select('//div[@class="pageHeaderSubMenu"]/ul/li/a/@href').extract()
        category_urls += hxs.select('//div[@class="pageBodyLeft"]//a/@href').extract()
        category_urls += hxs.select('//li[@class="category"]/a/@href').extract()
        for url in category_urls:
            yield Request(urljoin_rfc(base_url, url), meta=response.meta)

        products = hxs.select('//li[starts-with(@id, "item")]//a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)

        if not category_urls and not products:
            retry = response.meta.get('retry', 0)
            if retry < 10:
                retry += 1
                self.log('Retrying No. %s => %s' % (retry, response.url))
                meta = response.meta.copy()
                meta['retry'] = retry
                yield Request(response.url, meta=meta, dont_filter=True)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        try:
            identifier = hxs.select('//font[@class="content" and contains(text(), "Item Code:")]'
                                    '/parent::td/following-sibling::td/font/text()').extract()[0]
        except:
            identifier = response.url.split('/')[-3]
            if 'jracenstein.com' in identifier:
                identifier = url_query_parameter(response.url, 'ic')
            if not identifier:
                identifier = url_query_parameter(response.url, 'kc')
                return

        try:
            name = hxs.select('//div[@class="bigbox"]/div[@class="top"]/text()').extract()[0]
            price = hxs.select('//div[@class="priceAmount"]/text()').extract()[0]
            sku = hxs.select('//font[@class="content" and contains(text(), "Model")]/../../td[2]/font/text()').extract()
            sku = sku[0] if sku else None
            category = hxs.select('//div[@class="pageHeaderCrumbs"]/a/text()').extract()
            brand = hxs.select('//font[@class="content" and contains(text(), "Brand")]/../../td[2]/font//text()[normalize-space()]').extract()
            image_url = hxs.select('//img[@class="imagePanelLarge"]/@src').extract()
            loader = WindowsCleaningProductLoader(item=Product(), selector=hxs)
            loader.add_value('url', response.url)
            loader.add_value('name', name)
            loader.add_value('price', price)
            if not loader.get_output_value('price'):
                loader.add_value('stock', 0)
            if sku:
                loader.add_value('sku', sku)
            loader.add_value('identifier', identifier)
            if brand:
                brand = brand[0].strip().split(' ')[0]
                loader.add_value('brand', brand)
            if category:
                loader.add_value('category', category[-1])
            if image_url:
                loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            yield loader.load_item()
        except IndexError:
            retry = response.meta.get('retry', 0)
            if retry < 10:
                retry += 1
                self.log('Retrying No. %s => %s' % (retry, response.url))
                meta = response.meta.copy()
                meta['retry'] = retry
                yield Request(response.url, callback=self.parse_product, meta=meta, dont_filter=True)

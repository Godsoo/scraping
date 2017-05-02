# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price
import re
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import DontCloseSpider
from scrapy.utils.url import add_or_replace_parameter


class LloydspharmacySpider(BaseSpider):
    name = u'merckgroup-lloydspharmacy.com'
    allowed_domains = ['www.lloydspharmacy.com']
    start_urls = ('http://www.lloydspharmacy.com/', )
    retry_links = []

    def __init__(self, *args, **kwargs):
        super(LloydspharmacySpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.process_retry_links, signals.spider_idle)

    def process_retry_links(self, spider):
        if spider.name == self.name:
            self.log("Spider idle. Processing retry_links")
            url = None
            if self.retry_links:
                url = self.retry_links.pop(0)
            if url:
                r = Request(url, dont_filter=True, callback=self.parse_products_list)
                self._crawler.engine.crawl(r, self)
                raise DontCloseSpider

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//*[@id="mainNavigationTopLevel"]//li/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

    def parse_products_list(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//div[@class="category filterCategory"]//li/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

        urls = hxs.select('//div[@class="row productList"]//div[@class="product"]/div[@class="productContent"]/a/@href').extract()
        self.log('Product # found: {}'.format(len(urls)))
        if len(urls) == 0:
            self.log('Retry: {}'.format(response.url))
            retry = int(response.meta.get('retry', 0))
            retry += 1
            if retry < 10:
                yield Request(response.url, meta={'retry': retry}, dont_filter=True, callback=self.parse_products_list)
            else:
                self.log("No products found on the page on %s" % response.url)
                #self.retry_links.append(response.url)
            return
        for url in urls:
            yield Request(urljoin_rfc(base_url, url),
                          dont_filter=True,
                          callback=self.parse_product,
                          cookies={},
                          meta={'dont_merge_cookies': True})

        #next pages
        if 'pageSize=' not in response.url:
            products_count = int(hxs.select('//div[@id="plpContent"]/div[@id="searchCounter"]/text()').re('"productCount".*?(\d+)')[0])
            self.log('products_count: {}'.format(products_count))
            if products_count > 12:
                next_p = hxs.select('//div[@class="facetJSON hide"]/@data-url').extract()
                if next_p:
                    next_p = next_p[0]
                    self.log('Next P: {}'.format(next_p))
                    for i in xrange((products_count - 1) / 12):
                        begin_index = (i + 1) * 12
                        url = add_or_replace_parameter(next_p, 'beginIndex', str(begin_index))
                        formdata = {'beginIndex': str(begin_index),
                                    'scrollTo': 'false',
                                    'requesttype': 'ajax'}
                        yield FormRequest(url,
                                          formdata=formdata,
                                          callback=self.parse_products_list,
                                          cookies={},
                                          meta={'dont_merge_cookies': True})
                else:
                    self.log('Retry next page: {}'.format(response.url))
                    retry = int(response.meta.get('retry', 0))
                    retry += 1
                    if retry < 10:
                        yield Request(response.url,
                                      meta={'retry': retry},
                                      dont_filter=True,
                                      callback=self.parse_products_list)
                    else:
                        self.log("No next page found on the page on %s" % response.url)
                        #self.retry_links.append(response.url)

    @staticmethod
    def parse_product(response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        price = hxs.select('//div[@class="productPrice"]/text()').extract()
        if not price:
            return
        price = extract_price(''.join(price))
        loader.add_value('price', price)
        loader.add_xpath('name', '//div[@class="productName"]/h1/text()')
        loader.add_value('url', response.url)
        identifier = response.css('.skuNumber').xpath('p/text()').re('SKU: *(\S+)')
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        if hxs.select('//div[@class="productActions"]/p[text()="This product is currently unavailable"]'):
            loader.add_value('stock', 0)
        loader.add_xpath('category', '//ul[@aria-label="breadcrumb navigation region"]/li[2]/a/text()')
        if price < 35:
            loader.add_value('shipping_cost', 2.95)
        image_url = hxs.select('//div[@class="galleryImage"]/img/@src').extract()
        image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''
        loader.add_value('image_url', image_url)
        yield loader.load_item()
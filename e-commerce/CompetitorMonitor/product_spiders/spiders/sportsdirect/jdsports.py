# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from selenium.common.exceptions import NoSuchElementException
from phantomjs import PhantomJS
import time


class JDSportsSpider(BaseSpider):
    name = u'jdsports.co.uk'
    allowed_domains = ['www.jdsports.co.uk']
    start_urls1 = [
        'http://www.jdsports.co.uk/men/mens-footwear/brand/nike/',
        'http://www.jdsports.co.uk/women/womens-footwear/brand/nike/'
    ]
    start_urls2 = [
        'http://www.jdsports.co.uk/featured/kids+nike+footwear?pageSize=9999',
        'http://www.jdsports.co.uk/search/nike-skateboarding?pageSize=9999'
    ]

    def __init__(self, *args, **kwargs):
        super(JDSportsSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        # Browser
        self.log('>>> BROWSER: Open browser')
        self._browser = PhantomJS()
        self.log('>>> BROWSER: OK')

    def spider_closed(self, spider):
        # Browser close
        self.log('>>> BROWSER: close')
        self._browser.close()
        self.log('>>> BROWSER: OK')

    def start_requests(self):
        product_urls = []
        for url in self.start_urls1:
            self.log('>>> BROWSER: GET => %s' % url)
            self._browser.get(url)
            self.log('>>> BROWSER: OK')
            find_more = True
            while find_more:
                hxs = HtmlXPathSelector(text=self._browser.driver.page_source)
                product_urls += hxs.select('//a[@data-perf-id="product"]/@href').extract()
                try:
                    self.log('>>> BROWSER: CLICK NEXT PAGE LINK')
                    self._browser.driver.find_element_by_xpath('//ul[@data-component-name="pagination"]/li[contains(@class, "next")]/a').click()
                    self.log('>>> BROWSER: OK')
                except NoSuchElementException:
                    self.log('>>> BROWSER: NEXT PAGE NOT FOUND')
                    find_more = False
                else:
                    time.sleep(5)

        for url in product_urls:
            yield Request(url, callback=self.parse_product)
        for url in self.start_urls2:
            yield Request(url, callback=self.parse_products_list, meta={'category': ''})

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        urls = hxs.select('//*[@id="Sport/Activity"]/li/a/@href').extract()
        categories = hxs.select('//*[@id="Sport/Activity"]/li/a/@id').extract()
        for url, category in zip(urls, categories):
            url = url.replace('fh_view_size%3d20', 'fh_view_size%3d9999')
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list, meta={'category': category})

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//a[@data-perf-id="product"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        # page 404
        if hxs.select("//img[@class='image-404']"):
            self.log("[WARNING] Product not found on page: %s" % response.url)
            return
        base_url = get_base_url(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//*[@id="infoPanel"]/h1/text()').extract()[0].strip()
        url = response.url
        loader.add_value('url', urljoin_rfc(base_url, url))
        loader.add_value('name', name)
        image_url = hxs.select('//*[@id="main"]/noscript/img/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        price = hxs.select('//*[@id="productSummaryPrice"]/text()').extract()[0]
        if price == 'No price available.':
            return
        price = extract_price(price.replace(u'\xa3', ''))
        loader.add_value('price', price)
        if 'category' in response.meta:
            loader.add_value('category', response.meta.get('category'))
        else:
            categories = hxs.select('//div[@class="breadcrumbs"]/a[not(contains(@class, "current"))]/text()').extract()
            if categories:
                loader.add_value('category', categories[-1])
        identifier = hxs.select('//div[@id="productPage"]/@data-plu').extract()[0]
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('brand', 'Nike')
        if price < 60:
            loader.add_value('shipping_cost', 3.99)
        else:
            loader.add_value('shipping_cost', 0)
        yield loader.load_item()

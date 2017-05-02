import os
import time
from datetime import datetime

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

from phantomjs import PhantomJS


class CulpittFeedSpider(BaseSpider):
    # This spider used a feed, now it monitors the client site
    name = 'culpitt.com-feed'
    allowed_domains = ['culpittcakeclub.com']
    start_urls = ['http://www.culpittcakeclub.com/shop']

    handle_httpstatus_list = [403, 400, 503]

    def __init__(self, *args, **kwargs):
        super(CulpittFeedSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        self._browser = PhantomJS.create_browser()

    def spider_closed(self):
        self._browser.quit()

    def start_requests(self):
        yield Request('http://www.culpittcakeclub.com/shop')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@class="categoryItem panel"]/div/ul/li/a/@href').extract()
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category)
            yield Request(url, callback=self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        self.log('>> BROWSER => GET < %s />' % response.url)
        self._browser.get(response.url)
        self.log('>> OK')

        self.log('>> BROWSER => Looking for more products ...')
        try:
            load_more_button = self._browser.find_element_by_xpath('//input[@class="button more"]')
            more_reviews = load_more_button.is_displayed()
            max_pages = 40
            while more_reviews and max_pages>0:
                self.log('>> More products found...')
                load_more_button.click()
                self.log('>> BROWSER => CLICK "Load more"')
                time.sleep(50)
                self.log('>> OK')
                load_more_button = self._browser.find_element_by_xpath('//input[contains(@class, "more")]')
                more_reviews = load_more_button.is_displayed()
                max_pages -= 1
            self.log('>> No more products...')
        except Exception, e:
            self.log('>> ERROR FOUND => %s' % e)

        hxs = HtmlXPathSelector(text=self._browser.page_source)

        products = hxs.select('//div[contains(@class, "product")]//div[@class="details"]/p/a/@href').extract()
        for product in products:
            url = urljoin_rfc(get_base_url(response), product)
            yield Request(url, callback=self.parse_product)

        formdata = {}
        inputs = hxs.select('//input')
        for input in inputs:
            name = input.select('@name').extract()
            value = input.select('@value').extract()
            if name and value:
                formdata[name[0]] = value[0]

        req = FormRequest(url=response.url, method='POST', formdata=formdata,
                          callback=self.parse_products,
                          dont_filter=True)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(response=response, item=Product())
        sku = hxs.select('//tr[td/text()="Item Number:"]/td[text()!="Item Number:"]/text()').extract()

        if sku:
            sku = sku[0]
        else:
            # Bundle offers don't have item number
            # But identifier is not unique since we use SKU as identifiers
            parts = response.url.split('/')
            sku = 'bundle' + parts[parts.index('products')+1]

        loader.add_value('identifier', sku)
        loader.add_value('sku', sku)
        loader.add_xpath('name', '//div[contains(@class, "productpage")]/h1/text()')
        loader.add_xpath('price', '//span[@class="price"]/text()')
        loader.add_value('url', response.url)
        image_url = hxs.select('//div[contains(@class, "productImages")]//img/@src').extract()
        image_url = urljoin_rfc(get_base_url(response), image_url[0]) if image_url else ''
        loader.add_value('image_url', image_url)
        brand = hxs.select('//div[h2/text()="Manufacturer Information"]/div/p/text()').extract()
        if brand:
            brand = brand[0].split(' (')[0].replace('Ltd', '').replace('Corporation', '').replace('Manufacturers', '').replace('Limited', '').strip()
            loader.add_value('brand', brand)
        category = hxs.select('//div[@class="bc shop"]/ul/li/a/span/text()').extract()[-1]
        loader.add_value('category', category)
        in_stock = hxs.select('//input[@id="BtnAddToBasket"]')
        if not in_stock:
            loader.add_value('stock', 0)
        item = loader.load_item()
        if item['price']<25:
            item['shipping_cost'] = 4.99
        
        yield item

# -*- coding: utf-8 -*-
import re
import time

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price

from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

def retry_decorator(callback):
    def wrapper(self, response):
        if response.status in self.handle_httpstatus_list:
            self.retry_urls[response.url] = callback.__name__
            return
        else:
            res = callback(self, response)
            for i in res:
                yield i
    return wrapper

class WmsSpider(BaseSpider):

    name = u'wms.co.uk'
    deduplicate_identifiers = True
    allowed_domains = ['wms.co.uk']
    start_urls = [
        u'http://www.wms.co.uk/',
    ]

    rotate_agent = True
    download_delay = 1
    headers = {'Host':'www.wms.co.uk'}
    handle_httpstatus_list = [500, 501, 502, 503, 504, 400, 408, 403, 456, 429]
    cookies = {'_gat':'1'}

    def __init__(self, *args, **kwargs):
        super(WmsSpider, self).__init__(*args, **kwargs)
        self.retry_urls = dict()
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def start_requests(self):
        yield Request('http://www.wms.co.uk/Blood_Pressure_and_ABPM/Sphygmomanometer_Accessories/Click_300_Cuff_Control_Valve?PC=W610',
                      callback=self.parse_product)
        yield Request('http://www.wms.co.uk/Blood_Pressure_and_ABPM/Sphygmomanometer_Accessories',
                      callback=self.parse_categories)
        for url in self.start_urls:
            yield Request(url)

    def spider_idle(self, spider):
        if spider.name == self.name and self.retry_urls:
            time.sleep(300)
            urls = self.retry_urls.copy()
            self.retry_urls = dict()
            self.log('Spider idle. %d urls to retry' %len(urls))
            for i, url in enumerate(urls):
                if urls[url] == 'parse_categories':
                    callback = self.parse_categories
                else:
                    callback = self.parse_product
                request = Request(url, dont_filter=True, callback=callback, meta={'cookiejar':i, 'recache': True}, cookies=self.cookies)
                self.crawler.engine.crawl(request, self)


    def _proxy_service_check_response(self, response):
        return response.status in [403, 503, 504, 400]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        urls = hxs.select('//div[@class="Top_Nav_Menu"]/div[contains(@class,"column")]/ul/li/a/@href').extract()
        urls.extend([
            'https://www.wms.co.uk/search/?KS=Caption:Clearance&CO=1&PT=C&V=',
            'https://www.wms.co.uk/search/?KS=Caption:Clearance&CO=1&PT=E&V=',
            'https://www.wms.co.uk/search/?KS=Caption:Clearance&CO=1&PT=P&V='
        ])
        urls = list(set(urls))

        for i, url in enumerate(urls):
            yield Request(
                urljoin(base_url, url),
                callback=self.parse_categories,
                headers=self.headers,
                cookies={}
            )

    @retry_decorator
    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        find_any = False

        # subcats
        urls = hxs.select('//*[@id="Full_Div"]//div[@class="Subsection_Div"]//a/@href').extract()
        urls += hxs.select('//div/div/a[img[@alt="View entire range"]]/@href').extract()
        urls = list(set(urls))

        for url in urls:
            find_any = True
            yield Request(
                urljoin(base_url, url),
                callback=self.parse_categories,
                meta={'dont_retry':True},
                cookies={}
            )

        # products
        urls = hxs.select('//*[@id="Info_Div"]//div[@class="Search_Item_Div_Buttons"]//a[last()]/@href').extract()
        urls = list(set(urls))
        for url in urls:
            find_any = True
            yield Request(
                urljoin(base_url, url),
                callback=self.parse_product,
                meta={'dont_retry':True},
                cookies={}
            )

        # page
        next_page = hxs.select("//a[text()='Next']/@href").extract()
        if next_page:
            yield Request(
                urljoin(base_url, next_page[0]),
                callback=self.parse_categories,
                meta={'dont_retry':True},
                cookies={}
            )

        if not find_any and response.request.meta.get('redirect_urls'):
            yield Request(response.url,
                          dont_filter=True,
                          callback=self.parse_product,
                          cookies={})

    @retry_decorator
    def parse_product(self, response):
        if response.url == 'http://www.wms.co.uk/Pulse_Oximetry/Handheld_Pulse_Oximeters/Huntleigh_Smartsigns_MiniPulse_MP1R_Rechargeable_Pulse_Oximeter?PC=W6609':
            text = response.body.replace('<3kg', '&lt;3kg')
            hxs = HtmlXPathSelector(text=text)
        else:
            hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        image_url = hxs.select('//*[@id="Images_Main"]/@src').extract()
        image_url = urljoin(base_url, image_url[0]) if image_url else ''
        category = hxs.select('//*[@id="Breadcrumb_Div"]/div/a[2]/text()').extract()
        category = category[0] if category else ''

        products = hxs.select('//*[@id="Product_Div_Outer"]//div[@class="Product_Grid_Outer"]')

        for product in products:

            try:
                price = product.select('.//div[@class="Product_Grid_Price"]/text()').extract()[0].strip()
                price = extract_price(price)
            except Exception as e:
                self.log("Couldn't find price for product {}, error code: {}".format(response.url, e))
                continue

            availability = product.select('.//div[@class="Product_Grid_Availability"]/text()').extract()
            if availability and availability[0].strip() == 'This product is no longer available':
                self.log('Product {} is no longer available'.format(response.url))
                continue

            options = product.select('.//select[@class="Product_Grid_Variant_Select"]/option')
            if options:
                x = hxs.select('//script[contains(text(), "SwapVariant(event, intPC)")]').extract()[0]
                options_availability_lines = x.split('\r\n')
                name = product.select('./div[@class="Product_Grid_Description"]/text()').extract()[0].strip()
                for option in options:
                    loader = ProductLoader(item=Product(), selector=product)
                    identifier = option.select('./@value').extract()[0]
                    option_name = option.select('./text()').extract()[0].strip()
                    option_availability = ''
                    for line in options_availability_lines:
                        if identifier in line:
                            if any(word in line for word in ['strInner = ""',
                                                             'Please contact us for availability',
                                                             'None in stock']):
                                option_availability = 'out of stock'
                            if 'This product is no longer available' in line:
                                option_availability = 'delisted'
                            # self.log("==============={}================".format(line))
                    if option_availability == 'delisted':
                        self.log('Product {} is delisted'.format(response.url))
                        continue
                    elif option_availability == 'out of stock':
                        loader.add_value('stock', 0)
                    loader.add_value('url', response.url)
                    loader.add_value('name', name + ' ' + option_name)
                    loader.add_value('image_url', image_url)
                    loader.add_value('category', category)
                    price_line = ''
                    for line in response.body_as_unicode().split('\n'):
                        if identifier.upper() in line.upper() and 'PRICE' in line.upper():
                            price_line = line
                    option_price = re.findall("strPrice = (.*)<br", price_line)
                    option_price = extract_price(option_price[0]) if option_price else 0
                    option_price = option_price if option_price else price
                    loader.add_value('price', option_price)
                    loader.add_value('sku', identifier)
                    loader.add_value('identifier', identifier)
                    if int(price) <= 100:
                        loader.add_value('shipping_cost', 5.33)
                    yield loader.load_item()

            else:
                loader = ProductLoader(item=Product(), selector=product)
                availability = product.select('.//div[@class="Product_Grid_Availability"]/span/text()').extract()
                if availability:
                    availability = availability[0].strip()
                    if 'None in stock' in availability or 'Please contact us for availability' in availability:
                        loader.add_value('stock', 0)
                loader.add_value('url', response.url)
                name = product.select('./div[@class="Product_Grid_Description"]/text()').extract()
                if not name:
                    name = hxs.select("//h1/text()").extract()
                name = name.pop().strip()
                sku = product.select('./div[@class="Product_Grid_Code_Availability_Outer"]//strong/text()').extract()
                if not sku:
                    sku = product.select('.//div[@class="Product_Grid_Code_Availability_Outer"]//text()').re(".* (.*)")
                sku = sku.pop().strip()
                loader.add_value('name', name)
                loader.add_value('image_url', image_url)
                loader.add_value('category', category)
                loader.add_value('price', price)
                loader.add_value('sku', sku.strip())
                identifier = product.select('.//input[contains(@name,"PC")]/@value').extract()[0]
                if sku.strip() != identifier.strip():
                    loader.add_value('identifier', identifier.strip() + '-' + sku.strip())
                else:
                    loader.add_value('identifier', identifier.strip())
                if int(price) <= 100:
                    loader.add_value('shipping_cost', 5.33)
                yield loader.load_item()

        other_products = hxs.select('//div[@id="You_May_Need"]/div[@class="Product_Page_Accessories_Row"]')
        for product in other_products:
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_value('url', response.url)
            name = product.select('div[contains(@class, "_Description")]/text()').extract()
            if not name:
                self.log('Name not found for product {}'.format(response.url))
                continue
            loader.add_value('name', name[0])
            loader.add_value('category', category)
            price = product.select('div[contains(@class, "_Price")]/strong/font/text()').extract()[0].strip()
            price = extract_price(price)
            loader.add_value('price', price)
            sku = product.select('div[contains(@class, "_Code")]/div/strong/text()').extract()[0].strip()
            loader.add_value('sku', sku)
            loader.add_value('identifier', sku)
            if int(price) <= 100:
                loader.add_value('shipping_cost', 5.33)
            yield loader.load_item()

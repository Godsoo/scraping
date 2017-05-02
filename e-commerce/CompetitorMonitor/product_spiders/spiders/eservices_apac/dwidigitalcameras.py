import os
import time
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))


def retry_decorator(callback):
    def new_callback(obj, response):
        if response.status in obj.retry_codes:
            yield obj._retry_request(response.request)
        else:
            res = callback(obj, response)
            if res:
                for r in res:
                    yield r
    return new_callback


class DwidigitalcamerasSpider(BaseSpider):
    name = 'dwidigitalcameras'
    allowed_domains = ['dwidigitalcameras.com.au']
    start_urls = ['http://www.dwidigitalcameras.com.au/astore/Directory.aspx']
    handle_httpstatus_list = [403, 503]

    rotate_agent = True
    retry_codes = [403, 503, 411]
    max_retry_times = 20

    def __init__(self, *args, **kwargs):
        self.id_seen = []

    def _retry_request(self, request):
        time.sleep(1)

        retries = request.meta.get('retry_times', 0) + 1

        if retries <= self.max_retry_times:
            retryreq = request.copy()
            retryreq.meta['retry_times'] = retries
            retryreq.meta['recache'] = True
            retryreq.dont_filter = True
            return retryreq
        else:
            self.blocked_urls.append(request.url)
            self.log('Gave up retrying %(request)s (failed %(retries)d times)' %
                     {'request': request, 'retries': retries})

    @retry_decorator
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        cookie_jar = 0
        for url in hxs.select('//td[@id="mainPanel"]//a[contains(@class, "level-")]/@href').extract():
            cookie_jar += 1
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'cookiejar': cookie_jar})

    @retry_decorator
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)

        pid = ''
        if 'viewedProductIds:' in response.body:
            ss = response.body.split('viewedProductIds:',1)[1].split("'",2)
            if len(ss)>2:
                pid = ss[1]
        if pid:
            loader.add_value('identifier', pid)
            loader.add_value('sku', pid)
        else:
            self.log('### No product ID at ' + response.url)
            return

        loader.add_xpath('name', '//span[@itemprop="name"]/text()')
        loader.add_xpath('price', '//span[@itemprop="price"]/span[1]/text()')

        image_url = hxs.select('//img[@id="ProductMainImage"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

        brand = hxs.select('//span[@itemprop="offers"]//u/text()').extract()
        if brand:
            loader.add_value('brand', brand[0])

        categories = hxs.select('//div[@class="CategoryBreadCrumbs"]/a/text()').extract()
        loader.add_value('category', categories)

        product = loader.load_item()
        options = hxs.select('//select[@name="ctl00$wpm$ShowProduct$ctl09$option0"]/option[not(contains(@value,"Select"))]')

        if not options:
            if not product['identifier'] in self.id_seen:
                self.id_seen.append(product['identifier'])
                yield product
            else:
                self.log('### Duplicate product ID at ' + response.url)
            return

        for sel in options:
            item = Product(product)
            value = sel.select('@value').extract()[0]
            item['identifier'] += '-' + value
            try:
		item['name'] += ' - ' + sel.select('text()').extract()[0]
	    except IndexError:
		continue

            meta = response.meta.copy()
            meta['item'] = item
            yield FormRequest.from_response(
                response,
                formnumber=0,
                formdata={'ctl00$wpm$ShowProduct$ctl11$option0': value,
                          '__EVENTTARGET':'ctl00$wpm$ShowProduct$ctl11$option0',
                          '__EVENTARGUMENT':''},
                meta=meta,
                callback=self.parse_option)

    @retry_decorator
    def parse_option(self, response):
        hxs = HtmlXPathSelector(response)
        item = response.meta['item']
        price = hxs.select('//span[@itemprop="price"]/span[1]/text()').extract()
        if price:
            item['price'] = extract_price(price[0].strip())

        if not item['identifier'] in self.id_seen:
            self.id_seen.append(item['identifier'])
            yield item
        else:
            self.log('Duplicated product id: ' + item['identifier'])

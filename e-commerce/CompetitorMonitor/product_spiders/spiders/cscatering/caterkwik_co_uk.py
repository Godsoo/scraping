import re
import json
import urlparse
from decimal import Decimal
from random import random

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price, fix_spaces
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.prodcache import ProductCacheSpider
from product_spiders.base_spiders.primary_spider import PrimarySpider

from scrapy import log

from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
import time

def retry_decorator(callback):
    def new_callback(obj, response):
        if response.status in obj.handle_httpstatus_list:
            obj.log('Response status for %s is %s' %(response.url, response.status))
            obj.log('Saving for later tries')
            r = response.request.replace(dont_filter=True)
            r.meta['recache'] = True
            obj.blocked_urls.append(r)
            return
        else:
            res = callback(obj, response)
            if res:
                for r in res:
                    yield r
    return new_callback


class CaterKwikSpider(PrimarySpider):
    name = 'caterkwik.co.uk'
    allowed_domains = ['caterkwik.co.uk']
    start_urls = ('https://www.caterkwik.co.uk',)


    #user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:42.0) Gecko/20100101 Firefox/42.0'
    rotate_agent = True
    download_delay = 1
    handle_httpstatus_list = [500, 501, 502, 503, 504, 400, 408, 403, 456, 429]

    csv_file = 'carterkwik_products.csv'

    cookies = {'mobile':'d',
               '__cfduid':'d43b0ef6b4190dbe586187dbd060b5e2a1448800166',
               'CATERKWIK_SESSION':'c6ad43a9632a6d86aa4dfe0e23b579ee'}
    headers = {'Host':'www.caterkwik.co.uk',
               'Connection':'keep-alive'}
    ignore_brands = []

    def proxy_service_check_response(self, response):
        return response.status in self.handle_httpstatus_list

    def __init__(self, *args, **kwargs):
        super(CaterKwikSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)
        self.blocked_urls = []

    def spider_idle(self, spider):
        time.sleep(200)
        if self.blocked_urls:
            self.log("%d urls haven't been parsed. Trying more" %len(self.blocked_urls))
            blocked_urls = list(self.blocked_urls)
            self.blocked_urls = []
            for request in blocked_urls:
                self._crawler.engine.crawl(request, self)
        else:
            super(CaterKwikSpider, self).spider_idle(spider)


    def start_requests(self):
        for url in self.start_urls:
            yield Request(url, meta={'dont_merge_cookies':True}, dont_filter=True, headers=self.headers)
        #yield Request('http://www.caterkwik.co.uk/cgi-bin/trolleyed_public.cgi?action=showprod_DCSB40036242', callback=self.parse_product, meta={'product': Product()})
#        http://www.caterkwik.co.uk/cgi-bin/trolleyed_public.cgi?action=showprod_ROBOTCOUPEC200
#        yield Request('http://www.caterkwik.co.uk/cgi-bin/trolleyed_public.cgi?action=showprod_CK0659BBQ', callback=self.parse_product, meta={'product': Product()})

    @retry_decorator
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        category_urls = hxs.select('//nav[@id="nav"]//li/a/@href').extract()
        category_urls += hxs.select('//div[@id="secondary-nav"]/nav//li/a/@href').extract()
        for url in category_urls:
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_cat, headers = self.headers)

    @retry_decorator
    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//li[@class="grid-link"]//a/@href').extract() + \
            hxs.select('//div[@class="item-sub"]/a/@href').extract():
                yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_cat, headers=self.headers)

        for productxs in hxs.select('//div[contains(@class,"productbox")]'):
            product = Product()
            product['price'] = extract_price(''.join(productxs.select('.//p[@class="item-price"]/text()').extract()))
            if product['price']:
                product['stock'] = 1
            else:
                product['stock'] = 0

            try:
                meta = dict(response.meta)
                meta['product'] = product
                #meta['dont_merge_cookies'] = True
                #meta['dont_retry'] = True
                yield Request(urljoin_rfc(get_base_url(response), productxs.select('.//a[@class="productname"]/@href').extract()[0]),
                        callback=self.parse_product,
                        meta=meta)
            except IndexError:
                continue

        for url in hxs.select('//div[@class="pages"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_cat, meta=response.meta)

    @retry_decorator
    def parse_product(self, response):
        body = unicode(re.sub(u'(<select|SELECT .*>)</p>', '\\1', response.body), "utf8", errors="ignore")
        body = re.sub(u'(<(option|OPTION) (value|VALUE)=\".+?)(\")(.*?\">)', r'\1\5', body)
        hxs = HtmlXPathSelector(text=body)
        loader = ProductLoader(item=response.meta.get('product', Product()), selector=hxs)
        loader.add_xpath('identifier', '//input[@name="prodid"]/@value')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//*[@itemprop="name"]//text()')
        loader.add_xpath('sku', '//p/strong[contains(text(), "MPN:")]/../text()')

        loader.add_xpath('category', '//div[@itemprop="breadcrumb"]/a[2]/text()')
        img = hxs.select('//div[contains(@class, "product-image-main")]//img/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_xpath('brand', 'normalize-space(//p/strong[contains(text(), "BRAND:")]/../text())')
        brand = loader.get_output_value('brand').strip().upper()
        if brand in self.ignore_brands:
            log.msg('Ignoring %s product: %s' % (brand, response.url))
            return

        got_options = False
        prod = loader.load_item()

        for select in hxs.select('//select[@name and @name!="Accessories" and not(contains(option/@value, "No Thanks"))]'):
            for o in select.select(u'./option'):
                option = ''.join(o.select('.//text()').extract())
                try:
                    name, price = option.split('(')
                except:
                    name, price = option, ''

                if not price or price.startswith('+'):
                    continue

                opt_id = o.select('./@value').extract()[0].split('(')[0].replace(' ', '')
                name = select.select('./@name').extract()[0] + '=' + name
                price = extract_price(price)
                if price == 0:
                    continue


                # Only "options" that are model
                got_options = True
                p = Product(prod)
                p['name'] = p['name'] + ' ' + name
                p['price'] = Decimal(price).quantize(Decimal('1.00'))
                p['identifier'] = p['identifier'] + ':' + opt_id if opt_id else p['identifier']
                yield self.add_shipping_cost(p)

        if not got_options:
            yield self.add_shipping_cost(prod)

    def add_shipping_cost(self, item):
        # Shipping costs can only be found when in checkout. Also depends on the weight of the product. Please just ignore this field
        return item

"""
Account: Tiger Chef
Name: acitydiscount.com
"""


import time
from scrapy import Spider, Request
from scrapy import signals
from scrapy.utils.url import url_query_parameter
from scrapy.xlib.pydispatch import dispatcher
from product_spiders.items import Product
from tigerchefloader import TigerChefLoader as ProductLoader


def blocked_retry_decorator(callback):
    def new_callback(obj, response):
        if 'system/denied' in response.url or 'Request unsuccessful' in response.body:
            time.sleep(300)
            yield obj._retry_request(response.request)
        else:
            res = callback(obj, response)
            if res:
                for r in res:
                    yield r
    return new_callback


class AcityDiscountSpider(Spider):
    name = 'acitydiscount.com'
    allowed_domains = ['acitydiscount.com']
    start_urls = ['https://www.acitydiscount.com/restaurant_equipment/index.cfm?_faction=1']

    rotate_agent = True
    download_delay = 10
    max_retry_times = 10

    def __init__(self, *args, **kwargs):
        self._add_to_cart_products = []
        self._current_cookie = 0
        self._search_done = False

        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def spider_idle(self, spider):
        if self._search_done and self._add_to_cart_products:
            item_id, url, product = self._add_to_cart_products.pop()
            self._current_cookie += 1
            req = Request(url,
                          meta={'item_id': item_id,
                                'product': product,
                                'cookiejar': self._current_cookie},
                          callback=self.parse_cart,
                          dont_filter=True)
            self.crawler.engine.crawl(req, self)

    # Only if Proxy Service enabled
    def proxy_service_check_response(self, response):
        return ('system/denied' in response.url or 'Request unsuccessful' in response.body)

    @blocked_retry_decorator
    def parse(self, response):
        next_page = response.xpath('//*[@class="pagelinks"]/following-sibling::td//a[contains(text(), "Next")]/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]), meta={'dont_merge_cookies': True}, dont_filter=True)

        if not next_page:
            self._search_done = True

        products_xs = response.xpath('//td[contains(@class, "search-prod")]')
        for product_xs in products_xs:
            sku = None
            product_id = product_xs.xpath('.//*[@class="search-item-title"]/a/@href').extract()[0].split('/')[-1].split('.')[2]
            try:
                brand, sku = product_xs.xpath('.//*[@class="search-item-title"]/following-sibling::div/a/text()').extract()
            except ValueError:
                try:
                    brand = product_xs.xpath('.//*[@class="search-item-title"]/following-sibling::div/a/text()').extract()[0]
                except:
                    brand = None
            image_url = map(response.urljoin, product_xs.xpath('.//img/@src').extract())
            price = product_xs.xpath('.//*[@class="search-item-price"]').re(r'[\d\.,]+')
            add_to_cart = bool(product_xs.xpath('.//*[@class="search-item-price"]/span[@class="see-price-sprite"]'))
            loader = ProductLoader(item=Product(), selector=product_xs)
            identifier = product_id
            if sku:
                identifier = identifier + ' ' + sku.lower()

            loader.add_value('identifier', identifier)
            if sku:
                loader.add_value('sku', sku)
            loader.add_xpath('url', './/*[@class="search-item-title"]/a/@href')
            if image_url:
                loader.add_value('image_url', image_url[0].replace('/pics/sm/', '/pics/md/').replace('sm_', 'md_'))
            if brand:
                loader.add_value('brand', brand)
            loader.add_xpath('name', './/*[@class="search-item-title"]/a/strong/text()')
            if price:
                    loader.add_value('price', price[0])
                    yield loader.load_item()
            elif add_to_cart:
                product = loader.load_item()
                url = response.urljoin(product_xs.xpath('.//a[@class="atc-primary"]/@href').extract()[0])
                item_id = url_query_parameter(url, 'ItemID')
                self._add_to_cart_products.append((item_id, url, product))

    @blocked_retry_decorator
    def parse_cart(self, response):
        item_id = response.meta['item_id']
        price = response.xpath('//table[@width="980"]//tr[not(@class) and '
                       './/input[@name="Qty%s"]]/td[@align="right" and @valign="top"]/text()' % item_id)\
                .re(r'[\d\.,]+')
        if price:
            loader = ProductLoader(response.meta['product'], response=response)
            loader.add_value('price', price)
            yield loader.load_item()

    def _retry_request(self, request):
        retries = request.meta.get('retry_times', 0) + 1

        if retries <= self.max_retry_times:
            if 'redirect_urls' in request.meta:
                new_url = filter(lambda u: 'system/denied' not in u,request.meta['redirect_urls'])
                retryreq = request.replace(url=new_url[0])
            else:
                retryreq = request.copy()
            retryreq.meta['retry_times'] = retries
            retryreq.dont_filter = True
            return retryreq
        else:
            self.log('Gave up retrying %(request)r (failed %(retries)d times)' %
                     {'request': request, 'retries': retries})

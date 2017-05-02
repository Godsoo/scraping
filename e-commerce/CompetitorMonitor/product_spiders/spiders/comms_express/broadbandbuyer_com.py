"""
Name: broadbandbuyer.com
Account: Comms Express

IMPORTANT

- Blocking issues
- Need proxies
- Do not use concurrent requests
- High download delay value
- Custom retry method author: Emiliano M. Rudenick <emr.frei@gmail.com>
"""


from itertools import chain
from decimal import Decimal
from datetime import datetime
from urllib import quote as url_quote
from scrapy import Request
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.spiders.comms_express.utils import CommsBaseSpider
from extruct.w3cmicrodata import MicrodataExtractor


def retry_decorator(callback):
    def new_callback(obj, response):
        if (response.status in obj.retry_codes) or (not response.body):
            yield obj._retry_request(response.request)
        else:
            res = callback(obj, response)
            if res:
                for r in res:
                    yield r
    return new_callback


class BroadbandBuyerSpider(CommsBaseSpider):
    name = 'broadbandbuyer.com'
    allowed_domains = ['broadbandbuyer.com']
    start_urls = ['http://www.broadbandbuyer.com/']

    rotate_agent = True
    handle_httpstatus_list = [500, 501, 502, 503, 504, 400, 408, 404, 403]
    download_timeout = 300
    download_delay = 2

    MAX_ALL_RETRY = 1
    full_run_day = 3

    def __init__(self, *args, **kwargs):
        super(BroadbandBuyerSpider, self).__init__(*args, **kwargs)

        self.search_done = False
        self.blocked_urls = []
        self.global_retry_no = 0
        self.max_retry_times = 20
        self._full_run = datetime.today().weekday() == self.full_run_day

    def _retry_request(self, request):
        retries = request.meta.get('retry_times', 0)
        max_retry = request.meta.get('max_retry', self.max_retry_times)

        if retries < max_retry:
            retries += 1
            retryreq = request.copy()
            retryreq.meta['retry_times'] = retries
            retryreq.meta['recache'] = True
            retryreq.dont_filter = True
            return retryreq
        else:
            self.blocked_urls.append(request.url)
            self.log('Gave up retrying %(request)s (failed %(retries)d times)' %
                     {'request': request, 'retries': retries})

    def retry_blocked_urls(self, response):
        blocked_urls = list(self.blocked_urls)
        self.blocked_urls = []
        self.global_retry_no += 1
        for i, url in enumerate(blocked_urls):
            callback_method = self.parse_products
            yield Request(url,
                          dont_filter=True,
                          callback=callback_method,
                          meta={'dont_retry': True,
                                'cookiejar': i})

    def start_requests(self):
        self.retry_codes = self._crawler.settings['RETRY_HTTP_CODES']
        self.search_codes = []
        for search in self.whitelist:
            self.search_codes.append(url_quote(search.split('/')[0], ' ').lower())

        for url in self.start_urls:
            yield Request(url)

    @retry_decorator
    def parse(self, response):
        categories = response\
            .xpath('//div[@class="header-nav"]/div[@class="header-nav-column"]'
                   '/div[@class="group-title"][1]/a')
        sub_categories = response\
            .xpath('//div[@class="header-nav"]/div[@class="header-nav-column"]'
                   '/div[@class="group-title"][1]/following-sibling::ul/li/a')
        i = 0
        for cat in chain(categories, sub_categories):
            i += 1
            url = cat.xpath('@href').extract()[0]
            name = cat.xpath('text()').extract()[0].strip()
            yield Request(response.urljoin(url),
                          callback=self.parse_products,
                          meta={'cookiejar': i,
                                'category': name})

    @retry_decorator
    def parse_products(self, response):
        mde = MicrodataExtractor()
        data = mde.extract(response.body)

        category = response.meta['category']

        selectors = response.xpath('//div[contains(@id, "Products_")]')
        products = filter(lambda d: d['type'] == 'http://schema.org/Product', data['items'])
        for product_data, product_xs in zip(products, selectors):
            properties = product_data['properties']
            try:
                offer = properties['offers']['properties']
            except:
                self.log('Offers are not found for %s => %s' % (properties['name'], response.url))
                continue
            brand = product_xs.xpath('.//div[@class="Image"]//img[contains(@alt, "View more ")]/@alt').re(r'View more (.*) products')
            product_url = product_xs.xpath('.//div[@class="Info"]//h2/a[contains(@href, "/products/")]/@href').extract()
            if not product_url:
                self.log('Not product url in => %s' % response.url)
                continue
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('identifier', properties['mpn'])
            loader.add_value('url', response.urljoin(product_url[0]))
            loader.add_value('name', properties['name'])
            loader.add_value('price', round(Decimal(offer['price'].replace(',', '')) / Decimal('1.2'), 2))
            loader.add_value('sku', properties['mpn'])
            loader.add_value('category', category)
            loader.add_value('image_url', urljoin_rfc('http://www.broadbandbuyer.com/images/products/', properties['image']))
            if brand:
                loader.add_value('brand', brand[0])
            loader.add_value('shipping_cost', '13')

            in_stock = (offer['availability'] == 'http://schema.org/InStock')
            if not in_stock:
                loader.add_value('stock', 0)
            else:
                stock_no = product_xs.xpath('.//div[@class="Info"]//span[@class="Stock3"]/text()').re(r'(\d+)')
                if stock_no:
                    loader.add_value('stock', stock_no[0])

            item = loader.load_item()

            self.yield_item(item)

        page_urls = set(response.xpath('//div[@class="pages"]/a[not(contains(@class, "active"))'
                                       ' and contains(@href, "page=")]/@href').extract())
        for url in page_urls:
            yield Request(response.urljoin(url),
                          callback=self.parse_products,
                          meta={'cookiejar': response.meta['cookiejar'],
                                'category': response.meta['category']})


    def proxy_service_check_response(self, response):
        return (not response.body)

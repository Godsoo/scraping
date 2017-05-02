import os
import time
import random

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
# from scrapy.http import Request

# from scrapy import signals
# from scrapy.xlib.pydispatch import dispatcher

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)

from phantomjs import PhantomJS

from product_spiders.config import (
    PROXY_SERVICE_HOST,
    PROXY_SERVICE_USER,
    PROXY_SERVICE_PSWD,
)

from product_spiders.contrib.proxyservice import ProxyServiceAPI


HERE = os.path.abspath(os.path.dirname(__file__))


class TotalFioulreducSpider(BaseSpider):
    name = 'total-fioulreduc.com'
    allowed_domains = ['fioulreduc.com']
    start_urls = ['http://www.fioulreduc.com/']

    zipcodes_filename = os.path.join(HERE, 'fioulreduc_zipcodes.txt')
    search_url = 'http://www.fioulreduc.com/commande/devis?z=%(zip_code)s&q=1000&p=%(fuel_type)s&e=%(email)s&u='
    fuel_types = [('1', 'Ordinaire'), ('2', 'Superieure')]

    # max_retries = 10
    user_agents_filename = os.path.join(HERE, 'useragents.txt')

    proxy_target_id = 145

    def __init__(self, *args, **kwargs):
        super(TotalFioulreducSpider, self).__init__(*args, **kwargs)

        # dispatcher.connect(self.spider_opened, signals.spider_opened)
        # dispatcher.connect(self.spider_closed, signals.spider_closed)
        # dispatcher.connect(self.spider_idle, signals.spider_idle)

        self.init_zipcodes()
        self.init_useragents()

        # self.retrysearches = []
        # self.retry_count = 0

    def init_zipcodes(self):
        self.zipcodes = []
        with open(self.zipcodes_filename) as f:
            for l in f:
                self.zipcodes.append(l.strip())

    def init_useragents(self):
        self._all_user_agents = []
        with open(self.user_agents_filename) as f:
            for l in f:
                self._all_user_agents.append(l.strip())

    def _get_new_browser(self):
        proxy = None
        proxy_service_api = ProxyServiceAPI(host=PROXY_SERVICE_HOST, user=PROXY_SERVICE_USER, password=PROXY_SERVICE_PSWD)
        proxy_data = {'id': '', 'url': ''}
        proxy_list = proxy_service_api.get_proxy_list(self.proxy_target_id, types='https', log=self.log, length=1)
        if proxy_list:
            proxy_data = proxy_list[0]
            proxy_type, proxy_host = proxy_data['url'].split('://')
            proxy = {
                'host': proxy_host,
                'type': proxy_type,
            }
        user_agent = random.choice(self._all_user_agents)
        return PhantomJS(load_images=True, proxy=proxy, user_agent=user_agent)

    '''
    def spider_idle(self, spider):
        if self.retrysearches and self.retry_count < self.max_retries:
            self.retry_count += 1
            self._crawler.engine.crawl(Request(self.start_urls[0], dont_filter=True, callback=self.parse_retry_searches), self)

    def parse_retry_searches(self, response):
        while self.retrysearches:
            params = self.retrysearches.pop()
            params['email'] = mkemail()
            url = self.search_url % params
            self.log('RETRYING search => %s' % url)
            try:
                self._browser.get(url)
                hxs = HtmlXPathSelector(text=self._browser.driver.page_source)
                price = hxs.select('//span[@id="summary-total-price"]/text()').extract()[0]
                price = price.replace('.', '')
                price = price.replace(',', '.')
                loader = ProductLoader(item=Product(), selector=hxs)
                loader.add_value('identifier', params['zip_code'] + ':' + params['fuel_desc'])
                loader.add_value('sku', params['zip_code'] + ':' + params['fuel_desc'])
                loader.add_value('name', params['zip_code'] + ' - ' + params['fuel_desc'])
                loader.add_value('price', price)
                loader.add_value('brand', params['fuel_desc'])
                loader.add_value('category', params['fuel_desc'])
                loader.add_value('url', url)
                yield loader.load_item()
            except Exception, e:
                self.retrysearches.append(params)
                self.log('ERROR in search %s => %s' % (url, e))
            time.sleep(2)
    '''

    def parse(self, response):
        for zipcode in self.zipcodes:
            for fuel_type, fuel_desc in self.fuel_types:
                params = {
                    'zip_code': zipcode,
                    'fuel_type': fuel_type,
                }
                max_try = 5
                try_no = 0
                not_found = True
                while not_found and try_no < max_try:
                    try:
                        try_no += 1
                        params['email'] = mkemail()
                        url = self.search_url % params
                        browser = self._get_new_browser()
                        browser.get(url)
                        hxs = HtmlXPathSelector(text=browser.driver.page_source)
                        browser.close()
                        price = hxs.select('//span[@id="summary-total-price"]/text()').extract()[0]
                        price = price.replace('.', '')
                        price = price.replace(',', '.')
                        loader = ProductLoader(item=Product(), selector=hxs)
                        loader.add_value('identifier', zipcode + ':' + fuel_desc)
                        loader.add_value('sku', zipcode + ':' + fuel_desc)
                        loader.add_value('name', zipcode + ' - ' + fuel_desc)
                        loader.add_value('price', price)
                        loader.add_value('brand', fuel_desc)
                        loader.add_value('category', fuel_desc)
                        loader.add_value('url', url)
                        yield loader.load_item()
                    except Exception, e:
                        # params['fuel_desc'] = fuel_desc
                        # self.retrysearches.append(params)
                        self.log('ERROR in search %s => %s' % (url, e))
                    else:
                        not_found = False
                    time.sleep(2)


import string
from itertools import chain
from random import seed, choice, sample


def mkemail(length=8, digits=2, upper=2, lower=2, host='gmail.com'):

    seed(time.time())

    lowercase = string.lowercase.translate(None, "o")
    uppercase = string.uppercase.translate(None, "O")
    letters = "{0:s}{1:s}".format(lowercase, uppercase)

    password = list(
        chain(
            (choice(uppercase) for _ in range(upper)),
            (choice(lowercase) for _ in range(lower)),
            (choice(string.digits) for _ in range(digits)),
            (choice(letters) for _ in range((length - digits - upper - lower)))
        )
    )

    return "".join(sample(password, len(password))) + '@' + host

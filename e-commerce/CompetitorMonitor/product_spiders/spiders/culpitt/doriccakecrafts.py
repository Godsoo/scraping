"""

Account: Culpitt
Name: culpitt-doriccakecrafts.co.uk
Original developer: Nano (emiliano.rudenick@competitormonitor.com, emr.frei@gmail.com)
Notes:

* This site requires you to sign in to view products. It's using three accounts now.
To create a new account on website it's not necessary the real existence of the E-Mail account used for that purpose,
this is that way now but it could be different at future.
* This is using concurrent requests and the number of concurrent requests to use is calculated locally.
Momentarilly it's the same as number of website accounts to use.
* The price which the website is displaying is VAT excluded, the spider should to add the 20% on top.

"""


import os
import time
import pandas as pd
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.url import urljoin_rfc, url_query_parameter, add_or_replace_parameter
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from product_spiders.phantomjs import PhantomJS
from product_spiders.config import DATA_DIR


class DoricCakeCrawftsSpider(BaseSpider):
    name = 'culpitt-doriccakecrafts.co.uk'
    allowed_domains = ['doriccakecrafts.co.uk']
    start_urls = ['http://www.doriccakecrafts.co.uk']
    download_delay = 10
    login_account = ('pompis.cake@pompis.com', '1234')

    def __init__(self, *args, **kwargs):
        super(DoricCakeCrawftsSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        self.search_all_done = False
        self._browser = PhantomJS(load_images=True)
        self.try_deletions = True
        self.new_ids = []
        self.viewed_urls = []

    def _get_prev_crawl_filename(self):
        filename = None
        if hasattr(self, 'prev_crawl_id'):
            filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
        return filename

    def spider_idle(self, spider):
        if not self.search_all_done:
            self.search_all_done = True
            request = Request(self.start_urls[0],
                              dont_filter=True,
                              callback=self.parse_search_all,
                              meta={'cookiejar': 1})
            self._crawler.engine.crawl(request, self)
        elif self.try_deletions:
            self.try_deletions = False
            request = Request(self.start_urls[0],
                              dont_filter=True,
                              callback=self.parse_deletions,
                              meta={'cookiejar': 1})
            self._crawler.engine.crawl(request, self)

    def spider_closed(self, spider):
        self._browser.close()

    def start_requests(self):

        self._browser.get('http://www.doriccakecrafts.co.uk/account/login')
        email_input = self._browser.driver.find_element_by_id('email')
        password_input = self._browser.driver.find_element_by_id('password')
        submit_button = self._browser.driver.find_element_by_id('login')
        email_input.send_keys(self.login_account[0])
        password_input.send_keys(self.login_account[1])
        submit_button.click()

        yield Request('http://www.doriccakecrafts.co.uk/account/login',
                      callback=self.sign_in,
                      meta={'cookiejar': 1},
                      dont_filter=True)

    def sign_in(self, response):
        req = FormRequest.from_response(response,
                                        formnumber=1,
                                        formdata={'email': self.login_account[0],
                                                  'password': self.login_account[1]},
                                        callback=self.parse_categories,
                                        meta={'cookiejar': response.meta['cookiejar']})
        yield req

    def parse_categories(self, response):
        if response.url != 'http://www.doriccakecrafts.co.uk/account':
            self.log('WARNING: Login unsuccessful for account: %s' % self.login_account[0])
            return
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = filter(lambda u: u != '#',
                            hxs.select('//*[@id="top-nav"]//ul/li[1]//a/@href|'
                                       '//*[@id="top-nav"]//ul/li[2]//a/@href')
                            .extract())
        cookie_jar = response.meta['cookiejar']
        for url in categories:
            url = urljoin_rfc(base_url, url)
            url = add_or_replace_parameter(url, 'page', '1')
            url = add_or_replace_parameter(url, 'per_page', '200')
            yield Request(url,
                          callback=self.parse_results,
                          meta={'cookiejar': cookie_jar})

    def parse_search_all(self, response):
        yield Request('http://www.doriccakecrafts.co.uk/search/results/+?per_page=200&sort=PriceHiLo&page=1&search_term=+',
                      callback=self.parse_results,
                      meta={'cookiejar': response.meta['cookiejar']})

    def parse_deletions(self, response):
        filename = self._get_prev_crawl_filename()
        if filename and os.path.exists(filename):
            old_products = pd.read_csv(filename, dtype=pd.np.str)
            deletions = old_products[old_products['identifier'].isin(self.new_ids) == False]
            for product_url in deletions['url']:
                self._browser.get(product_url)
                response = HtmlResponse(url=self._browser.driver.current_url, body=self._browser.driver.page_source, encoding='utf-8')
                for item in self.parse_product(response):
                    if item['identifier'] not in self.new_ids:
                        self.new_ids.append(item['identifier'])
                        yield item
                time.sleep(10)

    def parse_results(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//div[contains(@class, "item") and contains(@class, "product")]')
        cookie_jar = response.meta['cookiejar']
        current_page = url_query_parameter(response.url, 'page')
        pages_found = bool(hxs.select('//div[@class="item-count"]/strong/text()').extract())
        if current_page and pages_found:
            current_page = int(current_page)
            per_page = int(url_query_parameter(response.url, 'per_page'))
            total_items = int(hxs.select('//div[@class="item-count"]/strong/text()').extract()[-1])
            next_page = current_page + 1
            total_pages = total_items / per_page
            if (total_items % per_page) > 0:
                total_pages += 1
            if next_page <= total_pages:
                next_url = add_or_replace_parameter(response.url, 'page', str(next_page))
                yield Request(next_url, meta={'cookiejar': cookie_jar}, callback=self.parse_results)

        for product in products:
            product_url = product.select('.//div[@class="title"]//a/@href').extract()
            if not product_url:
                continue
            product_url = urljoin_rfc(base_url, product_url[0])
            if product_url in self.viewed_urls:
                continue

            self.viewed_urls.append(product_url)

            self._browser.get(product_url)
            response = HtmlResponse(url=self._browser.driver.current_url, body=self._browser.driver.page_source, encoding='utf-8')
            for item in self.parse_product(response):
                if item['identifier'] not in self.new_ids:
                    self.new_ids.append(item['identifier'])
                    yield item

            options = product.select('.//*[@class="color-selector-items"]/a/@href').extract()
            for option_url in options:
                option_url = urljoin_rfc(base_url, option_url)
                if option_url in self.viewed_urls:
                    continue
                self.viewed_urls.append(option_url)
                self._browser.get(option_url)
                response = HtmlResponse(url=self._browser.driver.current_url, body=self._browser.driver.page_source, encoding='utf-8')
                for item in self.parse_product(response):
                    if item['identifier'] not in self.new_ids:
                        self.new_ids.append(item['identifier'])
                        yield item

                time.sleep(5)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        options_values = hxs.select('//select[contains(@id, "label_index_")]/option[@selected]/@value').re(r'(\d+)')

        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//*[@id="product-title"]/text()')
        loader.add_xpath('sku', '//*[@id="product-sku"]/text()', re=r'Item Code: (.*)')
        loader.add_value('url', response.url)
        try:
            loader.add_value('category', hxs.select('//div[contains(@class, "breadcrumb")]/a/text()').extract()[1:-1])
        except:
            loader.add_value('category', '')
        product_id = hxs.select('//input[@name="product_id"]/@value').extract()[0]
        product_option_id = hxs.select('//input[@name="product_option_id"]/@value').extract()[0]
        if options_values:
            product_option_id = ':'.join(options_values)
        if product_id != product_option_id:
            loader.add_value('identifier', product_id + ':' + product_option_id)
        else:
            loader.add_value('identifier', product_id)

        product_price = hxs.select('//*[@id="product-sale-price"]').re(r'[\d,.]+')
        if product_price:
            product_price = round(Decimal(product_price[0]) * Decimal('1.2'), 2)
        else:
            product_price = round(Decimal(response.meta.get('product_price', '0')) * Decimal('1.2'), 2)
        loader.add_value('price', product_price)

        if bool(hxs.select('//*[@id="available_temporary" and '
                           'contains(text(), "temporarily out of stock") and '
                           'contains(@style, "display: block")]')
                .extract()): loader.add_value('stock', 0)

        product_image = hxs.select('//a[@id="product-image-zoom"]/@href').extract()
        if product_image:
            loader.add_value('image_url', urljoin_rfc(base_url, product_image[0]))

        yield loader.load_item()

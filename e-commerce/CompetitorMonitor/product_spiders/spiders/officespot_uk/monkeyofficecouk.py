# -*- coding: utf-8 -*-
import re
import time
import random
from decimal import Decimal
from urlparse import urljoin

from scrapy.contrib.spiders import SitemapSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoader

USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/537.75.14',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.116 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.131 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.131 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:28.0) Gecko/20100101 Firefox/28.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.116 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:28.0) Gecko/20100101 Firefox/28.0',
    'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.116 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.131 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:29.0) Gecko/20100101 Firefox/29.0',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows NT 6.1; rv:28.0) Gecko/20100101 Firefox/28.0',
    'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.116 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.131 Safari/537.36',
]


class MonkeyOfficeSpider(SitemapSpider):
    name = u'monkeyoffice.co.uk'
    allowed_domains = [u'www.monkeyoffice.co.uk']
    # start_urls = [u'http://www.monkeyoffice.co.uk/category.aspx']
    sitemap_urls = ['http://www.monkeyoffice.co.uk/sitemap.xml']
    sitemap_rules = [
        ('/productinfo.aspx', 'parse_product_page'),
    ]
    product_name_xpath = '//div[@class="product-title-container"]/h1/text()'
    shipping_cost = Decimal('3.95')

    handle_httpstatus_list = [500]

    max_retry_count = 5

    errors = []

    def _parse_sitemap(self, response):
        for req in super(MonkeyOfficeSpider, self)._parse_sitemap(response):
            if isinstance(req, Request):
                req = req.replace(
                    meta={'dont_retry': True,
                          'handle_httpstatus_list': [500],
                          'dont_merge_cookies': True},
                    headers={'User-Agent': random.choice(USER_AGENTS)})
                yield req
            else:
                yield req

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        anchors = hxs.select('//div[@id="panelMfr"]/div/ul/li[position() != last()]/a')
        for anchor in anchors:
            url = anchor.select('@href').extract().pop()
            cat = anchor.select('text()').extract().pop().strip()
            yield Request(urljoin(get_base_url(response), url), callback=self.parse_category, meta={"category": cat})

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # self.log("Meta: %s" % pprint.pformat(response.meta))
        # check if its a redirected product page
        if ('redirect_times' in response.meta and response.meta['redirect_times'] and hxs.select(self.product_name_xpath)):
            self.log("Category-To-Product Redirection to URL: %s" % response.url)
            yield Request(
                urljoin(base_url, response.url),
                callback=self.parse_product_page,
                dont_filter=True,
                meta={"category": response.meta['category']}
            )

        else:
            all_page = hxs.select('//span[@id="ctl00_ContentPlaceHolder1_lblresultsperpage"]/a[contains(text(), "All")]/@href').extract()
            if all_page:
                yield Request(urljoin(base_url, all_page[0]), callback=self.parse_category, meta={"category": response.meta['category']})
            else:
                """ parse all codes by regular expression
                    cause for some reason all xpath fails after extracting 112 result
                """
                codes = re.findall(r"AddToComparison\('([^']+)", response.body)
                for code in codes:
                    yield Request(
                        urljoin(base_url, '/productinfo.aspx?catref=%s' % code),
                        callback=self.parse_product_page,
                        meta={"category": response.meta['category']}
                    )

    def parse_product_page(self, response):
        if response.status == 500:
            retry = int(response.meta.get('retry', 0))
            if retry < 10:
                time.sleep(60)
                retry += 1
                yield Request(response.request.url,
                              dont_filter=True,
                              callback=response.request.callback,
                              meta={'dont_retry': True,
                                    'handle_httpstatus_list': [500],
                                    'retry': retry,
                                    'dont_merge_cookies': True},
                              headers={'User-Agent': random.choice(USER_AGENTS)})
                return

        # skip if it's home page
        if response.url.endswith('home.aspx'):
            return

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        quantity = hxs.select('//div[@class="stock" and contains(text(), "Stock Availability")]//text()').extract()
        quantity = " ".join([x.strip() for x in quantity[1:]])

        self.log("Availability: %s" % quantity)

        id_xpath = '//div[@class="new-review"]/input[@id="ctl00_ContentPlaceHolder1_hfCatalogueRef"]/@value'

        loader = ProductLoader(item=Product(), selector=hxs)
        identifier = hxs.select('//div[@class="new-review"]/input[@id="ctl00_ContentPlaceHolder1_hfCatalogueRef"]/@value').extract()
        if not identifier:
            try_no = response.meta.get('try', 1)
            if try_no < self.max_retry_count:
                meta = {
                    'try': try_no + 1
                }
                self.log("[WARNING] Retrying. Failed to scrape product identifier from page: %s" % response.url)
                yield Request(response.request.url,
                              callback=response.request.callback,
                              meta=meta,
                              dont_filter=True)
            else:
                self.log("[WARNING] Gave up. Failed to scrape product identifier from page: %s" % response.url)
                self.errors.append("Failed to scrape product identifier from page: %s" % response.url)
            return
        identifier = identifier[0]

        loader.add_value('url', response.url)  # urljoin(base_url, '/productinfo.aspx?catref='+identifier))

        loader.add_xpath('name', self.product_name_xpath)
        image_url = hxs.select('//a[@id="zoom1"]/img/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin(base_url, image_url[0]))

        loader.add_xpath(
            'price',
            '//span[@class="ProductInfoPrice"]/b/text()')
        category = response.meta.get('category')
        if not category:
            category = hxs.select('//*[@id="ctl00_lblbreadcrumbs"]//a[last()]/text()').extract()
        loader.add_value('category', category)
        # loader.add_xpath('category', '//span[@id="ctl00_lblbreadcrumbs"]/a[last()]/text()')
        # loader.add_xpath('sku', '//div[@class="manufacturer-code"]/span/text()')
        loader.add_value('sku', identifier)
        loader.add_value('identifier', identifier)

        loader.add_value('stock', quantity, re='[0-9]+')

        yield loader.load_item()

    def calculate_price(self, value):
        res = re.search(r'[.0-9]+', value)
        if res:
            price = Decimal(res.group(0))
            self.log("Price: %s" % price)
            return (price) * Decimal('1.2')  # 20% VAT
        else:
            return None

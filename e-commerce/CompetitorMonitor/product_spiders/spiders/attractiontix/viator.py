import os
import csv
import json
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector

from product_spiders.items import Product, ProductLoader
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

HERE = os.path.abspath(os.path.dirname(__file__))

LOCATIONS = [['Bodrum', '4292'], ['Majorca', '955'], ['Algarve', '774'], ['Antalya', '586'], ['Barcelona', '562'],
             ['Cancun', '631'], ['Costa Del Sol', '790'], ['Dubai', '828'], ['Gran Canaria', '792'],
             ['Hurghada', '800'], ['Ibiza', '4217'], ['Las Vegas', '684'], ['London', '737'], ['Los Angeles', '645'],
             ['Miami', '662'], ['New York', '687'], ['Orlando', '663'], ['Paris', '479'], ['Reykjavik', '905'],
             ['Riviera Maya', '770'], ['Rome', '511'], ['San Francisco', '651'],
             ['Sharm el Sheikh', '827'], ['Sorrento', '947']]


class ViatorSpider(BaseSpider):
    name = 'viator.com'
    allowed_domains = ['viator.com', '144.76.118.46']
    start_urls = ['http://www.viator.com']
    dates = []
    deduplicate_identifiers = True

    def parse(self, response):
        yield Request('http://www.viator.com/changeCurrency.jspa?currencyCode=GBP&page=', callback=self.parse_all)

    def parse_all(self, response):
        with open(os.path.join(HERE, 'atix.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                d = row['DateFrom'].split('/')
                d[-1] = '20' + d[-1]
                d = '/'.join(d)
                if d not in self.dates:
                    self.dates.append(d)

        self.log('%s dates to crawl' % len(self.dates))

        for l in LOCATIONS:
            url = 'http://www.viator.com/ajax-getProducts.jspa?' + \
                  'destinationID=%s&sortBy=SCORE&pageIndex=1&pageLister.page=1' % l[1]
            yield Request(url, meta={'location': l, 'page': 1, 'cookiejar': l[0]}, callback=self.parse_locations)

        # yield Request('http://www.viator.com/tours/Paris/Disneyland-Paris-Ticket/d479-5307DISNEYPASS', callback=self.parse_product,
        #              meta={'location': 'Paris', 'cookiejar': 'Paris'})

    def parse_locations(self, response):
        products = []
        try:
            hxs = HtmlXPathSelector(response)
            products = hxs.select('//h2[@class="man product-title"]/a/@href').extract()
        except:
            return

        if products:
            l = response.meta['location']
            page = response.meta['page']
            self.log(str(products))
            next_ = 'http://www.viator.com/ajax-getProducts.jspa?' + \
                    'destinationID=%s&sortBy=SCORE&pageIndex=%s&pageLister.page=%s' % (l[1], page + 1, page + 1)
            yield Request(next_, meta={'location': l, 'page': page + 1, 'cookiejar': l[0]},
                          callback=self.parse_locations)

            for product in products:
                yield Request(urljoin_rfc(get_base_url(response), product), meta={'location': l},
                              callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        try:
            name = hxs.select('//span[@itemprop="name"]/text()').extract()[0]
        except IndexError:
            return
        id_ = hxs.select('//input[@name="id"]/@value').extract()[0]
        product_id = hxs.select('//input[@name="productId"]/@value').extract()[0]
        product_type = hxs.select('//input[@name="productType"]/@value').extract()[0]
        code = hxs.select('//input[@name="code"]/@value').extract()[0]
        options_url = 'http://www.viator.com/popups/priceAvailCal.jspa?code=%s&productType=%s&id=%s&setLocale=en'
        options_url = options_url % (code, product_type, id_)
        yield Request(options_url, callback=self.parse_options, meta={'name': name,
                                                                      'location': response.meta['location'],
                                                                      'code': code, 'product_id': id_,
                                                                      'url': response.url,
                                                                      'product_type': product_type,
                                                                      'cookiejar': response.meta['location']})

    def parse_options(self, response):
        hxs = HtmlXPathSelector(response)
        options = hxs.select('//div[@class="tour_options"]//li//a')
        for i, opt in enumerate(options):
            tour_grade_code = re.search('tourGradeCode=(.*?)&', opt.select('./@href').extract()[0]).groups()[0]
            sub_name = opt.select('./strong/text()').extract()[0].strip()
            option_url = response.url + '&tourGradeCode=%s' % tour_grade_code
            yield Request(option_url, callback=self.parse_option, meta={'name': response.meta['name'] + ' ' + sub_name,
                                                                        'location': response.meta['location'],
                                                                        'code': response.meta['code'],
                                                                        'product_id': response.meta['product_id'],
                                                                        'url': response.meta['url'],
                                                                        'cookiejar': response.meta['location'],
                                                                        'product_type': response.meta['product_type'],
                                                                        'sub_id': tour_grade_code, 'num': i})
        if not options:
            res = hxs.select('//div[@class="unit size1of7"]/a[@href="#"]/div[@class="date-num"]/../@onclick')
            date_ = re.search('(\d+-\d+-\d+)', res[0].extract()).groups()[0]

            meta = {
                'name': response.meta['name'],
                'location': response.meta['location'],
                'code': response.meta['code'],
                'product_id': response.meta['product_id'],
                'url': response.meta['url'],
                'cookiejar': response.meta['location'],
                'product_type': response.meta['product_type'],
            }

            url = 'http://www.viator.com/tour-options/popup/showTourGradePricing.jspa?' + \
                  'bookDate=%s&code=%s&productType=%s&id=%s&setLocale=en'
            url = url % (date_, meta['code'], meta['product_type'], meta['product_id'])

            yield Request(url, callback=self.parse_prices, meta=meta)

    def parse_option(self, response):
        hxs = HtmlXPathSelector(response)
        res = hxs.select('//div[@class="unit size1of7"]/a[@href="#"]/div[@class="date-num"]/../@onclick')
        try:
            date_ = re.search('(\d+-\d+-\d+)', res[0].extract()).groups()[0]
        except:
            retry = int(response.meta.get('retry', 0))
            if retry < 10:
                new_meta = response.meta.copy()
                new_meta['retry'] = retry + 1
                yield Request(response.url, meta=new_meta, callback=self.parse_option, dont_filter=True)
                return

        url = 'http://www.viator.com/tour-options/popup/showTourGradePricing.jspa' + \
              '?code=%s&productType=%s&id=%s&setLocale=en&tourGradeCode=%s&bookDate=%s'
        url = url % (response.meta['code'], response.meta['product_type'], response.meta['product_id'],
                     response.meta['sub_id'], date_)

        yield Request(url, callback=self.parse_prices, meta=response.meta)

    def parse_prices(self, response):
        if not len(response.body):
            return

        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        num = response.meta.get('num', 0)
        loader.add_value('identifier', response.meta['code'] + ':' + (str(num) if not num else response.meta['sub_id']) + ':Adult')
        # loader.add_value('sku', d)
        loader.add_value('brand', 'Adult')
        loader.add_value('category', response.meta['location'][0])
        loader.add_value('url', response.meta['url'])
        loader.add_value('name', response.meta['name'])
        price = hxs.select('//table[contains(@class, "pricing_table")]/tbody/tr[2]/td[2]//text()').extract()
        if price:
            loader.add_value('price', price[0])
            yield loader.load_item()

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('identifier', response.meta['code'] + ':' + (str(num) if not num else response.meta['sub_id']) + ':Child')
        # loader.add_value('sku', d)
        loader.add_value('brand', 'Child')
        loader.add_value('category', response.meta['location'][0])
        loader.add_value('url', response.meta['url'])
        loader.add_value('name', response.meta['name'])
        price = hxs.select('//table[contains(@class, "pricing_table")]/tbody/tr[2]/td[3]//text()').extract()
        if price:
            loader.add_value('price', price[0])
            yield loader.load_item()

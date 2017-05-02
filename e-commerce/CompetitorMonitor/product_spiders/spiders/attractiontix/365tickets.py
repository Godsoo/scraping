# -*- coding: utf-8 -*-
import os
import csv
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector

from product_spiders.items import Product, ProductLoader
from product_spiders.spiders.BeautifulSoup import BeautifulSoup
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

HERE = os.path.abspath(os.path.dirname(__file__))

LOCATIONS = [['Barcelona', 'http://www.365tickets.co.uk/europe/spain/barcelona'],
             ['Benidorm', 'http://www.365tickets.co.uk/europe/spain/benidorm'],
             ['Costa Del Sol', 'http://www.365tickets.co.uk/europe/spain/costa-de-luz/'],
             ['Ibiza', 'http://www.365tickets.co.uk/europe/spain/ibiza/'],
             ['Las Vegas', 'http://www.365tickets.co.uk/united-states/nevada/las-vegas/'],
             ['London', 'http://www.365tickets.co.uk/united-kingdom/england/central-london'],
             ['London', 'http://www.365tickets.co.uk/united-kingdom/england/outer-london'],
             ['Los Angeles', 'http://www.365tickets.co.uk/united-states/california/los-angeles/'],
             ['Miami', 'https://www.365tickets.co.uk/united-states/florida/miami/'],
             ['New York', 'http://www.365tickets.co.uk/united-states/new-york/new-york-city/'],
             ['Orlando', 'https://www.365tickets.co.uk/united-states/florida/orlando/'],
             ['Paris', 'http://www.365tickets.co.uk/europe/france'],
             ['United Kingdom', 'http://www.365tickets.co.uk/united-kingdom/england'],
             ['United Kingdom', 'http://www.365tickets.co.uk/united-kingdom/scotland'],
             ['United Kingdom', 'http://www.365tickets.co.uk/united-kingdom/wales'],
             ['Rome', 'http://www.365tickets.co.uk/europe/italy/rome?q=Rome'],
             ['San Francisco', 'http://www.365tickets.co.uk/united-states/california/san-francisco/'],
             ['Tenerife', 'http://www.365tickets.co.uk/europe/spain/tenerife/']]


class S365TicketsSpider(BaseSpider):
    name = '365tickets.co.uk'
    allowed_domains = ['365tickets.co.uk']
    dates = []
    deduplicate_identifiers = True
    start_urls = ('http://www.365tickets.co.uk/home/change_currency/GBP?return=/', )

    def parse(self, response):
        with open(os.path.join(HERE, 'atix.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                d = row['DateFrom'].split('/')
                if len(d[-1]) < 4:
                    d[-1] = '20' + d[-1]
                d = '/'.join(d)

                if d not in self.dates:
                    self.dates.append(d)

        self.log('%s dates to crawl' % len(self.dates))

        for l in LOCATIONS:
            url = l[1]
            yield Request(url, meta={'location': l[0]}, callback=self.parse_location)


    def parse_location(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[starts-with(@id, "product_")]/h5/a/@href').extract()
        base_url = get_base_url(response)
        for p in products:
            if 'cardiff-castle-tickets/cardiff-castle-ticket' in p:
                continue
                
            yield Request(urljoin_rfc(base_url, p), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        options = hxs.select('//div[@id="product_list_html"]/a/@href').extract()
        base_url = get_base_url(response)
        for o in options:
            yield Request(urljoin_rfc(base_url, o), callback=self.parse_option, meta=response.meta, dont_filter=True)

    def parse_option(self, response):
        hxs = HtmlXPathSelector(response)
        name = ' '.join(hxs.select('//div[@id="product_desc"]/h1//text()').extract())
        option_name = hxs.select('//div[@id="accordian_active"]//h2/text()').extract()[0]
        try:
            product_id = hxs.select('//input[@class="product_id"]/@value').extract()[0]
        except IndexError:
            return

        if name.lower().strip() == option_name.lower().strip():
            final_name = name
        else:
            final_name = name + ' ' + option_name

        for d in self.dates:
            d_ = '-'.join(reversed(d.split('/')))
            formdata = {'return': hxs.select('//input[@id="return"]/@value').extract()[0],
                        'combo_product_id': hxs.select('//input[@id="combo_product_id"]/@value').extract()[0],
                        'visit_dates[%s]' % product_id: d_}
            f = FormRequest('http://www.365tickets.co.uk/availability_checker/check/%s/0/1' % product_id,
                            method='POST',
                            formdata=formdata,
                            meta={'location': response.meta['location'], 'name': final_name,
                                  'date': d, 'url': response.url, 'product_id': product_id}, callback=self.parse_date)

            yield f

    def parse_date(self, response):
        res = json.loads(response.body)
        if res['error']:
            return
        try:
            soup = BeautifulSoup(res['html'])
        except Exception:
            return

        all_prices = soup.findAll('td', {'class': 'table_desc'})
        adult_price = None
        child_price = None
        adult_ids = ['adult']
        child_ids = ['children', 'child', 'junior']
        excluded_ids = ['concession', 'student', 'infant', 'niño']

        remaining_prices = []
        for p in all_prices:
            if not adult_price and 'adult' in p.text.lower():
                adult_price = p.parent.findAll('td')[2].text
            elif not child_price and ('child' in p.text.lower() or 'junior' in p.text.lower()):
                child_price = p.parent.findAll('td')[2].text
            else:
                remaining_prices.append(p)

        if adult_price:
            loader = ProductLoader(item=Product(), selector=HtmlXPathSelector())
            loader.add_value('identifier', response.meta['product_id'] + ':' + response.meta['date'] + ':Adult')
            loader.add_value('url', response.meta['url'])
            loader.add_value('sku', response.meta['date'])
            loader.add_value('category', response.meta['location'])
            loader.add_value('brand', 'Adult')
            loader.add_value('price', adult_price)
            loader.add_value('name', response.meta['name'])
            yield loader.load_item()
        if child_price:
            loader = ProductLoader(item=Product(), selector=HtmlXPathSelector())
            loader.add_value('identifier', response.meta['product_id'] + ':' + response.meta['date'] + ':Child')
            loader.add_value('url', response.meta['url'])
            loader.add_value('sku', response.meta['date'])
            loader.add_value('category', response.meta['location'])
            loader.add_value('brand', 'Child')
            loader.add_value('price', child_price)
            loader.add_value('name', response.meta['name'])
            yield loader.load_item()

        for p in remaining_prices:
            exclude = False
            for t in excluded_ids:
                if t.decode('utf8') in p.text.lower():
                    exclude = True
                    break

            if exclude:
                continue

            ticket_type = 'Adult'
            for t in child_ids:
                if t in p.text.lower():
                    ticket_type = 'Child'

            loader = ProductLoader(item=Product(), selector=HtmlXPathSelector())
            option_name = p.text.lower()
            loader.add_value('identifier', response.meta['product_id'] + ':' + response.meta['date']
                                           + ':' + ticket_type + ':' + option_name)
            loader.add_value('url', response.meta['url'])
            loader.add_value('sku', response.meta['date'])
            loader.add_value('category', response.meta['location'])
            loader.add_value('brand', ticket_type)
            loader.add_value('price', p.parent.findAll('td')[2].text)
            loader.add_value('name', response.meta['name'] + ' - ' + p.text)
            if loader.get_output_value('price'):
                yield loader.load_item()


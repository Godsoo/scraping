import re
import json
import urlparse
from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timedelta
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector, XmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from urlparse import urljoin

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


def format_price(price):
    if price is None:
        return ''

    return str(price.quantize(Decimal('0.01'), rounding=ROUND_DOWN))

class LastMinuteSpider(BaseSpider):
    name = 'lastminute.com'
    allowed_domains = ['lastminute.com']
    start_urls = ('http://www.lastminute.com/site/entertainment/theatre/event-results.html'
                  + '?skin=engb.lastminute.com&eventType=&sortBy=defaultDSC&startIndex=1' +
                  '&keyword=I+don%27t+mind&location=London&catID=&dayVal=0&monthVal=0&numTickets=1&maxPrice=',
    'http://www.lastminute.com/site/entertainment/event-results.html?skin=engb.lastminute.com&eventType=&sortBy='+
    'defaultDSC&keyword=lion+king&location=London&catID=&dayVal=0&monthVal=0&numTickets=&maxPrice=',
    'http://www.lastminute.com/site/entertainment/event-results.html?skin=engb.lastminute.com&eventType=&sortBy=defaultDSC&keyword=let+it+be&location=London&catID=&dayVal=0&monthVal=0&numTickets=&maxPrice=')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="item_wrapper"]')

        for product in products:
            url = product.select('.//h3/a/@href').extract()
            if url:
                yield Request(urljoin_rfc(get_base_url(response), url.pop()), callback=self.parse_product)

        next_ = hxs.select('//a[@class="next"]/@href')
        if next_:
            next_ = urljoin_rfc(get_base_url(response), next_.extract()[0])
            yield Request(next_)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #url = hxs.select('//div[@class="checkAvail"]/a/@href').extract()[0]
        q_string = urlparse.parse_qs(urlparse.urlparse(response.url).query)
        if 'PRODID' in q_string:
            name = hxs.select('//title/text()').extract().pop()
            price = extract_price(hxs.select('//table[@class="rule_box"]/tr/td[contains(., "Price")]/following-sibling::td/text()').extract().pop().strip())
            identifier = q_string['PRODID']
            image_url = hxs.select('//table[contains(@class, "rule_left_right")]/tr/td/img/@src').extract()
            loader = ProductLoader(item=Product(), selector=HtmlXPathSelector())
            loader.add_value('name', name)
            loader.add_value('price', format_price(price))
            loader.add_value('url', response.url)
            loader.add_value('identifier', identifier)
            loader.add_value('image_url', urljoin(base_url, image_url.pop()))
            yield loader.load_item()
            return
        name = hxs.select('//h1[@class="eventHeading"]/text()').extract()[0]
        name = name.split('-')[0].replace('tickets', '').replace('Tickets', '').strip()
        #yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_product_performances,
        #              meta={'name': name, 'url': response.url})
        date_from = datetime.now()
        date_to = date_from + timedelta(days=7*6)
        d_ = date_from
        months = []
        while d_ != date_to:
            months.append(d_.month)
            d_ += timedelta(days=1)

        event_id = re.search('eventID=([^&]*)', response.url).groups()[0]

        months = sorted(list(set(months)))
        for i, m in enumerate(months):
            if not i:
                url = 'http://www.lastminute.com/site/entertainment/entertainment_event_availibility_query_json?' + \
                      'eventID=%s&monthVal=&selectDate=&selectTime=&venueIDCode=' % (event_id,)
            else:
                url = 'http://www.lastminute.com/site/entertainment/entertainment_event_availibility_query_json?' + \
                      'eventID=%s&monthVal=%s/%s&selectDate=&selectTime=&venueIDCode=' % (event_id,
                                                                                       str(m) if m > 9 else '0' + str(m),
                                                                                       date_to.year)

            yield Request(url, callback=self.parse_product_performances, meta={'name': name, 'url': response.url})


    def parse_product_performances(self, response):
        data = json.loads(response.body)
        for date_ in data['performanceDates']:
            date_data = data['performanceDates'][date_]
            for time_ in date_data['performanceTimes']:
                for ticket in time_['tickets']:
                    d_time = time_['time'].split('T')[1]
                    perf_date = datetime.strptime(date_ + ' ' + d_time, '%d/%m/%Y %H:%M:%S')
                    fee = re.search('excl (.+) fee', ticket['description'])
                    if fee:
                        fee = fee.groups()[0]
                        fee = extract_price(fee)
                    else:
                        fee = Decimal(0)
                    price = extract_price(str(ticket['price']))
                    if perf_date.hour > 17 or perf_date.hour == 17 and perf_date.minute >= 30:
                        time_s = 'E'
                    else:
                        time_s = 'M'

                    show_id = re.search('eventID=([^&]+)&', response.url).groups()[0]
                    date_from = datetime.now()
                    date_to = date_from + timedelta(days=7*6)
                    if perf_date <= date_to:
                        loader = ProductLoader(item=Product(), selector=HtmlXPathSelector())
                        loader.add_value('name', response.meta['name'])
                        loader.add_value('price', format_price(price + fee))
                        loader.add_value('brand', format_price(price))
                        loader.add_value('url', response.meta['url'])
                        loader.add_value('identifier', ':'.join([show_id, perf_date.strftime('%Y-%m-%d'),
                                                                 time_s, format_price(price)]))
                        p = loader.load_item()
                        p['sku'] = perf_date.strftime('%d-%m-%y') + ' ' + time_s
                        yield p




    '''
    def parse_product_performances(self, response):
        hxs = HtmlXPathSelector(response)
        date_from = datetime.now()
        date_to = date_from + timedelta(days=7*6)
        name = response.meta['name']
        performances = hxs.select('//table[@id="listTickets"]//tr')[1:]
        date_reached = False
        for perf in performances:
            url = perf.select('.//td')[-1].select('./a/@href').extract()[0]
            date_ = perf.select('.//td')[2].select('./span/text()').extract()[0]
            time_ = perf.select('.//td')[3].select('./span/text()').extract()[0]
            perf_date = datetime.strptime(date_ + ' ' + time_, '%d %B %Y %H:%M')
            if perf_date > date_to:
                date_reached = True
                break

            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_single_performance,
                          meta={'name': name, 'date': date_, 'time': time_, 'url': response.meta['url']})

        next_ = hxs.select('//a[@class="next"]/@href')
        if next_ and not date_reached:
            #next_ = urljoin_rfc(get_base_url(response), next_.extract()[0])
            current = int(hxs.select('//ul[@class="paging right"]//strong/text()').extract()[0])
            next_ = re.sub('startIndex=\d+', 'startIndex=%s' % ((current * 10) + 1,), response.url)            
            yield Request(next_, callback=self.parse_product_performances, meta=response.meta)

        if not date_reached:
            next_ = hxs.select('//div[@class="nextMonth"]/a/@href')
            if next_:
                next_ = urljoin_rfc(get_base_url(response), next_.extract()[0])
                yield Request(next_, callback=self.parse_product_performances, meta=response.meta)

    def parse_single_performance(self, response):
        date_ = response.meta['date']
        time_ = response.meta['time']
        perf_date = datetime.strptime(date_ + ' ' + time_, '%d %B %Y %H:%M')
        hxs = HtmlXPathSelector(response)
        options = hxs.select('//div[starts-with(@class, "mockTblRow")]')
        for opt in options:
            fee = opt.select('.//span[@class="ticketType"]/text()')[0].extract()
            fee = re.search('excl (.+) fee', fee)
            if fee:
                fee = fee.groups()[0]
                fee = extract_price(fee)
            else:
                fee = Decimal(0)

            price = opt.select('.//span[@class="ticketPrice"]/strong/text()')[0].extract()
            price = extract_price(price)

            loader = ProductLoader(item=Product(), selector=opt)
            loader.add_value('name', response.meta['name'])
            loader.add_value('price', price + fee)
            loader.add_value('brand', str(price))
            loader.add_value('url', response.meta['url'])

            if perf_date.hour > 17 or perf_date.hour == 17 and perf_date.minute >= 30:
                time_s = 'E'
            else:
                time_s = 'M'

            show_id = re.search('eventID=([^&]+)&', response.url).groups()[0]
            loader.add_value('identifier', ':'.join([show_id, perf_date.strftime('%Y-%m-%d'), time_s, str(price)]))
            p = loader.load_item()
            p['sku'] = perf_date.strftime('%d-%m-%y') + ' ' + time_s

            yield p
    '''

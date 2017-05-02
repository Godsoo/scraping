import re
import json
import urlparse
from collections import defaultdict
from datetime import datetime, timedelta
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector, XmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


SHOWS_DATA = '''
<show id="%s">
  <location id="LDN"/>
  <performance type="A" />
  <startDate>%s</startDate>
  <endDate>%s</endDate>
  <tickets>1</tickets>
  <limit>100</limit>
  <seatDetails>off</seatDetails>
</show>
'''

SHOWS_DATA_NEXT = '''
<show id="%s">
  <location id="LDN"/>
  <performance type="A" />
  <startDate>%s</startDate>
  <endDate>%s</endDate>
  <tickets>1</tickets>
  <limit>100</limit>
  <seatDetails>off</seatDetails>
  <navigate key="%s">next</navigate>
</show>
'''

class EncoreSpider(BaseSpider):
    name = 'encoretickets.co.uk'
    allowed_domains = ['api.entstix.com']
    start_urls = ('https://api.entstix.com/api/v1/xlive/content/show',)
    http_user = 'intelligenteye'
    http_pass = 'yApUCrust6crach5'

    def parse(self, response):
        hxs = XmlXPathSelector(response)
        shows = hxs.select('//show')
        date_from = datetime.now()
        date_to = date_from + timedelta(days=7*6)

        for show in shows:
            name = show.select('./name/text()').extract()[0]
            url = show.select('./@href').extract()[0]
            show_id = url.split('/')[-1]
            show_data = SHOWS_DATA % (show_id, date_from.strftime('%Y-%m-%d'), date_to.strftime('%Y-%m-%d'))
            r = Request('https://api.entstix.com/api/v1/xlive/booking/book/availability/show', method='POST',
                        body=show_data, callback=self.parse_products, meta={'name': name, 'id': show_id})
            yield r

    def parse_products(self, response):
        hxs = XmlXPathSelector(response)
        show_id = response.meta['id']
        name = response.meta['name']
        if not hxs.select('/availability/moreResults/text()'):
            self.log('No results for %s, %s' % (show_id, name))
            return

        if hxs.select('/availability/moreResults/text()')[0].extract() != 'false':
            self.log('There are more results!')
            date_from = datetime.now()
            date_to = date_from + timedelta(days=7*6)
            show_data = SHOWS_DATA_NEXT % (show_id, date_from.strftime('%Y-%m-%d'), date_to.strftime('%Y-%m-%d'),
                                      hxs.select('/availability/navigate/@key')[0].extract())

            r = Request('https://api.entstix.com/api/v1/xlive/booking/book/availability/show', method='POST',
                        body=show_data, callback=self.parse_products, meta={'name': name, 'id': show_id})
            yield r

        products = hxs.select('.//performances/performance')
        weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        ids_seen = defaultdict(list)
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            face_value = product.select('.//faceValue/text()')[0].extract()
            price = product.select('.//saleprice/text()')[0].extract()
            date_ = product.select('.//date/text()')[0].extract()[4:]
            date_ = datetime.strptime(date_, '%d-%b-%Y %H:%M')
            type_ = product.select('.//type/text()')[0].extract()
            identifier = ':'.join([show_id, date_.strftime('%Y-%m-%d'), type_, face_value])
            if identifier in ids_seen and price not in ids_seen[identifier]:
                ids_seen[identifier].append(price)
                identifier += '-' + product.select('.//block/@id')[0].extract()
            else:
                ids_seen[identifier].append(price)

            loader.add_value('identifier', identifier)
            loader.add_value('brand', face_value)
            loader.add_value('price', price)
            loader.add_value('name', name)
            loader.add_value('category', weekdays[date_.weekday()])

            p = loader.load_item()
            p['sku'] = date_.strftime('%d-%m-%y') + ' ' + type_.upper()

            yield p

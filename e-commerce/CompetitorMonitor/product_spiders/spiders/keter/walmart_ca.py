import re
import json
import urllib
import logging
import datetime
import time

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.http.cookies import CookieJar

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

from keteritems import KeterMeta, Review, ReviewLoader

from phantomjs import PhantomJS


class WalmartCaSpider(BaseSpider):
    name = 'walmart.ca'
    allowed_domains = ['walmart.ca', 'bazaarvoice.com']
    start_urls = ('http://www.walmart.ca/',)

    errors = []

    def __init__(self, *args, **kwargs):

        self._search_urls = [
            ('Keter', 'http://www.walmart.ca/search/Keter'),
            ('Suncast', 'http://www.walmart.ca/search/Suncast'),
            ('RUBBERMAID', 'http://www.walmart.ca/search/RUBBERMAID/N-1000132'),
            ('Lifetime', 'http://www.walmart.ca/search/lifetime%20products%20inc'),
            ('Step 2', 'http://www.walmart.ca/search/Step2/N-1001354'),
            ('Step 2', 'http://www.walmart.ca/search/Step2/N-1001354+1001711'),
            ('Sterilite', 'http://www.walmart.ca/search/Sterilite'),
        ]

    def parse(self, response):
        return self._get_search_request(0)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        links = hxs.select('//div[@id="shelf-thumbs"]//div[@class="title"]/a/@href').extract()
        for url in links:
            prod_url = urljoin_rfc(base_url, url)
            yield Request(prod_url,
                          callback=self.parse_product,
                          meta=response.meta)

        next = hxs.select('//div[@id="shelf-pagination"]/a[@id="loadmore"]/@href').extract()
        for url in next:
            self._search_urls.append((response.meta['brand'], urljoin_rfc(base_url, url)))

        if response.meta['current'] < len(self._search_urls):
            yield self._get_search_request(response.meta['current'] + 1)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        try:
            product_data = json.loads(hxs.select('//script[contains(text(), "walPP.variantDataRawArr")]/text()')
                                      .re(r'walPP.variantDataRawArr = (\[.*\])')[0])[0]
        except:
            self.errors.append('WARNING: No product data in %s' % response.url)
            return

        price = product_data.get(u'price_store_price', None)
        if not price:
            browser = PhantomJS.create_browser()
            self.log('>>> BROWSER: GET => %s' % response.url)
            browser.get(response.url)
            self.log('>>> BROWSER: OK')
            time.sleep(5)

            hxs = HtmlXPathSelector(text=browser.page_source)

            browser.quit()

             # Monitor all products even without a price (as requested in #248)
            price = '.'.join(hxs.select('//div[@id="pricing"]/div[@class="price-main"]//text()').re(r'(\d+)')).strip()
            if not price:
                price_elem = hxs.select('//span[@id="store-price"][1]/text()').extract()
                if price_elem:
                    price = price_elem[0]
            if not price:
                store_prices = hxs.select('//div[contains(@id, "store-")]//div[@class="price"]//text()').extract()
                try:
                    price = '.'.join(re.findall(r'(\d+)', '.'.join(store_prices[:3])))
                except:
                    price = '0.00'
        else:
            price = price[0]

        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_value('category', product_data[u'Category'])
        product_loader.add_value('name', product_data[u'prod_name_en'])
        product_loader.add_value('sku', product_data[u'P_RollupKey'])
        product_loader.add_value('price', price.replace(',', ''))
        product_loader.add_value('identifier', product_data[u'P_UniqueKey'])

        product_loader.add_value('url', response.url)
        product_loader.add_value('brand', response.meta['brand'].strip().lower())
        product = product_loader.load_item()

        metadata = KeterMeta()
        metadata['brand'] = response.meta['brand']
        metadata['reviews'] = []
        product['metadata'] = metadata
        response.meta['product'] = product

        # the same as canadiantire.ca
        # http://www.canadiantire.ca/AST/browse/2/OutdoorLiving/3/OutdoorStorage/Sheds/PRD~0600292P/Keter+Rattan+Vertical+Shed.jsp?locale=en
        # http://canadiantire.ugc.bazaarvoice.com/9045/0600292P/reviews.djs?format=embeddedhtml
        # <script language="JavaScript" src="http://canadiantire.ugc.bazaarvoice.com/static/9045/bvapi.js" type="text/javascript"></script>
        try:
            part2 = product['sku']
        except:
            self.errors.append('WARNING: No sku in %s' % response.url)
            yield product
        else:
            if not part2:
                self.errors.append('WARNING: No sku in %s' % response.url)
                yield product
            else:
                reviews_url = 'http://api.bazaarvoice.com/data/batch.json?passkey=e6wzzmz844l2kk3v6v7igfl6i&apiversion=5.4&displaycode=2036-en_ca&resource.q2=reviews&filter.q2=isratingsonly%3Aeq%3Afalse&filter.q2=productid%3Aeq%3A' + part2
                yield Request(reviews_url, meta=response.meta, callback=self.parse_reviews)


    def parse_reviews(self, response):
        hxs = HtmlXPathSelector(response)
        product = response.meta['product']
        json_body = json.loads(response.body)

        reviews = json_body['BatchedResults']['q2']['Results']
        for review in reviews:
            review_loader = ReviewLoader(item=Review(), response=response, date_format="%B %d, %Y")
            review_date = datetime.datetime.strptime(review['SubmissionTime'].split('.')[0], '%Y-%m-%dT%H:%M:%S')
            review_loader.add_value('date', review_date.strftime("%B %d, %Y"))

            title = review['Title']
            text = review['ReviewText']

            if title:
                full_text = title[0] + '\n' + text
            else:
                full_text = text

            pros = review['Pros']
            cons = review['Cons']
            if pros:
                full_text += '\nPros: ' + ', '.join(pros)
            if cons:
                full_text += '\nCons: ' + ', '.join(cons)


            review_loader.add_value('full_text', full_text)
            rating = review['Rating']
            review_loader.add_value('rating', rating)
            review_loader.add_value('url', response.url)

            product['metadata']['reviews'].append(review_loader.load_item())

        yield product

    def _get_search_request(self, current):
        data = self._search_urls[current]
        return Request(data[1],
                       callback=self.parse_product_list,
                       meta={'brand': data[0],
                             'current': current})

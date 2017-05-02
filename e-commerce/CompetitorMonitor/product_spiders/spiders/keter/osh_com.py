import urllib
import logging
import re
try:
    import json
except ImportError:
    import simplejson as json

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from keteritems import KeterMeta, Review, ReviewLoader

class OshComSpider(BaseSpider):
    name = 'osh.com'
    allowed_domains = ['osh.com']
    user_agent = 'Googlebot/2.1 (+http://www.google.com/bot.html)'

    def start_requests(self):
        search_url = 'http://www.osh.com/search?q=%(brand)s&lclsrch'
        for brand in ('Keter', 'SUNCAST', 'RUBBERMAID', 'LIFETIME', 'STEP 2', 'STERILITE'):
            url = search_url % dict(brand=urllib.quote_plus(brand))
            meta = {'brand': brand}
            yield self.get_form_request_page(url=url, start_row='1', meta=meta)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        items = hxs.select('//div[@id="searchResults"]//h2/a/@href').extract()
        for item_url in items:
            yield Request(urljoin_rfc(base_url, item_url),
                          meta=response.meta, callback=self.parse_item)

        next_pages = set(hxs.select('//div[@class="pagesNav"]//li/a/@href')
                         .re(r'navigateToPage\(\'(\d+)\'\)'))

        for start_row in next_pages:
            yield self.get_form_request_page(url=base_url,
                                             start_row=start_row,
                                             meta=response.meta)

    def parse_item(self, response):
        hxs = HtmlXPathSelector(response)

        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_xpath('name', u'//h1/text()')
        sku = hxs.select(u'//div[@id="idAndAvailable"]/text()[1]').extract()[0]
        sku = sku.split(':')[1].strip()
        product_loader.add_value('brand', response.meta['brand'].lower())
        product_loader.add_value('sku', sku)

        price = hxs.select('//span[@id="productPrice"]/text()').extract()
        if not price:
            price = hxs.select('//span[@id="productPriceonsale"]/text()').extract()
        price = price[0].replace('$', '')
        product_loader.add_value('price', price)

        product_loader.add_value('url', response.url)
        product = product_loader.load_item()

        metadata = KeterMeta()
        metadata['brand'] = response.meta['brand']
        metadata['reviews'] = []
        product['metadata'] = metadata
        response.meta.update({'product': product})

        brand = response.meta['brand'].lower()
        product_name = product['name'].lower()

        if (brand in product_name.lower() or
            ''.join(brand.split()) in product_name.lower()):
                for x in self.parse_review(response):
                    yield x

    def parse_review(self, response):
        hxs = HtmlXPathSelector(response)
        product = response.meta['product']

        for review in hxs.select(u'//div[@class="pr-review-wrap"]'):
            item = Review()
            loader = ReviewLoader(item=Review(), selector=review, date_format=u'%m/%d/%Y')
            loader.add_xpath('date', u'.//div[contains(@class, "pr-review-author-date")]/text()')
            comments = review.select(u'.//p[@class="pr-comments"]/text()').extract()[0]
            bottom_line = review.select(u'.//div[@class="pr-review-bottom-line-wrapper"]/p/text()[2]').extract()
            if bottom_line:
                bottom_line = bottom_line[0]
            else:
                bottom_line = ''

            pros = hxs.select('.//div[contains(@class,"pr-attribute-pros")]//li/text()').extract()
            cons = hxs.select('.//div[contains(@class,"pr-attribute-cons")]//li/text()').extract()
            best_uses = hxs.select('.//div[contains(@class,"pr-attribute-bestuses")]//li/text()').extract()

            loader.add_value('full_text', u'%s\nBottom Line: %s\nPros: %s\nCons: %s\nBest Uses: %s\n' % (
                    comments, bottom_line, u', '.join(pros), u', '.join(cons), u', '.join(best_uses)))

            loader.add_value('rating', int(float(review.select(u'.//span[contains(@class,"pr-rating")]/text()').extract()[0])))
            loader.add_value('url', response.url)

            product['metadata']['reviews'].append(loader.load_item())

        next_url = hxs.select(u'//span[@class="pr-page-next"]/a/@href').extract()
        if next_url:
            yield Request(next_url[0], meta=response.meta, callback=self.parse_review)
        else:
            yield product

    def get_form_request_page(self, url, start_row, meta):
        return FormRequest(url=url,
                           formdata={'KEYWORDS': meta['brand'],
                                     'ONCLEARANCE': 'N',
                                     'ONSALE': 'N',
                                     'STARTROW': start_row},
                           meta=meta,
                           callback=self.parse)

# -*- coding: utf-8 -*-

import os
import csv
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import (
    urljoin_rfc,
    add_or_replace_parameter,
    url_query_parameter,
)

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

from reviewitems import LegoUSAMeta, Review, ReviewLoader

import demjson
import datetime

from product_spiders.config import DATA_DIR

HERE = os.path.abspath(os.path.dirname(__file__))


class ToysRUsSpider(BaseSpider):
    name = 'legousa-toysrus.com'
    allowed_domains = ['toysrus.com']
    start_urls = ('http://www.toysrus.com/category/index.jsp?categoryId=3696486&ab=TRU_Header:Utility3:Brand:LEGO:Home-Page',)
    _re_sku = re.compile('(\d\d\d\d\d?)')

    # Map deviation screenshot feature
    map_deviation_detection = True
    map_deviation_csv = os.path.join(HERE, 'toysrus_map_deviation.csv')

    def __init__(self, *args, **kwargs):
        super(ToysRUsSpider, self).__init__(*args, **kwargs)

        self.errors = []

    def start_requests(self):
        # Parse default items and then start_urls
        yield Request('http://www.toysrus.com', self.parse_default)

    def parse_default(self, response):
        if hasattr(self, 'prev_crawl_id'):
            with open(os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    yield Request(row['url'], self.parse_product)

        # Scrape start urls
        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        category_urls = hxs.select('//div[@id="module_Taxonomy1"]//p/a/@href').extract()
        for url in category_urls:
            url = urljoin_rfc(base_url, url)
            yield Request(add_or_replace_parameter(url, 'view', 'all'))

        product_urls = hxs.select('//div[@class="prodloop_cont"]//a[@class="prodtitle"]/@href').extract()
        for url in product_urls:
            url = urljoin_rfc(base_url, url)
            yield Request(url, callback=self.parse_product)

        next_page = hxs.select(u'//span[@class="next"]/../@href').extract()
        if next_page:
            url = urljoin_rfc(base_url, next_page[0])
            yield Request(url)

        for item in self.parse_product(response):
            yield item

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            retries = response.meta.get('retries', 0)
            if retries < 5:
                self.log('Retrying URL {}'.format(response.url))
                yield Request(response.url, meta={'retries': retries+1}, dont_filter=True)
                return
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        prod_id = url_query_parameter(response.url, 'productId')

        if prod_id:
            name = hxs.select('//div[@id="lTitle"]/h1/text()').extract()[0]

            sku = self._re_sku.findall(name)
            sku = sku[0] if sku else ''

            category = hxs.select(u'//a[@class="breadcrumb"]/text()').extract()
            category = category[-1].strip() if category else ''
            loader.add_value('identifier', prod_id)
            loader.add_value('name', name)
            brand = hxs.select('//li/h3[contains(text(), "By:")]/label/text()').extract()
            brand = brand[0].strip() if brand else ''
            loader.add_value('brand', brand)
            loader.add_value('category', category)
            loader.add_value('sku', sku)
            loader.add_value('url', response.url)
            price = hxs.select('//div[@id="price"]/ul/li[contains(@class, "retail")]/span/text()').extract()
            price = price[0].replace(',', '.') if price else ''
            loader.add_value('price', price)
            image = hxs.select('//meta[@property="og:image"]/@content').extract()
            image = image[0] if image else ''
            loader.add_value('image_url', image)

            product = loader.load_item()

            reviews_url = u'http://www.toysrus.com/pwr/content/%s/%s-en_US-1-reviews.js' % (self.calculate_url(prod_id), prod_id)
            metadata = LegoUSAMeta()
            metadata['reviews'] = []
            product['metadata'] = metadata
            meta = {'dont_retry': True, 'handle_httpstatus_list': [404, 302], 'cur_page': 1,
                    'product': product, 'product_url': response.url, 'dont_redirect': True,
                    'reviews_url': u'http://www.toysrus.com/pwr/content/' + u'%s/%s' % (self.calculate_url(prod_id), prod_id) + u'-en_US-%s-reviews.js'}
            yield Request(reviews_url, meta=meta, callback=self.parse_review)

    def parse_review(self, response):

        reviews = re.search(u'= (.*);$', response.body, re.DOTALL)

        product = response.meta['product']

        try:
            reviews = reviews.group(1)
            reviews = map(lambda x: x.get('r'), demjson.decode(reviews))
        except:
            reviews = None

        if response.status != 200 or not reviews:
            yield product
            return

        for review in reviews:
            loader = ReviewLoader(item=Review(), selector=review, date_format=u'%m/%d/%Y')
            try:
                date_review = datetime.datetime.strptime(review.get('d'), "%m/%d/%Y").date()
                date_review = date_review.strftime("%m/%d/%Y")
            except:
                date_review = review.get('d')

            loader.add_value('date', date_review)

            title = review['h']
            text = review['p']
            if isinstance(text, int):
                text = unicode(text)

            review_data = {}
            if review.has_key('g'):
                for data in review['g']:
                    review_data[data['n']] = u', '.join(map(unicode, data['v']))
            fields = [u'Pros', u'Cons', u'Best Uses']
            text += u' #&#&#&# '
            for field in fields:
                if review_data.get(field):
                    text += u'%s:\n%s\n' % (field, review_data.get(field))
            if review.has_key('b') and review['b']['k'] == 'Yes':
                text += u'Yes, I would recommend this to a friend.'
            else:
                text += u'No, I would not recommend this to a friend.'

            text += '\nFrom: %s' % review['w']
            if 'g' in review:
                for elem in review['g']:
                    if elem['k'] == 'describeyourself':
                        text += '\nAbout me: %s' % ', '.join(elem['v'])

            if review['o'] == 'e':
                text += '\nVerified buyer'

            loader.add_value('full_text', u'%s #&#&#&# %s' % (title, text))
            loader.add_value('product_url', response.meta['product_url'])
            loader.add_value('url', response.meta['product_url'])
            loader.add_value('sku', product['sku'])
            loader.add_value('rating', review['r'])
            product['metadata']['reviews'].append(loader.load_item())

        cur_page = response.meta['cur_page']

        url = response.meta['reviews_url'] % str(cur_page + 1)
        response.meta['cur_page'] += 1
        yield Request(url, meta=response.meta, callback=self.parse_review)

    def calculate_url(self, prod_id):
        cg = 0
        for cf in range(0, len(prod_id)):
            ce = ord(prod_id[cf])
            ce *= abs(255 - ce)
            cg += ce
        cg %= 1023
        cg = str(cg)
        ci = 4
        cg = '0' * (ci - len(cg)) + cg
        return cg[0 : ci / 2] + '/' + cg[ci / 2 : ci]

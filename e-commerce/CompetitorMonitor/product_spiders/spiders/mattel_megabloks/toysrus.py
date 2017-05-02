import os
import re
import datetime
import json
import csv
import cStringIO
import demjson

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)
from reviewitems import LegoUSAMeta, Review, ReviewLoader
from scrapy.shell import inspect_response
from urlparse import urljoin
from product_spiders.utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))


class ToysrusSpider(BaseSpider):
    name = 'mattelmegabloks-toysrus.com'
    allowed_domains = ['toysrus.com']
    start_urls = ('http://www.toysrus.com/',)
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:24.0) Gecko/20100101 Firefox/24.0'
    download_delay = 1
    keys = [
        ('Mattel', 'Mattel'),
        ('Barbie', 'Mattel'),
        ('Hot Wheels', 'Mattel'),
        ('Monster High', 'Mattel'),
        ('WWE', 'Mattel'),
        ('Disney princess', 'Mattel'),
        ('Max Steel', 'Mattel'),
        ('Ever After High', 'Mattel'),
        ('Matchbox', 'Mattel'),
        ('Little Mommy', 'Mattel'),
        ('Cars', 'Mattel'),
        ('Polly Pocket', 'Mattel'),
        ('DC Universe', 'Mattel'),
        ('Sofia the First', 'Mattel'),
        ('Planes', 'Mattel'),
        ('Frozen', 'Mattel'),
        ('Toy Story', 'Mattel'),
        ('Fijit Friends', 'Mattel'),
        ('Mega Bloks', 'Mega Bloks'),
        ("Assassin's Creed", 'Mega Bloks'),
        ('Call of Duty', 'Mega Bloks'),
        ('Cat', 'Mega Bloks'),
        (u'Create \u2018n Play', 'Mega Bloks'),
        ("Create 'n Play Junior", 'Mega Bloks'),
        ('Dora the Explorer', 'Mega Bloks'),
        ('First Builders', 'Mega Bloks'),
        ('Halo', 'Mega Bloks'),
        ('Hello Kitty', 'Mega Bloks'),
        ('Jeep', 'Mega Bloks'),
        ('John Deere', 'Mega Bloks'),
        ('Junior Builders', 'Mega Bloks'),
        ('Kapow', 'Mega Bloks'),
        ('Mega Play', 'Mega Bloks'),
        ('power rangers', 'Mega Bloks'),
        ('Ride-ons', 'Mega Bloks'),
        ('Ride ons', 'Mega Bloks'),
        ('Skylanders', 'Mega Bloks'),
        ('spongebob squarepants', 'Mega Bloks'),
        ('thomas and friends', 'Mega Bloks'),
        ('world builders', 'Mega Bloks'),
    ]

    def parse(self, response):
        # inspect_response(response, self)
        # yield Request('http://www.toysrus.com/product/index.jsp?productId=4056112&fromWidget=TRU%3ACategory%3ATop+Sellers', meta={'brand':'test'}, callback=self.parse_product)
        # yield Request('http://www.toysrus.com/product/index.jsp?productId=12713417&prodFindSrc=pn&cp=3425690', meta={'brand':'test'}, callback=self.parse_product)
        # return
        hxs = HtmlXPathSelector(response)
        for key, brand in self.keys:  # ##
            self.log('###Searching ' + key)
            yield FormRequest.from_response(response, formname='search', formdata={'kw':key}, meta={'brand':brand}, callback=self.parse_list)

    def parse_list(self, response):
        # inspect_response(response, self)
        # return
        hxs = HtmlXPathSelector(response)

        if '/product/index.jsp?' in response.url:
            # This is a product page.
            for r in self.parse_product(response):
                yield r
            return

        links = hxs.select('//div[@id="featured-category"]//div[contains(@class,"featured-cat-product")]//a[1]/@href').extract()
        if links:
            # This is a category page
            for link in links:  # ##
                url = urljoin(response.url, link)
                yield Request(url, meta=response.meta, callback=self.parse_list)
            return
        urls = hxs.select('//div[@id="tru_category_3"]/div/div/a/@href').extract()
        if urls:
            # This is 2nd kind of category page
            for url in urls:  # ##
                yield Request(url, meta=response.meta, callback=self.parse_list)
            return


        # This is a products list page.
        # Crawl products.
        for link in hxs.select('//div[contains(@class,"prodloop_row_cont")]//a[@class="prodtitle"]/@href').extract():  # ##
            url = urljoin(response.url, link)
            yield Request(url, meta=response.meta, callback=self.parse_product)
        # Crawl next page.
        #return ###
        tmp = hxs.select('//div[@class="paginationText"][1]/a[span/@class="next"]/@href').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            yield Request(url, meta=response.meta, callback=self.parse_list)

    def parse_product(self, response):
        # inspect_response(response, self)
        # return
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)

        # identifier
        if 'productId=' in response.url:
            loader.add_value('identifier', response.url.split('productId=')[1].split('&')[0])
        else:
            tmp = hxs.select('//div[@id="AddnInfo"]/p[label/text()="Manufacturer #:"]/text()').extract()
            if not tmp:
                tmp = hxs.select('//div[@id="AddnInfo"]/p[label/text()="SKU:"]/span/text()').extract()
            if tmp:
                loader.add_value('identifier', tmp[0].strip())
        # name
        tmp = hxs.select('//div[@id="lTitle"]/h1/text()').extract()
        if tmp:
            loader.add_value('name', tmp[0])
        # brand
        loader.add_value('brand', response.meta['brand'])
        # category
        tmp = hxs.select('//div[@id="breadCrumbs"]/a/text()').extract()
        if len(tmp) > 1:
            loader.add_value('category', tmp[-1])
        # sku
        tmp = hxs.select('//div[@id="AddnInfo"]/p[label/text()="Manufacturer #:"]/text()').extract() or \
            hxs.select('//div[@id="AddnInfo"]/p[@class="skuText"]/span/text()').extract()
        if tmp:
            loader.add_value('sku', tmp[0].strip())
        loader.add_value('url', response.url)
        # price
        tmp = hxs.select('//div[@id="price"]//li[contains(@class,"retail")]/span/text()').extract()
        if tmp:
            price = extract_price(tmp[0])
            loader.add_value('price', price)
            loader.add_value('stock', 1)
        # image_url
        tmp = hxs.select('//div[@id="productView"]//img/@src').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            loader.add_value('image_url', url)
        product = loader.load_item()
        # Crawl reviews
        prod_id = re.search('productId=([\d]+)', response.url).group(1)
        reviews_url = u'http://www.toysrus.com/pwr/content/%s/%s-en_US-1-reviews.js' % (self.calculate_url(prod_id), prod_id)
        metadata = LegoUSAMeta()
        metadata['reviews'] = []
        product['metadata'] = metadata
        meta = {'dont_retry': True, 'handle_httpstatus_list': [404, 302], 'cur_page': 1,
                'product': product, 'product_url': response.url, 'dont_redirect': True,
                'reviews_url': u'http://www.toysrus.com/pwr/content/' + u'%s/%s' % (self.calculate_url(prod_id), prod_id) + u'-en_US-%s-reviews.js'}
        yield Request(reviews_url, meta=meta, callback=self.parse_review)

    def parse_review(self, response):
        # inspect_response(response, self)
        # return
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

            title = review['h'] or ""
            text = review['p'] or ""

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
            loader.add_value('sku', product.get("sku", ""))
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

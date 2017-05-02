import re
import os
import csv
import time

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from keteritems import KeterMeta, Review, ReviewLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class HomeDepotSpider(BaseSpider):
    name = 'homedepot.com'
    allowed_domains = ['homedepot.com', 'homedepot.ugc.bazaarvoice.com']
    start_urls = ('http://homedepot.com',)

    def start_requests(self):
        urls = {'keter': ['http://www.homedepot.com/h_d1/N-5yc1vZ7ey/h_d2/Navigation?langId=-1&storeId=10051&catalogId=10053&c=1&7ey=7ey'],
                'rubbermaid': ['http://www.homedepot.com/h_d1/N-5yc1vZ1an/h_d2/Navigation?langId=-1&storeId=10051&catalogId=10053&c=1&1an=1an',
                              'http://www.homedepot.com/h_d1/N-5yc1vZaaj/h_d2/Navigation?langId=-1&storeId=10051&catalogId=10053&c=1&aaj=aaj'],
                'suncast': ['http://www.homedepot.com/h_d1/N-5yc1vZ4rg/h_d2/Navigation?langId=-1&storeId=10051&catalogId=10053&c=1&4rg=4rg'],
                'step-2': ['http://www.homedepot.com/h_d1/N-5yc1vZ1fb/h_d2/Navigation?langId=-1&storeId=10051&catalogId=10053&c=1&1fb=1fb'],
                'lifetime': ['http://www.homedepot.com/h_d1/N-5yc1vZ42x/h_d2/Navigation?langId=-1&storeId=10051&catalogId=10053&c=1&42x=42x'],
                'sterilite': ['http://www.homedepot.com/h_d1/N-5yc1vZ40j/h_d2/Navigation?langId=-1&storeId=10051&catalogId=10053&c=1&40j=40j']}
        for brand, urllist in urls.items():
            for url in urllist:
                yield Request(url, meta={'brand': brand}, callback=self.parse_brand)

    def parse_brand(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)

        next_page = hxs.select(u'//a[contains(@class, "paginationNumberStyle") and child::img[contains(@src, "triangle-green-right")]]/@href').extract()
        if next_page:
            next_page = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(next_page, meta=response.meta, callback=self.parse_brand)

        products = set(hxs.select(u'//div[@id="products" and @class="grid"]//a[@class="item_description"]/@href').extract())
        for url in products:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, meta=response.meta, callback=self.parse_product)

    def parse(self, response):
        pass

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)

        try:
            name = hxs.select(u'//*[@class="product_title"]/*/text()').extract()[0].strip()
        except:
            name = hxs.select(u'//*[@class="product_title"]/text()').extract()[0].strip()
        name = re.sub(u'[\r\t\n]+', u' ', name)
        prod_id = hxs.select('//*[@class="internetNo"]/text()').re(r'(\d+)')
        if not prod_id:
            prod_id = hxs.select(u'//input[@type="hidden" and @name="productId"]/@value').extract()
        if not prod_id:
            prod_id = hxs.select(u'//input[@type="hidden" and @name="certona_critemId"]/@value').extract()
        prod_id = prod_id[0].strip()

        try:
            identifier = hxs.select('//form//input[contains(@name, "productId")]/@value').extract()[0]
        except:
            identifier = prod_id

        try:
            sku = hxs.select('//*[contains(@class, "modelNo")]'
                             '/text()').re(r'#[.\t\n\r]*([\d\w]+)')[0]
        except:
            sku = u''

        try:
            image = hxs.select('//*[contains(@class, "product_containerimg")]//img/@src').extract()[0]
        except:
            image = u''



        loader = ProductLoader(item=Product(), selector=hxs)

        loader.add_value('url', response.url)
        loader.add_value('identifier', identifier)
        loader.add_value('name', name)
        loader.add_value('sku', sku)
        loader.add_value('image_url', image)

        price = hxs.select(u'//*[@id="ajaxPrice"]/text()').extract()[0].strip()

        loader.add_value('price', price)

        reviews_url = u'http://homedepot.ugc.bazaarvoice.com/1999aalite/%s/reviews.djs?format=embeddedhtml&splittestbucket=p13n-2-BucketA'
        loader.add_value('brand', response.meta['brand'].strip().lower())

        product = loader.load_item()

        metadata = KeterMeta()
        metadata['brand'] = response.meta['brand'].strip().lower()
        metadata['reviews'] = []
        product['metadata'] = metadata
        yield Request(reviews_url % prod_id, meta={'product': product, 'product_url': response.url, 'reviews_url': reviews_url % prod_id}, callback=self.parse_review)

    def parse_review(self, response):

        html = re.search('var materials={.*?(<div.*?)"},.initializers', response.body, re.DOTALL).group(1)
        html = re.sub(r'\\n', r'\n', html)
        html = re.sub(r'\\(.)', r'\1', html)

        hxs = HtmlXPathSelector(text=html)

        reviews = hxs.select(u'//div[starts-with(@id, "BVRRDisplayContentReviewID_")]')
        product = response.meta['product']

        if not reviews:
            yield product
            return

        for review in reviews:
            loader = ReviewLoader(item=Review(), selector=review, date_format=u'%d/%m/%Y')

            date = review.select(u'.//span[@class="BVRRValue BVRRReviewDate"]/text()').extract()[0]
            date = time.strptime(date, u'%B %d, %Y')
            date = time.strftime(u'%d/%m/%Y', date)

            loader.add_value('date', date)

            title = review.select(u'.//span[@class="BVRRValue BVRRReviewTitle"]/text()').extract()
            if not title:
                title = u'Untitled'
            else:
                title = title[0]
            text = review.select(u'.//span[@class="BVRRReviewText"]/text()').extract()
            if text:
                text = text[0]
            else:
                text = u'No text supplied.'
            loader.add_value('full_text', u'%s\n%s' % (title, text))
            loader.add_value('url', response.meta['product_url'])
            loader.add_xpath('rating', u'.//div[@id="BVRRRatingOverall_Review_Display"]//span[@class="BVRRNumber BVRRRatingNumber"]/text()')
            product['metadata']['reviews'].append(loader.load_item())

        cur_page = hxs.select(u'//span[@class="BVRRPageLink BVRRPageNumber BVRRSelectedPageNumber"]/text()').extract()
        if not cur_page:
            yield product
            return
        else:
            cur_page = int(cur_page[0])

        if 'last_page' not in response.meta:
            response.meta['last_page'] = int(hxs.select(u'//span[@class="BVRRPageLink BVRRPageNumber"]/a/text()').extract()[-1])

        if cur_page < response.meta['last_page']:
            url = response.meta['reviews_url'] + u'&page=%s' % str(cur_page + 1)
            yield Request(url, meta=response.meta, callback=self.parse_review)
        else:
            yield product

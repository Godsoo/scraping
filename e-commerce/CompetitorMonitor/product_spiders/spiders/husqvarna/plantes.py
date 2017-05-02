import os
import json
import csv

import re
import urlparse
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.prodcache import ProductCacheSpider
from keteritems import KeterMeta, Review, ReviewLoader
import datetime

HERE = os.path.abspath(os.path.dirname(__file__))


def normalize_space(s):
    ''' Cleans up space/newline characters '''
    return re.sub(r'\s+', ' ', s.replace(u'\xa0', ' ').strip())

class Spider(ProductCacheSpider):
    name = 'plantes-et-jardins.com'
    allowed_domains = ['plantes-et-jardins.com', 'yotpo.com']

    def start_requests(self):
        brands = {}

        with open(HERE+'/brands.csv') as f:
            reader = csv.DictReader(f)
            for row in reader:
                formatted_brand = row['brand'].lower().replace(' ','-')
                search_url = 'http://www.plantes-et-jardins.com/recherche/q/'+formatted_brand+'?sid=1836775&uid=-1&site=pj&channel=fr&sourceRefKey=ex%3Arecherche_libre'
                brands[row['brand']] = search_url

        for brand, url in brands.items():
            yield Request(url, meta={'brand': brand})


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        for productxs in response.css('div.pj-product-item'):
            ref = ''.join(productxs.css('div.pj-product-item-description ::text').extract())
            if response.meta.get('brand','').lower() not in ref.lower():
                continue
            product = Product()
            product['price'] = Decimal(productxs.xpath('.//span[@itemprop="price"]/@content').extract_first())

            request = Request(response.urljoin(productxs.css('a.gotoproduct::attr(href)').extract_first()),
                                               callback=self.parse_product, meta=response.meta)
            yield self.fetch_product(request, self.add_shipping_cost(product))

        for page in response.css('nav.pj-pagination a::attr(href)').extract():
            yield Request(urljoin_rfc(get_base_url(response), page), meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=response.meta['product'], response=response)

        loader.add_value('url', response.url)
        identifier = response.xpath('//@data-product-id').extract_first()
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_css('name', 'h1.product-title::text')
        category = response.xpath('//script/text()').re_first('category: "(.+?)>')
        loader.add_value('category', category)
        img = response.xpath('//meta[@itemprop="image"]/@src').extract_first()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img))

        loader.add_value('brand', response.meta.get('brand'))

        if response.css('div.product-add-to-cart'):
            loader.add_value('stock', '1')
        else:
            loader.add_value('stock', '0')
        product = self.add_shipping_cost(loader.load_item())


        metadata = KeterMeta()
        metadata['reviews'] = []
        product['metadata'] = metadata

        identifier = loader.get_output_value('identifier')
        
        methods = ('[{"method":"main_widget","params":{"pid":"' + identifier + '"}},' +
                  '{"method":"bottomline", "params":{"pid": '+ identifier + ','+
                  '"link":"'+hxs.select('//div/@data-url').extract()[0]+'", "skip_average_score":false,'+
                  '"main_widget_pid": ' + identifier + '}}]')

        formdata = {'app_key': hxs.select('//div/@data-appkey').extract()[0], 
                    'is_mobile': 'false', 
                    'methods': methods, 
                    'widget_version': '2015-08-30_11-33-24'}
            
        req = FormRequest("http://w2.yotpo.com/batch", formdata=formdata, callback=self.parse_review, meta={'product': product})
        yield req

    def parse_review(self, response):
        
        product = response.meta['product']

        html = json.loads(response.body)[0]['result']
        hxs = HtmlXPathSelector(text=html)

        reviews = hxs.select('//div[contains(@class, "yotpo-reviews")]/div[contains(@class, "yotpo-regular-box")]')
        for review in reviews:
            loader = ReviewLoader(item=Review(), selector=review, date_format=u'%m/%d/%Y')
            date_review = review.select('.//label[contains(@class, "yotpo-review-date")]/text()').extract()[0]
            for month, num in (
                    (u'janvier', '01'),
                    (u'f\xe9vrier', '02'),
                    (u'mars', '03'),
                    (u'avril', '04'),
                    (u'mai', '05'),
                    (u'juin', '06'),
                    (u'juillet', '07'),
                    (u'ao\xfbt', '08'),
                    (u'septembre', '09'),
                    (u'octobre', '10'),
                    (u'novembre', '11'),
                    (u'd\xe9cembre', '12')):
                date_review = date_review.replace(month, num)
            date_review = datetime.datetime.strptime(date_review, "%d/%m/%y").date()
            date_review = date_review.strftime("%m/%d/%Y")
            loader.add_value('date', date_review)

            loader.add_xpath('full_text', './/div[contains(@class, "content-title")]/text()')
            content = ''.join(review.select('.//div[contains(@class, "content-review")]/text()').extract()).strip()
            if not content:
                continue
            
            loader.add_value('full_text', content)
            loader.add_value('product_url', product['url'])
            loader.add_value('url', product['url'])
            loader.add_value('sku', product['sku'])
            loader.add_value('rating', len(review.select('.//span[@class="yotpo-review-stars"]/span').extract()))
            product['metadata']['reviews'].append(loader.load_item())

        yield product

    def add_shipping_cost(self, item):
#        item['shipping_cost'] = 4.95
        return item

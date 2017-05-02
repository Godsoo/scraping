import re
import csv
import os

import urlparse
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

class MisterGoodDealSpider(ProductCacheSpider):
    name = 'le-jardin-de-catherine.com'
    allowed_domains = ['le-jardin-de-catherine.com']

    def start_requests(self):
        brands = {}

        with open(HERE+'/brands.csv') as f:
            reader = csv.DictReader(f)
            for row in reader:
                brands[row['brand']] = 'http://www.le-jardin-de-catherine.com/catalogsearch/result/?q=%s&ok=OK' % row['brand'].lower().replace(' ','+')

        for brand, url in brands.items():
            yield Request(url, meta={'brand': brand})


    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for productxs in hxs.select('//tr[@class="item-liste-produits"]'):
            product = Product()
            product['price'] = extract_price_eu(''.join(productxs.select('.//*[starts-with(@id,"product-price-")]/text()').extract()).replace(u'\xa0', ''))
            if productxs.select('.//img[contains(@src,"1_8.png")]'):
                product['stock'] = '1'
            else:
                product['stock'] = '0'

            meta = response.meta.copy()
            meta['product'] = product
            request = Request(urljoin_rfc(get_base_url(response), productxs.select('.//h2/a/@href').extract()[0]), callback=self.parse_product, meta=meta)
            yield request
#            yield self.fetch_product(request, self.add_shipping_cost(product))

        for page in hxs.select('//div[contains(@class,"pagination")]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), page), meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=response.meta.get('product', Product()), selector=hxs)

        url = hxs.select('//form[@id="product_addtocart_form"]/@action').extract()
        identifier = [x for x in url[0].split('/') if x][-1]
        loader.add_value('url', response.url)
        loader.add_value('identifier', identifier)
        loader.add_xpath('sku', '//td[contains(text(),"Reference Produit")]/../td[2]/text()')
        loader.add_xpath('name', '//h2[contains(@class, "product-name")]/text()')
        loader.add_xpath('category', '//div[@class="fil-ariane"]/a[2]/strong/text()')
        img = hxs.select('//div[@class="bloc-img-vignettes"]//img/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('brand', response.meta.get('brand'))

        product = self.add_shipping_cost(loader.load_item())


        metadata = KeterMeta()
        metadata['reviews'] = []
        product['metadata'] = metadata

        ratings = hxs.select('//p[@class="rating-links"]//a/@href').extract()
        if not ratings or '#review-form' in ratings[0]:
            yield product
        else:
            yield Request(ratings[0], meta={'product': product}, callback=self.parse_review)

    def parse_review(self, response):
        hxs = HtmlXPathSelector(response)
        product = response.meta['product']

        for review in hxs.select('//ul[@class="liste-avis"]/li'):
            loader = ReviewLoader(item=Review(), selector=review, date_format=u'%m/%d/%Y')
            date_review = ''.join(review.select('.//a[@href="#"]/strong/text()').extract())
            date_review = datetime.datetime.strptime(date_review[:8], "%d/%m/%y").date()
            date_review = date_review.strftime("%m/%d/%Y")
            loader.add_value('date', date_review)

            loader.add_value('full_text', normalize_space(' '.join(review.select('.//text()').extract())))
            loader.add_value('product_url', product['url'])
            loader.add_value('url', product['url'])
            loader.add_value('sku', product['sku'])
            loader.add_value('rating', hxs.select('.//a[starts-with(@class, "note-produit note-produit-")]/@class').extract()[0][-1])
            product['metadata']['reviews'].append(loader.load_item())

        yield product

    def add_shipping_cost(self, item):
#        item['shipping_cost'] = 4.95
        return item

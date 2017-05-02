import re
import os
import csv
import json
import logging
from HTMLParser import HTMLParser
import time

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter, url_query_parameter
from scrapy.utils.response import get_base_url

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from keteritems import KeterMeta, Review, ReviewLoader


HERE = os.path.abspath(os.path.dirname(__file__))

class OpticsPlanetSpider(BaseSpider):
    name = 'bushnell-opticsplanet.com'
    allowed_domains = ['opticsplanet.com']
    start_urls = ('http://www.opticsplanet.com/s/bushnell?brand=8&sort=name-asc&per_page=240&_iv_gridSize=60&_iv_sort=name-asc',
                  'http://www.opticsplanet.com/leupold-spotting-scopes.html',
                  'http://www.opticsplanet.com/vortex-spotting-scopes.html',
                  'http://www.opticsplanet.com/nikonspotscopes.html',
                  'http://www.opticsplanet.com/leupold-rifle-scopes.html',
                  'http://www.opticsplanet.com/vortex-riflescopes.html',
                  'http://www.opticsplanet.com/nikon-riflescopes.html',
                  'http://www.opticsplanet.com/leupold-binoculars.html',
                  'http://www.opticsplanet.com/vortex-binoculars.html',
                  'http://www.opticsplanet.com/nikonbinoculars.html')

    bushnell_products = {}

    def start_requests(self):
        with open(os.path.join(HERE, 'bushnell_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.bushnell_products[row['SKU'].upper().strip()] = row

        for start_url in self.start_urls:
            yield Request(start_url)


    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        products = hxs.select('//div[contains(@data-plugins,"ProductGrid")]//div[contains(@class, "product")]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_product)

        if products:
            current_page = url_query_parameter(response.url, '_iv_page')
            current_page = int(current_page) if current_page else 1
            next_url = add_or_replace_parameter(response.url, '_iv_page', str(current_page + 1))
            yield Request(next_url)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select('//div[@class="item"]/h1/text()')[0].extract().strip()
        category = hxs.select('//span[@class="breadcrumbs"]/span/a/span/text()').extract()
        if category:
            category = category[-1].strip()

        image_url = hxs.select('//div[@class="gallery-image"]/img/@data-src').extract()
        if image_url:
            image_url = image_url[0]
        brand = response.xpath('//meta[@itemprop="brand manufacturer"]/@content').extract()

        products = []
        options = hxs.select('//div[@id="fancy-options-variants"]/div[@class!="e-filtration-result-empty"]')
        if options:
            for option in options:
                loader = ProductLoader(item=Product(), response=response, selector=option)
                identifier = option.select('.//@data-variant-id')[0].extract().strip()
                loader.add_value('identifier', identifier)
                loader.add_value('brand', brand)
                sku = hxs.select('.//div[@itemprop="mpn"]/span/text()').extract()
                if sku:
                    loader.add_value('sku', sku[0])
                    bushnell_product = self.bushnell_products.get(sku[0].upper().strip(), None)
                    if bushnell_product:
                        category = bushnell_product['Class']
                        log.msg('Extracts category "%s" from bushnell file, URL: %s' % (category, response.url))

                loader.add_value('url', response.url)
                loader.add_value('category', category)
                loader.add_value('image_url', image_url)
                loader.add_value('name', option.select('.//@data-variant-name')[0].extract())
                price = option.select('.//span[@class="variant-price"]/@content')[0].extract()
                loader.add_value('price', price)
                product = loader.load_item()
                metadata = KeterMeta()
                metadata['reviews'] = []
                metadata['brand'] = brand[0] if brand else ''
                product['metadata'] = metadata
                products.append(product)
        else:
            loader = ProductLoader(item=Product(), response=response, selector=hxs)
            loader.add_value('name', name)
            identifier = hxs.select('.//@data-variant-id')[0].extract().strip()
            loader.add_value('identifier', identifier)
            loader.add_value('brand', brand)
            sku = hxs.select('.//div[@itemprop="mpn"]/span/text()').extract()
            if sku:
                loader.add_value('sku', sku[0])
                bushnell_product = self.bushnell_products.get(sku[0].upper().strip(), None)
                if bushnell_product:
                    category = bushnell_product['Class']
                    log.msg('Extracts category "%s" from bushnell file, URL: %s' % (category, response.url))

            loader.add_value('url', response.url)
            loader.add_value('category', category)
            loader.add_value('image_url', image_url)
            price = hxs.select('.//span[@class="variant-price"]/@content')[0].extract()
            loader.add_value('price', price)
            product = loader.load_item()
            metadata = KeterMeta()
            metadata['brand'] = brand[0] if brand else ''
            metadata['reviews'] = []
            product['metadata'] = metadata
            products.append(product)
        if hxs.select(u'//span[@id="product-social-header-ratings-text"]/span[@id="product-social-header-review-not-rated"]'):
            for product in products:
                yield product
            return
        try:
            reviews_url = hxs.select(u'//div[@id="product-customer-reviews"]/span[@class="all-reviews"]/a/@href').extract()[0]
        except:
            reviews_url = hxs.select(u'//div[@id="product-customer-reviews"]//span[@class="all-reviews"]/a/@href').extract()[0]
        yield Request(urljoin_rfc(base_url, reviews_url), meta={'products': products, 'product_url': response.url}, callback=self.parse_review)

    def parse_review(self, response):
        hxs = HtmlXPathSelector(response)

        reviews = hxs.select(u'//div[contains(@class, "review-item")]')
        products = response.meta['products']

        if not reviews:
            for product in products:
                yield product
            return

        for review in reviews:
            loader = ReviewLoader(item=Review(), selector=review, date_format=u'%m/%d/%Y')

            review_id = review.select('@data-review-id').extract()[0]
            loader.add_value('review_id', review_id)

            date = review.select(u'.//div[@class="item-author"]//text()').re(r'Written on (.*)')[0].strip()
            date = time.strptime(date, u'%B %d, %Y')
            date = time.strftime(u'%m/%d/%Y', date)

            loader.add_value('date', date)

            title = review.select(u'./h2/a/text()').extract()
            if not title:
                title = u'Untitled'
            else:
                title = title[0]
            text = ' '.join([s.strip().replace('\n', '') for s in review.select(u'.//div[@class="item-text"]//text()').extract() if s.strip()])
            text = re.sub(' {2,}', ' ', text)
            loader.add_value('full_text', u'%s\n%s' % (title, text))
            loader.add_value('product_url', response.meta['product_url'])
            loader.add_value('url', response.url)
            product = products[0] if products else {}
            loader.add_value('sku', product.get('sku') or '')
            rating = review.select(u'./div[@class="item-rating"]/div[contains(@class, "stars")]/div/@style').re(r'width: (\d+)%;')[0]
            loader.add_value('rating', int(rating) / 20)
            products[0]['metadata']['reviews'].append(loader.load_item())
        next_page = hxs.select('//div[contains(@class, "next-button") and not(contains(@class, "disabled"))]')
        if next_page:
            identifier = hxs.select('//input[@name="identifier"]/@value').extract()[0]
            next_page = int(response.meta.get('current_page', 1)) + 1
            meta = response.meta.copy()
            meta['current_page'] = next_page
            req = FormRequest(
                response.url.split('?')[0],
                headers={'Accept': 'application/json, text/javascript, */*; q=0.01'},
                formdata={'identifier': identifier,
                          'page': str(next_page),
                          'page_size': '10',
                          'sort': 'newest'},
                callback=self.parse_review,
                meta=meta)
            yield req
        else:
            for product in products:
                yield product

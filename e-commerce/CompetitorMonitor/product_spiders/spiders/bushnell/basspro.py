import re
import csv
import os
import json
import logging
from HTMLParser import HTMLParser
import time

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from keteritems import KeterMeta, Review, ReviewLoader

from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class BassProSpider(BaseSpider):
    name = 'bushnell-basspro.com'
    allowed_domains = ['basspro.com', 'basspro.ugc.bazaarvoice.com']
    start_urls = ('http://www.basspro.com/Bushnell/_/B-4294652225?taBrand=Bushnell&taSearchTerm=bushnell',
                  'http://www.basspro.com/Brand-Vortex/Shooting-Optics-Scopes-Binoculars/_/N-1z0wp5wZ1z0ux5n',
                  'http://www.basspro.com/Brand-Leupold/Shooting-Optics-Scopes-Binoculars/_/N-1z0x72fZ1z0ux5n',
                  'http://www.basspro.com/Brand-Vortex/Shooting-Optics-Scopes-Scopes/_/N-1z0wp5wZ1z0ux5t',
                  'http://www.basspro.com/Brand-Leupold/Shooting-Optics-Scopes-Scopes/_/N-1z0x72fZ1z0ux5t',
                  'http://www.basspro.com/Brand-Nikon/Shooting-Optics-Scopes-Scopes/_/N-1z0xeceZ1z0ux5t',
                  'http://www.basspro.com/Brand-Vortex/Shooting-Optics-Scopes-Spotting-Scopes/_/N-1z0wp5wZ1z0ux5p',
                  'http://www.basspro.com/Brand-Leupold/Shooting-Optics-Scopes-Spotting-Scopes/_/N-1z0x72fZ1z0ux5p',
                  'http://www.basspro.com/Brand-Nikon/Shooting-Optics-Scopes-Spotting-Scopes/_/N-1z0xeceZ1z0ux5p')

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

        next_page = hxs.select('//a[@class="next page"]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(get_base_url(response), next_page[0]))

        products = hxs.select('//div[@class="product container"]/div[@class="info"]/p/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        name = hxs.select('//h1[@itemprop="name"]/span[not(@class)]/text()')[0].extract().strip()
        category = hxs.select('//a[contains(@class,"breadcrumb")]/text()').extract()
        if category:
            h = HTMLParser()
            category = h.unescape(category[-1])

        image_url = re.search('var imageUrl = \'(.*)\'', response.body) or []
        if image_url:
            image_url = 'https://basspro.scene7.com/is/image/BassPro/%s' % image_url.group(1).split('/')[-1]
        sku = hxs.select('//div[@id="description"]/text()').re('Manufacturer model #: (.*)\.')

        brand = hxs.select('//a[@class="breadcrumb brand name" and contains(@href,"Brand")]/text()').extract()

        if sku:
            bushnell_product = self.bushnell_products.get(sku[0].upper().strip(), None)
            if bushnell_product:
                category = bushnell_product['Class']
                log.msg('Extracts category "%s" from bushnell file, URL: %s' % (category, response.url))

        products = []
        for option in hxs.select('//table[@id="chart"]//tr[starts-with(@id,"sku_")]'):
            loader = ProductLoader(item=Product(), response=response, selector=option)
            identifier = option.select('.//span[@itemprop="sku"]/text()')[0].extract().strip()
            loader.add_value('identifier', identifier)
            loader.add_value('sku', sku)
            loader.add_value('url', response.url)
            loader.add_value('brand', brand)
            loader.add_value('category', category)
            loader.add_value('image_url', image_url)
            loader.add_value('name', '%s %s' % (name, identifier))
            price = option.select('.//span[@itemprop="price"]/text()').extract()
            if not price:
                price = option.select('.//span[@itemprop="minPrice"]/text()').extract()
            if price:
                price = price[0]
            else:
                log.msg('No price: ' + response.url)
            loader.add_value('price', price)
            product = loader.load_item()
            metadata = KeterMeta()
            metadata['reviews'] = []
            metadata['brand'] = brand[0] if brand else ''
            product['metadata'] = metadata
            products.append(product)

        if not products:
            loader = ProductLoader(item=Product(), response=response, selector=hxs)
            identifier = hxs.select('.//input[@type="hidden" and @name="productId"]/@value')[0].extract().strip()
            loader.add_value('identifier', identifier)
            loader.add_value('sku', sku)
            loader.add_value('url', response.url)
            loader.add_value('brand', brand)
            loader.add_value('category', category)
            loader.add_value('image_url', image_url)
            loader.add_value('name', '%s %s' % (name, identifier))
            price = re.search('sku_\d+\.price = \'(.*)\' ;', response.body)
            if not price:
                price = re.search('sku_\d+\.regPrice = \'(.*)\' ;', response.body)
            price = price.group(1) if price else ''
            loader.add_value('price', price)
            product = loader.load_item()
            metadata = KeterMeta()
            metadata['reviews'] = []
            metadata['brand'] = brand[0] if brand else ''
            product['metadata'] = metadata
            products.append(product)
        reviews_url = u'http://basspro.ugc.bazaarvoice.com/2010category/%s/reviews.djs?format=embeddedhtml'
        prod_id = response.url.split('/')[-2]
        yield Request(reviews_url % prod_id, meta={'products': products, 'product_url': response.url, 'reviews_url': reviews_url % prod_id}, callback=self.parse_review)

    def parse_review(self, response):

        html = re.search('var materials={.*?(<div.*?)"},.initializers', response.body, re.DOTALL).group(1)
        html = re.sub(r'\\n', r'\n', html)
        html = re.sub(r'\\(.)', r'\1', html)

        hxs = HtmlXPathSelector(text=html)

        reviews = hxs.select(u'//div[starts-with(@id, "BVRRDisplayContentReviewID_")]')
        products = response.meta['products']
        if not reviews:
            for product in products:
                yield product
            return

        for review in reviews:
            loader = ReviewLoader(item=Review(), selector=review, date_format=u'%m/%d/%Y')

            review_id = review.select("@id").re(r'BVRRDisplayContentReviewID_(\d+)')[0]
            loader.add_value('review_id', review_id)

            date = review.select(u'.//span[contains(@class, "BVRRValue BVRRReviewDate")]/text()').extract()[0]
            date = time.strptime(date, u'%B %d, %Y')
            date = time.strftime(u'%m/%d/%Y', date)

            loader.add_value('date', date)

            title = review.select(u'.//span[@class="BVRRValue BVRRReviewTitle summary"]/text()').extract()
            if not title:
                title = u'Untitled'
            else:
                title = title[0]
            pros_cons_text = u' '.join(reviews[0].select(u'.//div[@class="BVRRReviewProsConsContainer"]//text()').extract())
            text = review.select(u'.//span[@class="BVRRReviewText"]/text()').extract()
            if text:
                text = text[0]
            else:
                text = u'No text supplied.'
            extra_information = u' '.join(review.select(u'.//div[@class="BVRRContextDataContainer"]//text()').extract())
            text = '%s\n%s\n%s' % (pros_cons_text, text, extra_information)
            loader.add_value('full_text', u'%s\n%s' % (title, text))
            loader.add_value('product_url', response.meta['product_url'])
            loader.add_value('url', response.meta['product_url'])
            product = products[0] if products else {}
            loader.add_value('sku', product.get('sku') or '')
            loader.add_xpath('rating', u'.//div[@id="BVRRRatingOverall_Review_Display"]//span[@itemprop="ratingValue"]/text()')
            products[0]['metadata']['reviews'].append(loader.load_item())

        cur_page = hxs.select(u'//span[@class="BVRRPageLink BVRRPageNumber BVRRSelectedPageNumber"]/text()').extract()
        if not cur_page:
            for product in products:
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
            for product in products:
                yield product

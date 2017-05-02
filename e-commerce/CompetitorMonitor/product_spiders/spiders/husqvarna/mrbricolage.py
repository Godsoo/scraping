import os
import csv

import json
import re
import time
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from keteritems import KeterMeta, Review, ReviewLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class MrBricolageSpider(BaseSpider):
    name = 'husqvarna-mr-bricolage.fr'
    allowed_domains = ['mr-bricolage.fr']
    start_urls = []
    COOKIES_ENABLED = True
    start_urls=['http://www.mr-bricolage.fr/']

    def start_requests(self):
        brands = {'Gardena': 'http://www.mr-bricolage.fr/search/?direction=asc&orderby=price&p=1&q=gardena',
                  'Flymo': 'http://www.mr-bricolage.fr/search/?direction=asc&orderby=price&p=1&q=flymo',
                  'Mc Culloch': 'http://www.mr-bricolage.fr/search/?direction=asc&orderby=price&p=1&q=mc+culloch'}

        search_url = 'http://www.mr-bricolage.fr/search/?direction=asc&orderby=price&p=1&q=%s'

        brands = {}

        with open(HERE+'/brands.csv') as f:
            reader = csv.DictReader(f)
            for row in reader:
                formatted_brand = row['brand'].lower().replace(' ','+')
                brands[row['brand']] = search_url % (formatted_brand)

        for brand, url in brands.items():
            yield Request(url, meta={'brand': brand})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        next_page = hxs.select('//a[@class="next i-next"]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]), meta=response.meta)

        products = hxs.select('//div[@class="content-product"]/a[@class="nom"]/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        base_url = get_base_url(response)

        product_id = hxs.select('//td[@itemprop="sku"]/@content')[0].extract()

        product_loader = ProductLoader(item=Product(), selector=hxs)

        name = hxs.select('//div[@id="titre"]/h1/text()').extract()
        product_loader.add_value('name', u'{}'.format(name[0].strip()))

        product_loader.add_value('url', response.url)

        product_loader.add_value('brand', response.meta.get('brand') or '')

        product_loader.add_value('identifier', product_id)
        product_loader.add_value('sku', product_id)

        image_url = hxs.select('//img[@id="visuelprincipal"]/@src').extract()
        if image_url:
            image_url = urljoin_rfc(base_url, image_url[0])
            product_loader.add_value('image_url', image_url)

        price = hxs.select('//div[@class="bloc-price-fiche"]/p/span[@class="price"]/text()').extract()
        if not price:
            price = ''.join(hxs.select('//div[@class="bloc-price-fiche"]/span[@class="price"]//text()').extract())
        else:
            price = price[0]
        product_loader.add_value('price', price.replace(',', '.') if price else '0.00')

        in_stock = hxs.select('//div[@class="postitdelais"]/span[contains(@class,"postitfond-dom1") or contains(@class,"postitfond-2h")]').extract()
        if not in_stock:
            product_loader.add_value('stock', 0)

        product =  product_loader.load_item()
        metadata = KeterMeta()
        metadata['reviews'] = []
        metadata['brand'] = response.meta.get('brand') or ''
        product['metadata'] = metadata
        response.meta['product'] = product

        shipping_cost = hxs.select('//button/@onclick').re('ajoutPanier\(\'(.*)\'\)')

        for product in self.parse_review(response):
            if shipping_cost:
                p_id = re.search('product/(.*?)/', shipping_cost[0]).group(1)
                yield Request(urljoin_rfc(base_url, shipping_cost[0]),
                              callback=self.parse_shipping_cost_url,
                              meta={'product': product.copy(), 'cookiejar': p_id},
                              errback=lambda failure, product=product: self.parse_error(failure, product), dont_filter=True)
            else:
                yield product

    def parse_review(self, response):
        hxs = HtmlXPathSelector(response)

        reviews = hxs.select('//div[@id="bvseo-reviewsSection"]/div[@itemprop="review"]')
        product = response.meta['product']

        if not reviews:
            yield product
            return

        for review in reviews:
            loader = ReviewLoader(item=Review(), selector=review, date_format=u'%m/%d/%Y')

            date = review.select('./meta[@itemprop="datePublished"]/@content').extract()[0]

            date = time.strptime(date, u'%Y-%m-%d')
            date = time.strftime(u'%m/%d/%Y', date)

            loader.add_value('date', date)

            title = ''.join(review.select('./span[@itemprop="name"]/text()').extract())
            if not title:
                title = u'Untitled'
            text = ''.join(review.select('./span[@itemprop="description"]/text()').extract()).strip()
            if not text:
                text = u'No text supplied.'
            loader.add_value('full_text', u'%s\n%s' % (title, text))
            loader.add_value('product_url', product['url'])
            loader.add_value('url', product['url'])
            loader.add_value('sku', product.get('sku') or '')
            rating = review.select('.//span[@itemprop="ratingValue"]/text()').extract()[0]
            loader.add_value('rating', rating)
            product['metadata']['reviews'].append(loader.load_item())

        yield product

    def parse_shipping_cost_url(self, response):
        try:
            url = json.loads(response.body)
        except:
            url = {'error': True}
        if url.get('error') == 0 or url.get('error') == '0' or not url.get('error'):
            url = url['url']
            yield Request(url, callback=self.parse_shipping_cost,
                          errback=lambda failure, product=response.meta.get('product'): self.parse_error(failure, product),
                          meta=response.meta)
        else:
            yield response.meta.get('product')

    def parse_shipping_cost(self, response):
        product = response.meta.get('product')
        hxs = HtmlXPathSelector(response)

        shipping_cost = hxs.select('//span[@class="popin-prix-livraison-valeur "]/span[@class="price"]/text()').re('([\d,\. ]+)')
        if shipping_cost:
            shipping_cost = Decimal(shipping_cost[0].replace(' ', '').replace('.', '').replace(',', '.'))
            product['shipping_cost'] = shipping_cost
        yield product

    def parse_error(self, failure, product):
        yield product

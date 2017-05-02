import csv
import os
import re
import time

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from keteritems import KeterMeta, Review, ReviewLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class LeroyMerlinSpider(BaseSpider):
    name = 'husqvarna-leroymerlin.fr'
    allowed_domains = ['leroymerlin.fr']
    start_urls = []

    def start_requests(self):
        brands = {'Gardena': 'http://www.leroymerlin.fr/recherche=gardena?pageTemplate=Recherche&resultOffset=0&resultLimit=100&resultListShape=SEARCHENGINE_PRODUCT_LIST_PLAIN&facet=PRODUCT&keyword=gardena&sort=TRI_PAR_PRIX_CROISSANT_ID',
                  'Flymo': 'http://www.leroymerlin.fr/recherche=flymo?pageTemplate=Recherche&resultOffset=0&resultLimit=100&resultListShape=SEARCHENGINE_PRODUCT_LIST_PLAIN&facet=PRODUCT&keyword=flymo&sort=TRI_PAR_PRIX_CROISSANT_ID',
                  'Mc Culloch': 'http://www.leroymerlin.fr/recherche=mc+culloch?pageTemplate=Recherche&resultOffset=0&resultLimit=100&resultListShape=SEARCHENGINE_PRODUCT_LIST_PLAIN&facet=PRODUCT&keyword=mc+culloch&sort=TRI_PAR_PRIX_CROISSANT_ID'}


        search_url = 'http://www.leroymerlin.fr/recherche=%s?pageTemplate=Recherche&resultOffset=0&resultLimit=100&resultListShape=SEARCHENGINE_PRODUCT_LIST_PLAIN&facet=PRODUCT&keyword=%s&sort=TRI_PAR_PRIX_CROISSANT_ID'

        brands = {}

        with open(HERE+'/brands.csv') as f:
            reader = csv.DictReader(f)
            for row in reader:
                formatted_brand = row['brand'].lower().replace(' ','+')
                brands[row['brand']] = search_url % (formatted_brand, formatted_brand)

        for brand, url in brands.items():
            yield Request(url, meta={'brand': brand})

    def _get_shipping_cost(self, weight):
        weight = float(weight)
        weights = (5, 15, 30, 40, 50, 60)
        costs = (5.95, 8.95, 15.95, 29.95, 39.95, 49.95)
        i = 0
        while i < len(weights) and weight > weights[i]:
            i += 1
        res = costs[i] if i < len(weights) else 59.95
        return str(res)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        next_page = hxs.select('//ul[@class="pagination"]/li/a[i[@class="ico-arrow-right"]]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]), meta=response.meta)

        products = hxs.select('//a[@itemprop="name"]/@href').extract()
        if not products:
            products = hxs.select('//a/span[@itemprop="name"]/../@href').extract()
        if not products:
            # Just in case layout changes once again..
            self.log('No URL found on product item at [%s]' % (response.url))
            for product in self.parse_product(response):
                yield product
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        base_url = get_base_url(response)

        product_id = hxs.select('//aside/span/span/text()')[0].extract()

        product_loader = ProductLoader(item=Product(), selector=hxs)

        name = hxs.select('//article/header/h1/text()').extract()
        product_loader.add_value('name', u'{}'.format(name[0].strip()))

        product_loader.add_value('url', response.url)

        product_loader.add_value('brand', response.meta.get('brand') or '')

        product_loader.add_value('identifier', '{}'.format(product_id))
        product_loader.add_value('sku', product_id)

        try:
            category = hxs.select('//ul[@class="breadcrumb"]//a/i/text()')[-1].extract()
        except:
            category = hxs.select('//ul[@class="breadcrumb"]//a/text()')[-1].extract()
        product_loader.add_value('category', category)

        image_url = hxs.select('//img[@id="img-01"]/@data-zoom-image').extract()
        if image_url:
            image_url = urljoin_rfc(base_url, image_url[0])
            product_loader.add_value('image_url', image_url)

        price = hxs.select('//aside[contains(@class, "price-container")]/div/p[@class="price"]//text()').extract()
        product_loader.add_value('price', extract_price(price[0]) if price else '0.00')

        if not hxs.select('//div[@class="infos-checkout"]/a[contains(@class,"cta green")]'):
            product_loader.add_value('stock', 0)

        weight = hxs.select('//section[@id="description-technique"]//th[@scope="row" and contains(text(),"Poids")]/following-sibling::td/text()').extract()
        if weight:
            product_loader.add_value('shipping_cost', self._get_shipping_cost(weight[-1]))

        product = product_loader.load_item()
        metadata = KeterMeta()
        metadata['reviews'] = []
        metadata['brand'] = response.meta.get('brand') or ''
        product['metadata'] = metadata

        reviews_url = 'http://www.leroymerlin.fr/v3/bazaarvoice/viewReviews.do?reflm={}&page={}&maxItems=4'
        yield Request(reviews_url.format(product_id, '1'),
                      meta={'product': product,
                            'page': 1,
                            'product_url': response.url,
                            'product_id': product_id,
                            'reviews_url': reviews_url},
                      callback=self.parse_review,
                      dont_filter=True)

    def parse_review(self, response):

        hxs = HtmlXPathSelector(response)

        reviews = hxs.select(u'//div[@class="rating-box"]')
        product = response.meta['product']

        if not reviews:
            yield product
            return

        months = enumerate(u'janvier, f\xe9vrier, mars, avril, mai, juin, juillet, ao\xfbt, septembre, octobre, novembre, d\xe9cembre'.split(', '), 1)
        months = dict(((y, x) for x, y in months))
        for review in reviews:
            loader = ReviewLoader(item=Review(), selector=review, date_format=u'%m/%d/%Y')

            date = review.select(u'.//footer/p/text()').extract()[0]

            for month, number in months.items():
                if month in date:
                    date = date.replace(month, str(number)).replace(' - ', '')
                    break
            date = time.strptime(date, u'%d %m %Y')
            date = time.strftime(u'%m/%d/%Y', date)

            loader.add_value('date', date)

            title = review.select(u'.//article/header/h3/text()').extract()
            if not title:
                title = u'Untitled'
            else:
                title = title[0]
            text = ''
            ratings = review.select('.//div[@class="infos-note"]/p')
            for rating in ratings:
                text += u'{} {}\n'.format(*rating.select('.//text()[normalize-space()]').extract())
            lines = review.select('.//article//p//text()[normalize-space()]').extract()
            for line in lines:
                text += u'{}\n'.format(line.strip())
            if not text:
                text = u'No text supplied.'
            loader.add_value('full_text', u'%s\n%s' % (title, text))
            loader.add_value('product_url', response.meta['product_url'])
            loader.add_value('url', response.meta['product_url'])
            loader.add_value('sku', product.get('sku') or '')
            loader.add_xpath('rating', u'.//span[@itemprop="ratingValue"]/text()')
            product['metadata']['reviews'].append(loader.load_item())

        reviews_url = response.meta.get('reviews_url')
        meta = response.meta
        meta['page'] += 1
        yield Request(reviews_url.format(response.meta.get('product_id'), str(response.meta.get('page') + 1)),
                      meta=meta,
                      callback=self.parse_review,
                      dont_filter=True)

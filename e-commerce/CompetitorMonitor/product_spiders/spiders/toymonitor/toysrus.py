import os
import re
import csv
import demjson
import datetime
from urlparse import urljoin

from scrapy.http import Request, HtmlResponse
from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from product_spiders.base_spiders.primary_spider import PrimarySpider
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from toymonitoritems import ToyMonitorMeta, Review, ReviewLoader
from brands import BrandSelector

HERE = os.path.abspath(os.path.dirname(__file__))


class ToysRUsSpider(PrimarySpider):

    name = 'toymonitor-toysrus.co.uk'
    allowed_domains = ['toysrus.co.uk']
    start_urls = ('http://www.toysrus.co.uk/brandDirectory.jsf',)
    products_filename = 'brandstomonitor.txt'
    categories_filename = os.path.join(HERE, 'toysrus_categories.txt')

    csv_file = 'toymonitor_toysrus_crawl.csv'
    errors = []
    brand_selector = BrandSelector(errors)
    #field_modifiers = {'brand': brand_selector.get_brand}

    def start_requests(self):
        with open(self.categories_filename) as f:
            category_urls = csv.reader(f)
            for row in category_urls:
                yield Request(row[1], meta={'category': row[0]})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        next_page = hxs.select('//img[@alt="Next page"]/../@href').extract()
        if next_page:
            next_page = urljoin(response.url, next_page[0])
            yield Request(next_page, meta=response.meta)

        products = set(hxs.select(u'//ul[@class="table result-list"]//div[@class="label"]/a/@href').extract())
        for url in products:
            url = urljoin(response.url, url)
            yield Request(url, meta=response.meta, callback=self.parse_product)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        name = hxs.select('//div[@class="product-title"]/h1/text()').extract()
        if not name:
            self.log('ERROR: no product NAME found! URL:{}'.format(response.url))
        else:
            loader.add_value('name', name[0].strip())

        prod_id = hxs.select('//input[@id="productId"]/@value').extract()[0]
        loader.add_value('identifier', prod_id)

        loader.add_value('url', response.url)
        price = hxs.select('//div[@class="price clearfix"]/div[@class="floatleft block"]/span/text()').extract()
        if not price:
            price = hxs.select('//script[contains(text(), "product_base_price")]').re('product_base_price:\["(.*)"\]')
            if not price:
                self.log('ERROR: no product PRICE found! URL:{}'.format(response.url))
                return
        if price:
            loader.add_value('price', price[0])
        product_image = hxs.select('//a[@id="mainImage"]/img/@src').extract()
        if not product_image:
            self.log('ERROR: no product Image found!')
        else:
            image = urljoin_rfc(get_base_url(response), product_image[0].strip())
            loader.add_value('image_url', image)

        loader.add_value('category', response.meta.get('category', ''))

        sku = hxs.select('//input[@name="skuId"]/@value').extract()
        if not sku:
            self.log('ERROR: no SKU found! URL:{}'.format(response.url))
        else:
            loader.add_value('sku', sku[0].strip())

        brand = re.search('product_brand:\[\"(.*)\"\],', response.body)
        if brand:
            loader.add_value('brand', brand.group(1).strip())

        promo = response.xpath('//div[contains(@class,"pdp_add-cart")]/div[@class="truuk-offer-box"]'
                               '//span[@class="truuk-special-offer-body"]/text()').extract()
        if not promo:
            promo = response.xpath('//div[contains(@class,"pdp_add-cart")]//span[@class="was-2 block"]/text()').extract()

        product = loader.load_item()

        reviews_url = u'http://www.toysrus.co.uk/assets/pwr/content/%s/%s-en_GB-1-reviews.js' % (self.calculate_url(prod_id), prod_id)
        metadata = ToyMonitorMeta()
        metadata['reviews'] = []
        if promo:
            metadata['promotions'] = promo[0]
        product['metadata'] = metadata
        meta = {'dont_retry': True, 
                'handle_httpstatus_list': [404, 302], 'cur_page': 1,
                'product': product, 
                'dont_redirect': True,
                'reviews_url': u'http://www.toysrus.co.uk/assets/pwr/content/' + u'%s/%s' % (self.calculate_url(prod_id), prod_id) + u'-en_GB-%s-reviews.js'}
        yield Request(reviews_url, meta=meta, callback=self.parse_review)


    def parse_review(self, response):
        meta = response.meta
        product = meta['product']

        reviews = re.search(u'= (.*);$', response.body, re.DOTALL)
        try:
            reviews = reviews.group(1)
            reviews = map(lambda x: x.get('r'), demjson.decode(reviews))
        except:
            reviews = None

        if response.status != 200 or not reviews:
            yield product
            return

        for review in reviews:
            review_loader = ReviewLoader(item=Review(), selector=review, date_format="%B %d, %Y")
            try:
                review_date = datetime.datetime.strptime(review.get('d'), "%m/%d/%Y").date()
                review_datew = review_date.strftime("%m/%d/%Y")
            except:
                review_date = review.get('d')

            review_loader.add_value('date', review_date.strftime("%B %d, %Y"))

            title = review['h']
            text = review['p']

            review_data = {}
            if review.has_key('g'):
                for data in review['g']:
                    review_data[data['n']] = u', '.join(map(unicode, data['v']))
            fields = [u'Pros', u'Cons', u'Best Uses']
            text += u' \n '
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

            review_loader.add_value('full_text', u'%s \n %s' % (title, text))
            review_loader.add_value('url', product['url'])
            review_loader.add_value('rating', review['r'])
            product['metadata']['reviews'].append(review_loader.load_item())

        cur_page = meta['cur_page']

        url = meta['reviews_url'] % str(cur_page + 1)
        meta['cur_page'] += 1
        yield Request(url, meta=meta, callback=self.parse_review)

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

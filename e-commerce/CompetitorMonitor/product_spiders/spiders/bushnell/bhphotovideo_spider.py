import csv
import re
import time
import os
import shutil
import StringIO
from datetime import datetime
import demjson
import json

from decimal import Decimal

from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.url import canonicalize_url
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product
from keteritems import KeterMeta, Review, ReviewLoader
from axemusic_item import ProductLoader

from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))


class BHPhotoVideoSpider(BaseSpider):
    name = 'bushnell-bhphotovideo.com'
    allowed_domains = ['bhphotovideo.com']
    start_urls = ('http://www.bhphotovideo.com/c/search?phd=4291573991&Ns=p_PRICE_2%7c0&ci=4&N=4294255798&srtclk=sort',
                  'http://www.bhphotovideo.com/c/search?ipp=100&Ns=p_PRICE_2|0&ci=1010&N=4083534123+4291369190+4291315846+4291123588&setIPP=100&srtclk=itemspp',
                  'http://www.bhphotovideo.com/c/search?Ns=p_PRICE_2|0&ci=13525&setNs=p_PRICE_2|0&N=4100994457+4291369190+4291123588&srtclk=sort',
                  'http://www.bhphotovideo.com/c/search?Ns=p_PRICE_2|0&ci=1032&setNs=p_PRICE_2|0&N=4083534116+4291369190+4291315846+4291123588&srtclk=sort')

    urls_list = []
    bushnell_products = {}

    def start_requests(self):
        with open(os.path.join(HERE, 'bushnell_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.bushnell_products[row['SKU'].upper().strip()] = row

        for start_url in self.start_urls:
            yield Request(start_url)

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        meta = response.meta.copy()

        cats = hxs.select(
                '//*[@id="tContent"]/div/div/div[@class="column"]'
                '/ul/li/a/@href').extract()

        pages = hxs.select('//div[contains(@class, "pagination-zone")]//a/@href').extract()
        for page_url in pages:
            yield Request(
                    callback=self.parse,
                    url=canonicalize_url(page_url),
                    errback=lambda failure, url=canonicalize_url(page_url), metadata=meta: self.retry_download(failure, url, metadata, self.parse))

        products = hxs.select(
                '//div[contains(@class, "item") and contains(@class, "clearfix")]')
        if products:
            for product in products:
                try:
                    brand = product.select('.//span[@itemprop="brand"]/text()').extract()[0]
                except IndexError:
                    brand = ''
                title = product.select('.//span[@itemprop="name"]/text()').extract()[0]
                name = ' '.join((brand, title))

                url = product.select('.//a[@itemprop="url"]/@href').extract()[0]

                identifier = product.select('.//input[@name="sku"]/@value').extract().pop()

                price = 0
                for data in hxs.select('//div/@data-itemdata').extract():
                    json_data = json.loads(data)
                    if json_data['sku'] == identifier:
                        price = json_data['price']
                        break

                if not price:
                    price = product.select('.//div[@class="price-zone"]/div[@class="atc-price"]'
                                        '//strong[contains(@class, "price")]/text()').extract()

                try:
                    sku = product.select('.//p[contains(@data-selenium, "skus")]//span[@class="sku"]/text()').extract()[-1]
                except:
                    sku = ''
                image_url = product.select('.//a[@class="itemImg"]/img/@data-src').extract() or product.select('.//a[@class="itemImg"]/img/@src').extract()
                if image_url:
                    image_url = urljoin_rfc(base_url, image_url[0])
                else:
                    image_url = ''

                category = hxs.select('//ul[@id="breadcrumbs"]/li/a/text()').extract()[-1].strip()
                if category.lower() == "home":
                    category = hxs.select('//ul[@id="breadcrumbs"]/li[@class="last"]/text()').extract()[-1].strip()

                bushnell_product = self.bushnell_products.get(sku.upper().strip(), None)
                if bushnell_product:
                    category = bushnell_product['Class']
                    log.msg('Extracts category "%s" from bushnell file, URL: %s' % (category, response.url))

                if url not in self.urls_list:
                    if price:
                        self.urls_list.append(url)
                        loader = ProductLoader(item=Product(), selector=product)
                        loader.add_value('url', url)
                        loader.add_value('identifier', identifier)
                        loader.add_value('sku', sku)
                        loader.add_value('image_url', image_url)
                        loader.add_value('brand', brand)
                        loader.add_value('category', category)
                        loader.add_value('name', name)
                        loader.add_value('price', price)
                        product = loader.load_item()
                        yield self._get_reviews_url(product)
                    else:
                        # parse product page if price not found
                        meta = {'name': name,
                                'brand': brand,
                                'category': category,
                                'identifier': identifier,
                                'image_url': image_url,
                                'sku': sku}
                        yield Request(
                            url=url,
                            callback=self.parse_product,
                            meta=meta,
                            errback=lambda failure, url=url, metadata=meta: self.retry_download(failure, url, metadata, self.parse_product))
        elif not cats:
            retry = response.meta.get('try', 0)
            if retry < 15:
                meta = response.meta.copy()
                meta['try'] = retry + 1
                yield Request(
                        url=response.url,
                        dont_filter=True,
                        callback=self.parse,
                        errback=lambda failure, url=response.url, metadata=meta: self.retry_download(failure, url, metadata, self.parse))

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        meta = response.meta
        url = response.url
        price = ''
        for line in hxs.extract().split('\n'):
            if "MAIN:No^Refrnce" in line:
                price = line.split('");')[0].split(', "')[-1]

        if not price:
            try:
                price = hxs.select('//span[@itemprop="price"]/text()').extract()[0].replace(',', '')
            except:
                pass

        identifier = meta.get('identifier')
        if not identifier:
            identifier = hxs.select('//form[@name="addItemToCart"]//input[@name="sku"]/@value').extract()[0]
        image_url = meta.get('image_url')
        if not image_url:
            image_url = hxs.select('//img[@id="mainImage"]/@src').extract()
        brand = meta.get('brand')
        if not brand:
            brand = hxs.select('//div[@id="tMain"]//div[@class="mfrLogo"]//img[1]/@alt').extract()
        category = meta.get('category')
        if not category:
            try:
                category = hxs.select('//ul[@id="breadcrumbs"]/li/a/text()').extract()[-1].strip()
            except:
                pass
        sku = meta.get('sku')
        if not sku:
            sku = hxs.select('//meta[@itemprop="productID" and contains(@content, "mpn:")]/@content').re(r'mpn:(\w+)')
            if sku:
                bushnell_product = self.bushnell_products.get(sku[0].upper().strip(), None)
                if bushnell_product:
                    category = bushnell_product['Class']
                    log.msg('Extracts category "%s" from bushnell file, URL: %s' % (category, response.url))

        name = meta.get('name')
        if not name:
            name = ''.join(hxs.select('//h1[@itemprop="name"]//text()').extract()).strip()

        if url not in self.urls_list:
            self.urls_list.append(url)
            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('identifier', identifier)
            loader.add_value('image_url', image_url)
            loader.add_value('brand', brand)
            loader.add_value('category', category)
            loader.add_value('url', url)
            loader.add_value('sku', sku)
            loader.add_value('name', name)
            loader.add_value('price', price)
            product = loader.load_item()
            yield self._get_reviews_url(product)

    def retry_download(self, failure, url, metadata, callback):
        no_try = metadata.get('retry', 1)
        self.log("Try %d. Retrying to download %s" %
                 (no_try, url))
        if no_try < 15:
            metadata['retry'] = no_try + 1
            metadata['recache'] = True
            time.sleep(60)
            return Request(url,
                           callback=callback,
                           meta=metadata,
                           dont_filter=True,
                           errback=lambda failure, url=url, metadata=metadata: self.retry_download(failure, url, metadata, callback)
                           )

    def parse_review(self, response):

        reviews = re.search(u'= (.*);$', response.body, re.DOTALL)

        product = response.meta['product']

        if response.status != 200 or not reviews:
            yield product
            return

        reviews = reviews.group(1)
        reviews = map(lambda x: x.get('r'), demjson.decode(reviews))

        for review in reviews:
            loader = ReviewLoader(item=Review(), selector=review, date_format=u'%m/%d/%Y')

            loader.add_value('review_id', review['id'])

            date_review = datetime.strptime(review.get('d'), "%m/%d/%Y").date()
            date_review = date_review.strftime("%m/%d/%Y")

            loader.add_value('date', date_review)

            title = review['h']
            text = review['p']

            review_data = {}
            if review.get('g'):
                for data in review['g']:
                    review_data[data['n']] = u', '.join(map(str, data['v']))
            fields = [u'Pros', u'Cons', u'Best Uses']
            text += u'\n'
            for field in fields:
                if review_data.get(field):
                    text += u'%s:\n%s\n' % (field, review_data.get(field))
            if review.get('b'):
                if review['b']['k'] == 'Yes':
                    text += u'Yes, I would recommend this to a friend.'
                else:
                    text += u'No, I would not recommend this to a friend.'

            loader.add_value('full_text', u'%s\n%s' % (title, text))
            loader.add_value('product_url', response.meta['product_url'])
            loader.add_value('url', response.meta['product_url'])
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
        return cg[0:ci / 2] + '/' + cg[ci / 2:ci]

    def _get_reviews_url(self, product):
        identifier = product['identifier']
        reviews_url = u'http://www.bhphotovideo.com/pwr/content/%s/%s-en_US-1-reviews.js' % (self.calculate_url(identifier), identifier)
        metadata = KeterMeta()
        metadata['reviews'] = []
        metadata['brand'] = product.get('brand', '')
        product['metadata'] = metadata
        meta = {'dont_retry': True, 'handle_httpstatus_list': [404], 'cur_page': 1, 'product': product, 'product_url': product['url'], 'reviews_url': u'http://www.bhphotovideo.com/' + u'%s/%s' % (self.calculate_url(identifier), identifier) +
                                                                                         u'-en_US-%s-reviews.js'}
        return Request(reviews_url, meta=meta, callback=self.parse_review)

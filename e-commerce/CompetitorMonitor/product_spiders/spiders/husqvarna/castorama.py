import re
import os
import csv
import time

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from keteritems import KeterMeta, Review, ReviewLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class CastoramaSpider(BaseSpider):
    name = 'husqvarna-castorama.fr'
    allowed_domains = ['castorama.fr']
    start_urls = []

    def retry(self, response, retries=3):
        meta = response.meta.copy()
        retry = int(meta.get('retry', 0))
        if 'redirect_urls' in meta and meta['redirect_urls']:
            url = meta['redirect_urls']
        else:
            url = response.request.url
        if retry < retries:
            retry = retry + 1
            meta['retry'] = retry
            meta['recache'] = True
            return Request(url, dont_filter=True, meta=meta, callback=response.request.callback)

    def start_requests(self):
        brands = {}

        with open(HERE+'/brands.csv') as f:
            reader = csv.DictReader(f)
            for row in reader:
                brands[row['brand']] = 'http://www.castorama.fr/store/rechercher/%s?isBrand=true&osearchmode=tagcloud' % row['brand'].upper().replace(' & ', '--')

        for brand, url in brands.items():
            yield Request(url, meta={'brand': brand})

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
                    return
        hxs = HtmlXPathSelector(response)

        # pagination
        next_page = hxs.select(u'//div[@class="suivantDivProds"]/a[@class="suivant"]/@href').extract()
        if next_page:
            next_page = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(next_page, meta=response.meta)

        # products
        for product in self.parse_product(response):
            yield product

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        products = hxs.select(u'//table[@class="productsTable grayTable"]//tr')
        for product in products:
            product_loader = ProductLoader(item=Product(), selector=product)
            url = product.select(u'.//div[@class="productItemDescription"]/a/@href').extract()
            if not url:
                continue
            url = urljoin_rfc(get_base_url(response), url[0])
            product_loader.add_value('url', (url.split(';')[0]).split('?')[0])
            product_loader.add_value('brand', response.meta.get('brand') or '')
            product_loader.add_xpath('name', u'.//div[@class="productItemDescription"]/a/text()')
            identifier = product.select(u'.//input[@name="/com/castorama/CastShoppingCartFormHandler.productId"]/@value').extract()
            if not identifier:
                identifier = product.select('.//div[@class="productItemImage"]//img/@productid').extract()
            if (identifier and not identifier[0].strip()) or not identifier:
                identifier = re.search(r'-([\w]*)\.html', url).groups()
            product_loader.add_value('identifier', identifier[0])
            product_loader.add_value('image_url',
                                         urljoin_rfc(get_base_url(response),
                                                     product\
                                                     .select('.//div[@class="productItemImage"]//img/@src').extract()[0]
                                                     ))
            price = product.select(u'.//div[@class="priceContent"]/span[@class="newprice"]/text()').re(u'([0-9\,\.\xa0\ ]+)')
            if not price:
                price = product.select(u'.//div[@class="priceContent"]/div[@class="price"]/text()').re(u'([0-9\,\.\xa0\ ]+)')
            if price:
                price = price[0].replace(u',', u'.').replace(' ', '').replace(u'\xa0', u'')
                product_loader.add_value('price', price)
            product = product_loader.load_item()
            meta = response.meta
            meta['product'] = product
            yield Request(product['url'], callback=self.parse_sku, meta=meta)

        if not products:
            log.msg('Retrying url: %s' % response.url, level=log.WARNING)
            retries = response.meta.get('retries', 0)
            if retries < 3:
                meta = response.meta
                meta['retries'] = retries + 1
                yield Request(response.url, dont_filter=True, meta=meta)

    def parse_sku(self, response):
        hxs = HtmlXPathSelector(response)
        product_loader = ProductLoader(item=response.meta.get('product'), selector=hxs)
        stock = hxs.select('//div[@class="rightColumn rightColumnV2 productDetailsRightColumn"]//input[@name="/com/castorama/CastShoppingCartFormHandler.addItemToOrder"]').extract()
        sku = hxs.select('//div[@class="productDecription"]/span[@class="refNum"]/text()').re(u':[\xa0]?(.*)')
        product_loader.add_value('sku', sku[0] if sku else '')
        if not stock:
            product_loader.add_value('stock', 0)
        reviews_url = hxs.select('//script/text()').re('bvPage = \'(.*)\';')
        product = product_loader.load_item()
        meta = response.meta
        meta['product'] = product
        metadata = KeterMeta()
        metadata['reviews'] = []
        metadata['brand'] = response.meta.get('brand') or ''
        product['metadata'] = metadata
        if reviews_url:
            yield Request(reviews_url.pop(), meta=meta, callback=self.parse_review)
        else:
            request = self.retry(response, "identifier not found on " + response.url)
            if request:
                yield request
                return
            yield product

    def parse_review(self, response):
        hxs = HtmlXPathSelector(response)

        reviews = hxs.select(u'//div[contains(@id,"BVRRDisplayContentReviewID")]')
        product = response.meta['product']

        if not reviews:
            yield product
            return

        for review in reviews:
            loader = ReviewLoader(item=Review(), selector=review, date_format=u'%m/%d/%Y')
            date = review.select(u'.//span[contains(@class, "BVRRReviewDate")]/span[@class="value-title"]/@title').extract()
            if date:
                date = time.strptime(date.pop(), u'%Y-%m-%d')
                date = time.strftime(u'%m/%d/%Y', date)

                loader.add_value('date', date)


            title = review.select(u'.//span[@class="BVRRValue BVRRReviewTitle"]/text()').extract()
            if not title:
                title = u'Untitled'
            else:
                title = title[0]
            text = '\n'.join(review.select('.//div[@class="BVRRReviewDisplayStyle3Summary"]//text()[normalize-space()]').extract())
            text += '\n' + '\n'.join(review.select(u'.//div[@class="BVRRReviewDisplayStyle3Content"]//text()[normalize-space()]').extract())

            loader.add_value('full_text', u'%s\n%s' % (title, text))
            loader.add_value('product_url', product['url'])
            loader.add_value('url', product['url'])
            loader.add_value('sku', product.get('sku') or '')
            loader.add_xpath('rating', u'.//div[@id="BVRRRatingOverall_Review_Display"]//span[@class="BVRRNumber BVRRRatingNumber"]/text()')
            product['metadata']['reviews'].append(loader.load_item())

        next_page = hxs.select(u'.//a[contains(text(),"Next page")]/@data-bvjsref').extract()
        if not next_page:
            yield product
            return
        else:
            yield Request(urljoin_rfc(get_base_url(response), next_page[0]),
                          meta=response.meta,
                          callback=self.parse_review,
                          dont_filter=True)

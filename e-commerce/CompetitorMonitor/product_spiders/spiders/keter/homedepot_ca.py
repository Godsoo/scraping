import re
import urllib
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from keteritems import KeterMeta, Review, ReviewLoader


class HomedepotCaSpider(BaseSpider):
    name = 'homedepot.ca'
    allowed_domains = ['homedepot.ca']
    user_agent = 'Googlebot/2.1 (+http://www.google.com/bot.html)'

    def start_requests(self):
        search_url = 'http://www.homedepot.ca/webapp/wcs/stores/servlet/SearchView?'\
                     + 'D=%(brand)s&Ntt=%(brand)s&langId=-15&Dx=mode+matchallpartial'\
                     + '&storeId=10051&Ntx=mode+matchallpartial&catalogId=10051&Nty=1&s=true&N='
        for brand in ('Keter', 'Suncast', 'Rubbermaid', 'Lifetime', 'Step 2', 'Step2', 'Sterilite'):
            yield Request(search_url % {'brand': urllib.quote(brand)},
                          meta={'brand': brand}, callback=self.parse_search)

    def _match_brand(self, brand_name, response):
        if brand_name.lower().startswith(response.meta['brand'].lower()):
            return True
        # Jardin == Keter
        if brand_name.lower().startswith('jardin') and response.meta['brand'].lower() == 'keter':
            return True
        return False

    def parse_search(self, response):
        hxs = HtmlXPathSelector(response)
        brands = hxs.select(u'//input[contains(@data-category,"Brand")]')
        if brands:
            for brand in brands:
                brand_name = brand.select(u'./span/text()').extract()
                if not brand_name:
                    brand_name = brand.select(u'../span/text()').extract()
                if self._match_brand(brand_name[0], response):
                    brand_id = brand.select(u'./@value').extract()[0]
                    yield Request(response.url + brand_id, meta=response.meta, callback=self.parse_product_list)
            return

        for x in self.parse_product_list(response):
            yield x

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        links = hxs.select(u'//p[@class="product-name"]/a/@href').extract()
        for url in links:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, meta=response.meta, callback=self.parse_product)

        next_url = hxs.select(u'//li/a[@class="next"]/@href').extract()
        if next_url:
            url = urljoin_rfc(get_base_url(response), next_url[0])
            yield Request(url, meta=response.meta, callback=self.parse_product_list)

        if not links and not next_url:
            # If only 1 product per brand exists, search forwards to product page
            for x in self.parse_product(response):
                yield x

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        product_loader = ProductLoader(item=Product(), response=response)
        name = hxs.select(u'//div[@class="column main-info"]/h1/text()').extract()[-1]
        product_loader.add_value('name', name.strip())
        product_loader.add_xpath('sku', u'//span[@class="store-sku"]/text()')
        # async JS
        # product_loader.add_xpath('price', u'//p[@class="offer-price"]/text()')
        product_loader.add_value('url', response.url)
        product_loader.add_value('brand', response.meta['brand'].strip().lower())
        image_url = hxs.select('//*[@id="main-product-image"]/img/@src').extract()
        if not image_url:
            self.log('ERROR no IMAGE found!')
        else:
            image_url = urljoin_rfc(get_base_url(response), image_url[0])
            product_loader.add_value('image_url', image_url)
        category = hxs.select('//*[@id="global-crumb-trail"]//a[2]/text()').extract()
        if not category:
            self.log('ERROR no CATEGORY found!')
        else:
            product_loader.add_value('category', category[0])
        identifier = hxs.select('//*[@id="internet-cat"]/text()').extract()
        if not identifier:
            self.log('ERROR no IDENTIFIER found!')
        else:
            product_loader.add_value('identifier', identifier[0])
        product = product_loader.load_item()

        metadata = KeterMeta()
        metadata['brand'] = response.meta['brand']
        metadata['reviews'] = []
        product['metadata'] = metadata
        response.meta['product'] = product

        reviews = hxs.select(u'//div[@class="bv-reviews"]//iframe/@src').extract()
        if reviews:
            yield Request(reviews[0], meta=response.meta, callback=self.parse_review)
        else:
            price_url = 'http://www.homedepot.ca/async-fetch-regional-price?storeId=9999&pnList='
            price_url += product['url'].split('/')[-1]
            yield Request(price_url, meta=response.meta, callback=self.parse_price)

    def parse_review(self, response):
        hxs = HtmlXPathSelector(response)
        product = response.meta['product']

        for review in hxs.select(u'//div[starts-with(@id, "BVRRDisplayContentReviewID_")]'):
            review_loader = ReviewLoader(item=Review(), selector=review, date_format="%B %d, %Y")
            review_loader.add_xpath('date', u'.//span[contains(@class,"BVRRReviewDate")]/text()')

            title = review.select(u'.//span[contains(@class,"BVRRReviewTitle")]/text()').extract()
            text = review.select(u'.//span[contains(@class,"BVRRReviewText")]/text()').extract()
            text = ' '.join(text)

            if title:
                full_text = title[0] + '\n' + text
            else:
                full_text = text

            pros = review.select(u'.//span[contains(@class,"BVRRReviewProTags")]/span/text()').extract()
            cons = review.select(u'.//span[contains(@class,"BVRRReviewConTags")]/span/text()').extract()
            if pros:
                full_text += '\nPros: ' + ', '.join(pros)
            if cons:
                full_text += '\nCons: ' + ', '.join(cons)

            review_loader.add_value('full_text', full_text)
            review_loader.add_xpath('rating', u'.//span[contains(@class,"BVRRRatingNumber")]/text()')
            review_loader.add_value('url', response.url)

            product['metadata']['reviews'].append(review_loader.load_item())

        next_url = hxs.select(u'//div[contains(@class,"BVRRNextPage")]/a/@href').extract()
        if next_url:
            yield Request(next_url[0], meta=response.meta, callback=self.parse_review)
        else:
            price_url = 'http://www.homedepot.ca/async-fetch-regional-price?storeId=9999&pnList='
            price_url += product['url'].split('/')[-1]

            yield Request(price_url, meta=response.meta, callback=self.parse_price)

    def parse_price(self, response):
        product = response.meta['product']
        # reg-price="349.0" promo-price="349.0"
        match = re.search(u'promo-price="([\d.,]+)"', response.body)
        if not match:
            match = re.search(u'reg-price="([\d.,]+)"', response.body)
        # contains negative price if price not available, regexp does not patch negative values
        if match:
            product['price'] = match.group(1)
            yield product

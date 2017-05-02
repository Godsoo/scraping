import re
import os
import datetime
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from keteritems import KeterMeta, Review, ReviewLoader
import demjson

HERE = os.path.abspath(os.path.dirname(__file__))


class ToysRUsSpider(BaseSpider):
    name = 'toysrus.co.uk'
    allowed_domains = ['toysrus.co.uk']
    start_urls = ('http://toysrus.co.uk',)

    def start_requests(self):
        brand_urls = {'step-2': u'http://www.toysrus.co.uk/browse/product/step-2',
                      'keter': u'http://www.toysrus.co.uk/browse/product/keter'}
        for brand, url in brand_urls.items():
            yield Request(url, meta={'brand': brand}, callback=self.parse_brand)

    def parse_brand(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)

        next_page = hxs.select(u'//li[@class="previous_next"]/a[contains(text(),"Next")]/@href').extract()
        if next_page:
            next_page = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(next_page, meta=response.meta, callback=self.parse_brand)

        products = set(hxs.select(u'//dl[@class="hproduct"]/dt/a/@href').extract())
        for url in products:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, meta=response.meta, callback=self.parse_product)

    def parse(self, response):
        pass

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        name = hxs.select(u'//div[@class="product_detail_main" or @class="product_lead"]/h1/text()').extract()
        if not name:
            self.log('ERROR: no product NAME found! URL:{}'.format(response.url))
        else:
            loader.add_value('name', name[0].strip())

        prod_id = re.search('\((.*)\)', response.url).group(1)
        loader.add_value('identifier', prod_id)
        # commented out because purchase form is not available when product is not in stock
        # prod_id = hxs.select('//*[@id="contentSubView:productDetailForm"]/../../../../../table/@id').extract()
        # if not prod_id:
        #     self.log('ERROR: no product ID found! URL:{}'.format(response.url))
        #     return
        # else:
        #     prod_id = prod_id[0]
        #     loader.add_value('identifier', prod_id)

        loader.add_value('url', response.url)

        price = hxs.select(u'//div[@class="pricing prices_new"]/ul/li[@class="price"]/text()').extract()
        if not price:
            price = hxs.select(u'//li[@class="price_bucket"]/ul/li[@class="total_price"]/text()').extract()
            if not price:
                self.log('ERROR: no product PRICE found! URL:{}'.format(response.url))
                return
        if price:
            loader.add_value('price', price[0])

        product_image = hxs.select('//*[@id="contentSubView:productImagesForm:productDetailImage"]/@src').extract()
        if not product_image:
            self.log('ERROR: no product Image found!')
        else:
            image = urljoin_rfc(get_base_url(response), product_image[0].strip())
            loader.add_value('image_url', image)

        category = hxs.select('//div[@class="breadcrumb"]/ul/li[1]/a[1]/text()').extract()
        if not category:
            self.log('ERROR: category not found! URL:{}'.format(response.url))
        else:
            loader.add_value('category', category[0].strip())

        sku = hxs.select('//ul[@class="product_meta"]/li[1]/text()').re('(\d+)')
        if not sku:
            self.log('ERROR: no SKU found! URL:{}'.format(response.url))
        else:
            loader.add_value('sku', sku[0].strip())

        loader.add_value('brand', response.meta['brand'].strip().lower())
        product = loader.load_item()

        reviews_url = u'http://www.toysrus.co.uk/pwr/content/%s/%s-en_GB-1-reviews.js' % (self.calculate_url(prod_id), prod_id)
        metadata = KeterMeta()
        metadata['brand'] = response.meta['brand'].strip().lower()
        metadata['reviews'] = []
        product['metadata'] = metadata
        meta = {'dont_retry': True, 'handle_httpstatus_list': [404], 'cur_page': 1, 'product': product, 'product_url': response.url, 'reviews_url': u'http://www.toysrus.co.uk/pwr/content/' + u'%s/%s'  % (self.calculate_url(prod_id), prod_id) +
                                                                                             u'-en_GB-%s-reviews.js'}
        yield Request(reviews_url, meta=meta, callback=self.parse_review)

    def parse_review(self, response):

        reviews = re.search(u'= (.*);$', response.body, re.DOTALL)

        product = response.meta['product']

        if response.status != 200 or not reviews:
            yield product
            return

        reviews = reviews.group(1)
        reviews = map(lambda x: x.get('r'), demjson.decode(reviews))

        for review in reviews:
            loader = ReviewLoader(item=Review(), selector=review, date_format=u'%d/%m/%Y')
            try:
                date_review = datetime.datetime.strptime(review.get('d'), "%m/%d/%Y").date()
                date_review = date_review.strftime("%d/%m/%Y")
            except:
                date_review = review.get('d')

            loader.add_value('date', date_review)

            title = review['h']
            text = review['p']

            review_data = {}
            for data in review['g']:
                review_data[data['n']] = u', '.join(data['v'])
            fields = [u'Pros', u'Cons', u'Best Uses']
            text += u'\n'
            for field in fields:
                if review_data.get(field):
                    text += u'%s:\n%s\n' % (field, review_data.get(field))
            if review['b']['k'] == 'Yes':
                text += u'Yes, I would recommend this to a friend.'
            else:
                text += u'No, I would not recommend this to a friend.'

            loader.add_value('full_text', u'%s\n%s' % (title, text))
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
        cg = '0' * (ci-len(cg)) + cg
        return cg[0 : ci/2] + '/' + cg[ci/2 : ci]

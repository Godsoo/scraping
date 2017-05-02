# -*- coding: utf-8 -*-

import re
from product_spiders.spiders.keter.keteritems import KeterMeta
from product_spiders.spiders.siehunting.generic import GenericReviewSpider
import urlparse
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import (
    ProductLoaderWithNameStrip as ProductLoader,
    Product
)
from scrapy.selector import HtmlXPathSelector

try:
    import simplejson as json
except ImportError:
    import json

__author__ = 'Theophile R. <rotoudjimaye.theo@gmail.com>'

digits = re.compile("\d+")


def get_reviews_url(product):
    url = product['url']
    parsed = urlparse.urlparse(url)
    params = urlparse.parse_qs(parsed.query)
    productId = params.get('productId')
    if productId:
        return 'http://reviews.lowes.com/0534/%s/reviews.htm' % productId[0]
    return None


def next_review_url(response, hxs=None):
    product = response.meta['product']
    next_page = hxs.select('//a[@name="BV_TrackingTag_Review_Display_NextPage"]/@href').extract()
    if next_page:
        return next_page[0]
    if 'productId=3030374' in product['url']:
        return 'http://reviews.lowes.com/0534/3122403/reviews.htm'
    if 'productId=1069811' in product['url']:
        return 'http://reviews.lowes.com/0534/3014192/reviews.htm'


def review_rating_extractor(review_box):
    url = review_box.select('.//div[@class="BVRRRatingNormalImage"]//img[@class="BVImgOrSprite"]/@src').extract()
    if url:
        return url[0].split("/")[-3].replace('_', '.')
    return None


class LowesSpider(GenericReviewSpider):
    name = "keter-lowes.com"
    allowed_domains = ["lowes.com"]
    user_agent = 'scrapybot'

    start_urls = [
        "http://www.lowes.com/Search=keter?storeId=10151&langId=-1&catalogId=10051&N=0&newSearch=true&Ntt=keter&rpp=48&page=1",
        "http://www.lowes.com/Search=SUNCAST?storeId=10151&langId=-1&catalogId=10051&N=0&newSearch=true&Ntt=SUNCAST&rpp=48&page=1",
        "http://www.lowes.com/Search=RUBBERMAID?storeId=10151&langId=-1&catalogId=10051&N=0&newSearch=true&Ntt=RUBBERMAID&rpp=48&page=1",
        "http://www.lowes.com/Search=LIFETIME?storeId=10151&langId=-1&catalogId=10051&N=0&newSearch=true&Ntt=LIFETIME&rpp=48&page=1",
        "http://www.lowes.com/Search=STEP2?storeId=10151&langId=-1&catalogId=10051&N=0&newSearch=true&Ntt=STEP2&rpp=48&page=1",
        "http://www.lowes.com/Search=STEP2?storeId=10151&langId=-1&catalogId=10051&N=0&newSearch=true&Ntt=STEP+2&rpp=48&page=1",
        "http://www.lowes.com/Search=STERILITE?storeId=10151&langId=-1&catalogId=10051&N=0&newSearch=true&Ntt=STERILITE&rpp=48&page=1",
    ]

    BRAND_GET_PARAM = "Ntt"

    # NAVIGATION = ['//div[@id="content-area-prod-list"]//a/@href', ]
    NAVIGATION = ['//ul[@id="productResults"]//a/@href']

    PRODUCT_BOX = [
        ('.', {'name': '//div[@id="descCont"]//h1/text()',
               'sku': '//span[@id="ModelNumber"]/text()',
               'price': '//div[@id="pricing"]/span[@class="price"]/text()',
               'review_url': get_reviews_url})
    ]

    PRODUCT_REVIEW_DATE_FORMAT = '%B %d, %Y'
    PRODUCT_REVIEW_BOX = {'xpath': '//div[@id="BVRRSDisplayContentBodyID"]/div', 'full_text': './/div[@class="BVRRReviewTextContainer"]//span/text()', 'date': './/span[@class="BVRRValue BVRRReviewDate dtreviewed"]/text()', 'rating': review_rating_extractor, 'next_url': next_review_url}
    PRODUCT_URL_EXCLUDE = ("productId=3122403", "productId=3014192")
    PRODUCT_IDS_EXCLUDE = ('3122403', '3014192')

    def __init__(self, *args, **kwargs):
        super(GenericReviewSpider, self).__init__(*args, **kwargs)
        # dispatcher.connect(self.item_scraped, signals.item_scraped)
        # dispatcher.connect(self.item_dropped, signals.item_dropped)
        self.products_map = {}
        self._cookies = {"selectedStore1": "Lowe's Of Wilkesboro## NC|0701|0|28697|no|Y|2003 Us Highway 421|Wilkesboro|Mon-Sat 7 Am - 9 Pm## Sun 9 Am - 7 Pm|(336) 838-1500|(336) 838-1732|KD; path=/"}
        self._current_cookiejar = 0

    def start_requests(self):
        reqs = []
        for url in self.start_urls:
            parsed = urlparse.urlparse(url)
            params = urlparse.parse_qs(parsed.query)
            brand = params.get(self.BRAND_GET_PARAM)
            '''
            if brand:
                ajax_url = "http://www.lowes.com/webapp/wcs/stores/servlet/GuidedSellingAjaxCmd?langId=-1&storeId=10151&catalogId=10051&categoryName=&nValue=0&page=%(page)s&rpp=16&neValue=&Ntt=%(brand)s" % {'brand': brand[0], 'page': 1}
                reqs.append(Request(ajax_url,
                                    meta={'product_brand': brand[0].replace(" ", "") if brand else None},
                                    cookies=cookies))
            '''
            reqs.append(Request(url,
                                meta={'product_brand': brand[0].replace(" ", "") if brand else None,
                                      'cookiejar': 0}))
        return reqs

    def build_full_name(self, spotlightDescription, description):
        if not spotlightDescription.endswith("..."):
            return spotlightDescription
        index = 1
        while index < len(description):
            try:
                start = description[:-index]
                return spotlightDescription[0:spotlightDescription.index(start)] + description
            except ValueError:
                index += 1

    def item_scraped(self, item, response, spider):
        """" """
        self.products_map[item['name']] = item

    def item_dropped(self, item, spider):
        """ Merge duplicate items reviews"""
        initial = self.products_map.get(item['name'])
        if initial and initial['url'] != item['url']:
            initial['metadata'].setdefault('reviews', [])
            initial['metadata']['reviews'].extend(item['metadata'].get('reviews', []))

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = self.get_base_url(response)

        products = hxs.select('//ul[@id="productResults"]//a/@href').extract()
        self.log('FOUND %s products in => %s' % (len(products), response.url))
        for url in map(lambda u: urljoin_rfc(base_url, u), products):
            self._current_cookiejar += 1
            meta = {'product_brand': response.meta['product_brand'],
                    'cookiejar': self._current_cookiejar}
            yield Request(url,
                          callback=self.parse_product,
                          meta=meta,
                          cookies=self._cookies)

        pages = self.next_pages(response, hxs, base_url)
        for page in pages:
            meta = response.meta.copy()
            yield Request(page,
                          callback=self.parse_products,
                          meta=meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = self.get_base_url(response)

        try:
            identifier = re.search(r'\?productId=(\d+)', response.url).groups()[0]
        except:
            return
        else:
            if identifier in self.PRODUCT_IDS_EXCLUDE:
                return

        brand = response.meta.get('product_brand')

        product_loader = ProductLoader(item=Product(), response=response)

        product_loader.add_xpath('name', '//div[@id="descCont"]//h1/text()')
        product_loader.add_xpath('sku', '//span[@id="ModelNumber"]/text()')
        product_loader.add_xpath('price', '//div[@id="pricing"]/span[@class="price"]/text()')
        product_loader.add_value('identifier', identifier)
        product_loader.add_value('brand', brand)
        product_loader.add_value('url', response.url)

        product = product_loader.load_item()

        if 'metadata' not in product:
            product['metadata'] = KeterMeta()
            product['metadata']['brand'] = brand

        reviews_url = get_reviews_url(product)
        if not reviews_url:
            yield product
        else:
            meta = dict(**response.meta)
            meta.update({'product': product})
            yield Request(url=reviews_url, callback=self.parse_product_reviews, meta=meta)

        # for item in self.do_parse_products(response, hxs, base_url): yield item

    '''
    def parse_products(self, response):
        try:
            json_result = json.loads(response.body)
        except:
            #
            for e in GenericReviewSpider.parse_products(self, response): yield e
            return
        base_url = self.get_base_url(response)
        products = json_result['prodListAjaxResp'].get('products') if 'prodListAjaxResp' in json_result else []
        if products:
            brand = response.meta.get('product_brand')
            for p in products:
                # if brand.lower != p['brandName'].lower(): continue

                product = Product()
                productLink = p['productDetailLink']
                product['name'] = self.build_full_name(p['spotlightDescription'], p['description'])
                product['price'] = p['price']
                product['url'] = urlparse.urljoin("http://www.lowes.com/", productLink['url'])
                product['sku'] = p['partNumber'].get('modelId')
                product['identifier'] = product['sku']
                product['brand'] = brand.strip().lower()

                exclude = False
                for item in self.PRODUCT_URL_EXCLUDE:
                    if item in product['url']:
                        exclude = True

                if exclude: continue

                if 'metadata' not in product:
                    product['metadata'] = KeterMeta()
                    product['metadata']['brand'] = brand

                reviews_url = get_reviews_url(product)
                if not reviews_url:
                    yield product
                else:
                    meta = dict(**response.meta)
                    meta.update({'product': product})
                    yield Request(url=reviews_url, callback=self.parse_product_reviews, meta=meta)
            # next page
            parsed = urlparse.urlparse(base_url)
            params = urlparse.parse_qs(parsed.query)
            page = params.get('page')
            if page:
                ajax_url = "http://www.lowes.com/webapp/wcs/stores/servlet/GuidedSellingAjaxCmd?langId=-1&storeId=10151&catalogId=10051&categoryName=&nValue=0&page=%(page)s&rpp=16&neValue=&Ntt=%(brand)s" % {'brand': brand, 'page': (int(page[0]) + 1)}
                yield Request(url=ajax_url, callback=self.parse_products, meta={'product_brand': brand})
    '''

    def parse_product_ext(self, response, hxs, product):
        product['identifier'] = re.search(r'\?productId=(\d+)', response.url).groups()[0]

        if 'metadata' not in product:
            product['metadata'] = KeterMeta()
            product['metadata']['brand'] = None

        if self.BRAND_GET_PARAM and product['metadata']['brand'] is None:
            brand = response.meta.get('product_brand')
            if brand:
                product['metadata']['brand'] = brand
                if not product.get('brand'):
                    product['brand'] = brand

        return product

    def next_pages(self, response, hxs, base_url):
        links = GenericReviewSpider.navigation_links(self, response, hxs, base_url)
        parsed = urlparse.urlparse(response.url)
        params = urlparse.parse_qs(parsed.query)
        nexts = hxs.select('//div[@class="product-listing"]/div[@class="topBar"]//form/span[@class="pagination_wrapper"]//a/@href').extract()
        pages = set(map(lambda u: re.search(r'page=(\d+)', u).groups()[0], nexts))
        for p in pages:
            params['page'] = p
            links.add(urlparse.ParseResult(scheme=parsed.scheme,
                                           netloc=parsed.netloc,
                                           path=parsed.path,
                                           params=parsed.params,
                                           fragment=parsed.fragment,
                                           query='&'.join('%s=%s' % (param[0],
                                                                     param[1][0])
                                                          for param in params.items())
                                           ).geturl())
        return links
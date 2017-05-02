# -*- coding: utf-8 -*-
from datetime import datetime
import json
import re

from scrapy.contrib.loader import XPathItemLoader
from scrapy.contrib.loader.processor import MapCompose, TakeFirst, Join
from scrapy.http import Request, FormRequest
from scrapy.item import Item, Field
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter
from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from w3lib.html import remove_entities
from urlparse import urljoin


from items import Product, ProductLoaderWithoutSpaces

__author__ = 'juraseg'


class TargetProductLoader(ProductLoaderWithoutSpaces):
    pass


class TargetMeta(Item):
    reviews = Field()
    brand = Field()


class Review(Item):
    date = Field()
    rating = Field()
    full_text = Field()
    url = Field()
    review_id = Field()


def extract_date(s, loader_context):
    date_format = loader_context['date_format']
    d = datetime.strptime(s, date_format)
    return d.strftime('%d/%m/%Y')


def extract_rating(s):
    r = re.search('(\d+)', s)
    if r:
        return int(r.groups()[0])


class TargetReviewLoader(XPathItemLoader):
    date_in = MapCompose(unicode, unicode.strip, extract_date, date_format='%d/%m/%Y')
    date_out = TakeFirst()

    rating_in = MapCompose(unicode, extract_rating)
    rating_out = TakeFirst()

    full_text_in = MapCompose(unicode, unicode.strip, remove_entities)
    full_text_out = Join()

    url_in = MapCompose(unicode, unicode.strip)
    url_out = TakeFirst()

    review_id_in = MapCompose(unicode, unicode.strip, unicode.lower)
    review_id_out = TakeFirst()


class BaseTargetSpider(BaseSpider):
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:24.0) Gecko/20100101 Firefox/24.0'
    allowed_domains = ['target.com', 'tws.target.com', 'c3.ugc.bazaarvoice.com', 'api.bazaarvoice.com']

    ProductLoaderCls = TargetProductLoader
    ReviewLoaderCls = TargetReviewLoader

    # type of category: single or ordered (last 3)
    category_type = 'single'

    def _load_product_data_to_loader(self, response):
        hxs = HtmlXPathSelector(response)
        loader = self.ProductLoaderCls(item=Product(), response=response)
        identifier = hxs.select('//input[@id="omniPartNumber"]/@value').extract()
        if not identifier:
            identifier_m = re.search(r'A-(\d+)', response.url)
            if identifier_m:
                identifier = identifier_m.groups()[0]
            else:
                return None
        else:
            identifier = identifier[0]

        sku = response.meta.get('sku', '')

        name = hxs.select('//h2[contains(@class, "title-product")]/span/text()').extract()

        if not name:
            return None
        else:
            name = name[0]

        brand = response.meta.get('brand', '')

        if self.category_type == 'ordered':
            categories = hxs.select(u'//div[@id="breadcrumbs"]/span/a/text()').extract()[-3:]
            categories = map(lambda x: x.strip(), categories)
            loader.add_value('category', categories)
        else:
            category = hxs.select(u'//div[@id="breadcrumbs"]/span[@class="last"]/a/text()').extract()
            category = category[-1].strip() if category else ''
            loader.add_value('category', category)
        loader.add_value('identifier', identifier)
        loader.add_value('name', name)
        loader.add_value('brand', brand)
        loader.add_value('sku', sku)
        loader.add_value('url', response.url)
        price = hxs.select('//p[@class="price"]/span[@itemprop="price"]/text()').extract()
        if not price:
            price = hxs.select('//span[@class="price"]/span[@itemprop="price"]/text()').extract()
        price = price[0] if price else ''
        loader.add_value('price', price)
        image = hxs.select('//*[@id="heroImage"]/@src').extract()
        image = image[0] if image else ''
        loader.add_value('image_url', image)

        return loader

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        identifier = hxs.select('//input[@id="omniPartNumber"]/@value').extract()
        if not identifier:
            identifier_m = re.search(r'A-(\d+)', response.url)
            if identifier_m:
                identifier = identifier_m.groups()[0]
            else:
                self.log("No product found: %s" % response.url)
                return
        else:
            identifier = identifier[0]

        name = hxs.select('//h2[contains(@class, "product-name")]/span/text()').extract()

        if not name:
            retry = int(response.meta.get('retry', 0))
            if retry < 10:
                retry += 1
                if '#' in response.url:
                    url = response.url.split('#')[0]
                else:
                    url = response.url
                meta = response.meta
                meta['retry'] = retry
                yield Request(url, callback=self.parse_product, meta=meta, dont_filter=True)
                return

        loader = self._load_product_data_to_loader(response)

        if loader is None:
            return

        product = loader.load_item()
        metadata = TargetMeta()
        metadata['reviews'] = []
        product['metadata'] = metadata
        reviews_url = self._get_reviews_url(identifier)
        request = Request(reviews_url, meta={'product': product, 'offset': 0, 'identifier': identifier}, callback=self.parse_reviews)
        yield request

    def parse_reviews(self, response):
        product = response.meta['product']
        identifier = response.meta['identifier']
        json_body = json.loads(response.body)

        reviews = json_body['result']
        for review in reviews:
            review_loader = self.ReviewLoaderCls(item=Review(), response=response, date_format="%B %d, %Y")
            parsed_review = self.parse_review(product['url'], review, review_loader)

            product['metadata']['reviews'].append(parsed_review)

        if len(reviews) == 100:
            offset = response.meta['offset'] + 100
            next_reviews = self._get_reviews_url(identifier, offset)
            request = Request(next_reviews, meta={'product': product, 'offset': offset, 'identifier': identifier},
                              callback=self.parse_reviews)
            yield request
        else:
            yield product

    def get_review_full_text(self, review):
        title = review['Title']
        text = review['ReviewText']

        if title:
            full_text = title + '\n' + text
        else:
            full_text = text

        pros = review['Pros']
        cons = review['Cons']
        if pros:
            full_text += '\nPros: ' + ', '.join(pros)
        if cons:
            full_text += '\nCons: ' + ', '.join(cons)

        return full_text

    def parse_review(self, product_url, review, review_loader):
        review_date = datetime.strptime(review['SubmissionTime'].split('.')[0], '%Y-%m-%dT%H:%M:%S')
        review_loader.add_value('date', review_date.strftime("%B %d, %Y"))

        full_text = self.get_review_full_text(review)

        pros = review['Pros']
        cons = review['Cons']
        if pros:
            full_text += '\nPros: ' + ', '.join(pros)
        if cons:
            full_text += '\nCons: ' + ', '.join(cons)

        review_loader.add_value('full_text', full_text)
        rating = review['Rating']
        review_loader.add_value('rating', rating)
        review_loader.add_value('url', product_url)
        review = review_loader.load_item()
        return review

    def _get_reviews_url(self, identifier, offset=0):
        return 'https://redsky.target.com/groot-domain-api/v1/reviews/' + identifier + \
            '?sort=helpfulness_desc&filter=&limit=1000&offset=' + str(offset)

    def _load_product_json_data_to_loader(self, response):
        data = json.loads(response.body)['product']
        try:
            identifier = data['item']['tcin']
        except KeyError:
            return
        loader = self.ProductLoaderCls(Product(), response=response)
        loader.add_value('identifier', identifier)
        loader.add_value('url', data['item']['buy_url'])
        loader.add_value('name', data['item']['product_description']['title'])
        price = data['price']['offerPrice']['price'] or data['price']['offerPrice']['formattedPrice'] or data['price']['offerPrice']['minPrice']
        loader.add_value('price', price)
        loader.add_value('sku', response.meta.get('sku'))
        try:
            categories = data['taxonomy']['breadcrumbs'][0][1:]
        except KeyError:
            classification = data['item']['product_classification']
            if classification:
                categories = []
                for field in ('product_type_name',
                              'product_subtype_name',
                              'item_type_name'):
                    name = classification.get(field)
                    if name:
                        categories.append(name)
            else:
                categories = []
        if self.category_type == 'ordered':
            categories = categories[-3:]
        else:
            categories = categories[-1:]
        for category in categories:
            if not isinstance(category, basestring):
                category = category['seo_data']['seo_h1']
            loader.add_value('category', category)
        loader.add_value('image_url',  urljoin(data['item']['enrichment']['images'][0]['base_url'], data['item']['enrichment']['images'][0]['primary']))
        brand = response.meta.get('brand') or data['item']['product_brand'].get('manufacturer_brand')
        loader.add_value('brand', brand)
        try:
            stock = data['available_to_promise_network']['availability']
        except KeyError:
            loader.add_value('stock', 0)
        else:
            loader.add_value('stock', int(stock=='AVAILABLE'))
        return loader

    def parse_product_json(self, response):
        loader = self._load_product_json_data_to_loader(response)
        if not loader:
            return
        product = loader.load_item()
        identifier = json.loads(response.body)['product']['item']['tcin']

        metadata = TargetMeta()
        metadata['reviews'] = []
        product['metadata'] = metadata
        reviews_url = self._get_reviews_url(identifier)
        request = Request(reviews_url, meta={'product': product, 'offset': 0, 'identifier': identifier}, callback=self.parse_reviews)
        yield request

    def parse(self, response):
        product_urls = []
        tcins = []
        if 'tws.target.com/searchservice/item/search_results/v2/by_keyword' in response.url:
            # Using Target Web Services
            data = json.loads(response.body)
            items = data['searchResponse']['items']['Item']
            for item in items:
                tcins.append(item['tcin'])

            try:
                # Pages
                pages_info = {}
                for d in data['searchResponse']['searchState']['Arguments']['Argument']:
                    pages_info[d['name']] = d['value']

                current_page = int(pages_info['currentPage'])
                total_pages = int(pages_info['totalPages'])
                page_count = int(pages_info['resultsPerPage'])
                offset = int(pages_info.get('offset', 0))
            except:
                self.log('Next page not found => %s' % response.url)
            else:
                if current_page < total_pages:
                    url = add_or_replace_parameter(response.url, 'offset', str(offset + page_count))
                    yield Request(url, meta=response.meta)

            for tcin in tcins:
                url = 'http://redsky.target.com/v1/pdp/tcin/%s' %tcin
                yield Request(url, self.parse_product_json, meta=response.meta)

        else:
            # Old method ...
            hxs = HtmlXPathSelector(response)
            product_urls = hxs.select('//div[@class="productTitle"]/a[@class="productClick"]/@href').extract()
            if not product_urls:
                product_urls = hxs.select('//a[contains(@class, "productTitle")]/@href').extract()

            search_term = hxs.select('//*[@id="searchTermDbp"]/@value').extract()
            if not search_term:
                search_term = hxs.select('//span[@class="srhTerm"]/text()').extract()

            if not search_term:
                search_term = response.meta.get('search_term') or response.meta.get('brand', '').strip().lower().replace(' ', '+')
            else:
                search_term = search_term[0]
            product_count = hxs.select('//*[@id="productCountValue"]/@value').extract()
            if not product_count:
                product_count = hxs.select('//span[@id="countMsg"]/text()').re('\d+')

            if not product_count:
                product_count = response.meta.get('product_count')
            else:
                product_count = product_count[0]
            if not product_urls:
                try:
                    data = json.loads(response.body)
                    data = data['productListArea']['productListForm']
                    hxs = HtmlXPathSelector(text=data)
                    product_urls = hxs.select('//div[@class="productTitle"]/a[@class="productClick"]/@href').extract()
                except:
                    pass

            next_page = hxs.select('//a[@id="seeMoreItemButton"]/@href')
            if next_page:
                self.log('Next page')
                yield Request(next_page.extract()[0], meta=response.meta, dont_filter=True)
            else:
                next_page = hxs.select('//div[contains(@class, "next")]/a/@href').extract()
                if next_page:
                    self.log('Next page')
                    yield Request(urljoin_rfc(get_base_url(response), next_page[0]), meta=response.meta, dont_filter=True)

            if product_urls:
                nao = response.meta.get('nao', 16)
                hash_value = '#navigation=true&Nao=%s&viewType=medium&RatingFacet=0&customPrice=false&productsCount=%s&isDbp=true' % (nao, product_count)
                ajaxlinkdata = ('http://www.target.com/SearchNavigationView?viewType=medium&customPrice=false&productsCount=%s&RatingFacet=0'
                                '&searchTerm=%s&dbpSeeMore=true&Nao=%s&isDbp=true') % (product_count, search_term, nao)

                formdata = {'ajaxLinkData': ajaxlinkdata, 'hashValue': hash_value, 'stateData': '', 'searchTerm': search_term, 'viewType': 'medium'}

                yield FormRequest('http://www.target.com/bp/SearchNavigationView',
                                  method='POST',
                                  formdata=formdata,
                                  dont_filter=True,
                                  meta={'nao': int(nao) + 16,
                                        'formdata': formdata,
                                        'brand': response.meta.get('brand', ''),
                                        'product_count': product_count,
                                        'search_term': search_term})

                for url in product_urls:
                    yield Request(url, callback=self.parse_product, meta={'brand': response.meta.get('brand', '')})
            else:
                retry = int(response.meta.get('retry', 0))
                if retry < 10:
                    retry += 1
                    meta = response.meta
                    meta['retry'] = retry
                    if meta.get('formdata'):
                        yield FormRequest('http://www.target.com/bp/SearchNavigationView',
                                          method='POST',
                                          formdata=meta['formdata'],
                                          dont_filter=True,
                                          meta=meta)
                    else:
                        yield Request(response.url, dont_filter=True, meta=meta)
                else:
                    return

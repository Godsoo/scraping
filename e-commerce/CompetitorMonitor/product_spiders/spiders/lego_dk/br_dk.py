import re
import json
import urlparse
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.prodcache import ProductCacheSpider
from math import ceil

class BrSpider(ProductCacheSpider):
    name = 'br.dk'
    allowed_domains = ['br.dk']
    start_urls = ('http://www.br.dk/Brands/LEGO',)

    '''
    def start_requests(self):
        yield Request('http://www.br.dk/brands/lego%20bricks%20and%20more/lego-10659-bl%C3%A5-kuffert?id=894137&vid=155140', callback=self.parse_product)
    '''

    def start_requests(self):
        yield self.mkreq_brand(0)

    def mkreq_brand(self, n=0):
        return Request('http://www.br.dk/RestApi/RestSearchService/MultiSearch',
                method='POST',
                body='{"Queries":[{"PageNumber":%d,"NumberOfRowsOnPage":24,"AgeRanges":null,"Categories":["Brands|LEGO"],"Filters":null,"FromPrice":null,"ToPrice":null,"SortBy":["-instock","-omniturepopularityscore","-score"],"DeDuplicationFieldName":null,"AgeMonthFrom":null,"AgeMonthTo":null,"AutoCorrectSpellingErrors":false,"DocumentTypes":2,"Gender":null,"FacetsEnabled":null,"Facets":null,"FreeTextQuery":null,"BoostQuery":null,"Name":"0fd4ae10-1a0d-4c9b-8868-b16f0b47ed48","PromotionSearch":false,"QueryParsing":0,"CustomFilter":"","FacetsToIncludeInResult":["{00AEDBEB-6D4C-4FC1-90A9-9F202B287764}","{ADDC4796-93D7-4099-B2E4-2FF477369C2E}"]}]}' % n,
                headers={'Content-Type': 'application/json', 'charset': 'UTF-8', 'Accept': 'application/json'},
                meta={'n':n, 'by_brand':True},
                dont_filter=True,
                )

    def mkreq_word(self, n=0):
        return Request('http://www.br.dk/RestApi/RestSearchService/MultiSearch',
                method='POST',
                body='{"Queries":[{"Name":"result1-products","FreeTextQuery":"LEGO","DocumentTypes":2,"NumberOfRowsOnPage":24,"QueryParsing":1,"PageNumber":%d}]}' % n,
                headers={'Content-Type': 'application/json', 'charset': 'UTF-8', 'Accept': 'application/json'},
                meta={'n':n, 'by_brand': False},
                dont_filter=True,
                )

    def parse(self, response):
        data = json.loads(response.body)

        products_count = data['SearchResults'][0]['TotalHits']
        pages_count = int(ceil(products_count / 24.0))
        page = response.meta['n']
        for p in data['SearchResults'][0]['ProductSearchResults']:
            product = Product()
            discount_price = p['DiscountUnitPrice']
            price = p['EffectivePrice']
            if not extract_price_eu(discount_price):
                product['price'] = extract_price_eu(price)
            else:
                product['price'] = extract_price_eu(discount_price)
            if int(p['StockStatus']) != 0:
                product['stock'] = '0'
            request = Request(urljoin_rfc(get_base_url(response), p['Url']), meta=response.meta, callback=self.parse_product)
            yield self.fetch_product(request, self.add_shipping_cost(product))

        yield self.continue_requests(page, pages_count, response.meta['by_brand'])

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=response.meta['product'], selector=hxs)

        # 'id' is not unique
        loader.add_value('identifier', urlparse.parse_qs(urlparse.urlparse(response.url).query)['vid'][0])
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1//text()')
        sku = ''.join(hxs.select('//h1//text()').extract())
        try:
            loader.add_value('sku', re.search('(\d{3}\d*)', sku).groups()[0])
        except:
            self.log('No SKU for %s' % (response.url))
        loader.add_value('category', hxs.select('//nav[starts-with(@class,"breadcrumb")]/ol/li/text()').extract()[-1])

        img = hxs.select('//meta[@property="og:image"]/@content').extract()
        if img:
            img = img.pop()
            if "br.dkhttp://" in img:
                img = "http://" + img.split("br.dkhttp://").pop()
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img))

        loader.add_value('brand', 'lego')
        item = self.add_shipping_cost(loader.load_item())
        if not response.meta['by_brand'] and not ('lego' in item['name'].lower()):
            return
        yield item

    def continue_requests(self, page, pages_count, by_brand):
        if page < pages_count:
            if by_brand:
                return self.mkreq_brand(page + 1)
            else:
                return self.mkreq_word(page + 1)
        elif by_brand:
            return self.mkreq_word(0)
        else:
            return None

    def add_shipping_cost(self, item):
        if item['price'] >= 400:
            item['shipping_cost'] = 0
        else:
            item['shipping_cost'] = 49
        return item

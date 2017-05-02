import urllib
import logging
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from keteritems import KeterMeta, Review, ReviewLoader

individual_products = {
    'keter': [
        'http://www.homebase.co.uk/webapp/wcs/stores/servlet/'
        'ProductDisplay?langId=110&storeId=10151&partNumber=949660&ts=92',
        'http://www.homebase.co.uk/webapp/wcs/stores/servlet/'
        'ProductDisplay?langId=110&storeId=10151&partNumber=602410&ts=91',
        'http://www.homebase.co.uk/webapp/wcs/stores/servlet/'
        'ProductDisplay?langId=110&storeId=10151&partNumber=784309&ts=90',
        'http://www.homebase.co.uk/webapp/wcs/stores/servlet/'
        'ProductDisplay?langId=110&storeId=10151&partNumber=591183&ts=89',
        'http://www.homebase.co.uk/webapp/wcs/stores/servlet/'
        'ProductDisplay?langId=110&storeId=10151&partNumber=750553&ts=68',
    ]
}


class HomebaseCoUkSpider(BaseSpider):
    """
    homebase.co.uk spider for Keter account

    On this site several products have "Keter" in name, but don't have a brand.
    And some have brand but don't have "Keter" in name
    This spider generates unique urls with &ts=x so each product gets visited from brand search or from "name" search
    """
    name = 'keter-homebase.co.uk'
    allowed_domains = ['homebase.co.uk']
    user_agent = 'Googlebot/2.1 (+http://www.google.com/bot.html)'
    ts = 1

    def start_requests(self):
        search_url = 'http://www.homebase.co.uk/webapp/wcs/stores/servlet/Search' \
                     + '?storeId=10151&catalogId=1500001201&langId=110&searchTerms=%(brand)s&authToken='
        for brand in ('keter', 'suncast', 'rubbermaid', 'lifetime', 'step 2', 'sterilite'):
            yield Request(search_url % {'brand': urllib.quote_plus(brand)},
                          meta={'brand': brand}, callback=self.parse_search)

        for brand, urls in individual_products.items():
            for url in urls:
                yield Request(url, meta={'brand': brand, 'got_brand': True}, callback=self.parse_product)

    def parse_search(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//select[@name="advancedSearchTerm"]/option/@value').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, meta=response.meta, callback=self.parse_search2)

    def parse_search2(self, response):
        hxs = HtmlXPathSelector(response)

        #brands = hxs.select(u'//ul[@class="clearfix"]/li/a/@href').extract()
        brands = hxs.select(u'//form[@name="Brands"]/ul/li/a/@href').extract()
        if brands:
            for url in brands:
                s = url.lower()
                if '|brands|' in s and '|' + response.meta['brand'].lower() + '|' in s:
                    yield Request(url, meta=response.meta, callback=self.parse_product_list)
        response.meta['got_brand'] = False
        for x in self.parse_product_list(response):
            yield x

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        for url in hxs.select(u'//li[contains(@class, "productWrap")]//h4/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            self.ts += 1
            yield Request(url + '&ts=' + str(self.ts), meta=response.meta, callback=self.parse_product)

        next_url = hxs.select(u'//div[@class="paginglinks"]/a[text()="next"]/@href').extract()
        if next_url:
            yield Request(next_url[0], meta=response.meta, callback=self.parse_product_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        product_loader = ProductLoader(item=Product(), response=response)
        name = hxs.select(u'//h1/text()').extract()[0].strip()
        if not name.lower().startswith(response.meta['brand'].lower()) and not response.meta.get('got_brand', True):
            logging.error("%s [%s] not matched" % (name, response.url))
            return
        product_loader.add_value('name', name)
        product_loader.add_xpath('sku', u'//input[@id="primaryPartNumber"]/@value')
        product_loader.add_xpath('identifier', u'//input[@id="productId"]/@value')
        image_url = hxs.select(u'//div[@class="image"]/img/@src').extract()
        if image_url:
            image_url = urljoin_rfc(get_base_url(response), image_url[0])
            product_loader.add_value('image_url', image_url)
        price = hxs.select('//span[@itemprop="price"]/text()').extract()[0]
        product_loader.add_value('price', price)

        product_loader.add_value('url', response.url)
        product_loader.add_value('brand', response.meta['brand'].strip().lower())
        product = product_loader.load_item()

        metadata = KeterMeta()
        metadata['brand'] = response.meta['brand']
        metadata['reviews'] = []
        product['metadata'] = metadata
        response.meta['product'] = product

        reviews = hxs.select(u'//iframe[@id="BVFrame"]/@src').extract()
        if reviews:
            yield Request(reviews[0], meta=response.meta, callback=self.parse_review)
        else:
            yield product

    def parse_review(self, response):
        hxs = HtmlXPathSelector(response)
        product = response.meta['product']

        for r in hxs.select(u'//div[starts-with(@id,"BVRRDisplayContentReviewID_")]'):
            loader = ReviewLoader(item=Review(), selector=r, date_format='%d %B %Y')

            title = r.select(u'.//span[contains(@class,"BVRRReviewTitle")]/text()').extract()
            text = ' '.join(r.select(u'.//span[contains(@class,"BVRRReviewText")]/text()').extract())
            if title:
                text = title[0] + '\n' + text
            loader.add_value('full_text', text)
            loader.add_xpath('date', u'.//span[contains(@class,"BVRRReviewDate") '
                                     u'and contains(@class,"BVRRValue")]/text()')
            loader.add_value('rating', r.select(u'.//img[@class="BVImgOrSprite"]/@title').extract()[0].split()[0])
            loader.add_value('url', response.url)
            product['metadata']['reviews'].append(loader.load_item())

        next_url = hxs.select(u'//span[contains(@class,"BVRRNextPage")]/a/@href').extract()
        if next_url:
            yield Request(next_url[0], meta=response.meta, callback=self.parse_review)
        else:
            yield product
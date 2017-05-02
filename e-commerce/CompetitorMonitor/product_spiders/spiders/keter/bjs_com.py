# Uses the same review code as Hayneedle.com (POWERVIEWS JavaScript)
# TODO: create a common library/mixin?
import urllib
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from keteritems import KeterMeta, Review


def function_Z(CM):
    # Reimplementation of JS-based hash function for review URLs
    # function
    # Z(CM){var CL=0;var CK;for(CK=0;CK<CM.length;CK++){var
    # CJ=CM.charCodeAt(CK);CJ=CJ*Math.abs(255-CJ);CL+=CJ;}CL=CL%1023;CL=CL+"";var
    # CN=4;var
    # CI=CL.split("");for(CK=0;CK<CN-CL.length;CK++){CI.unshift("0");}CL=CI.join("");CL=CL.substring(0,CN/2)+"/"+CL.substring(CN/2,CN);return
    # CL;}

    CL = 0;
    for char in CM:
        CJ = ord(char)
        CJ = CJ * abs(255 - CJ)
        CL += CJ
    CL = CL % 1023
    CL = str(CL)
    CN = 4
    CL = '0' * (CN - len(CL)) + CL
    CL = CL[0:CN / 2] + '/' + CL[CN / 2:CN]
    return CL


def review_url(product, page):
    # http://www.bjs.com/pwr/content/00/99/KNA017-en_US-2-reviews.js
    return 'http://www.bjs.com/pwr/content/%s/%s-en_US-%d-reviews.js' % (function_Z(product), product, page)


def load_js_objects(data):
    # Loads JS objects (not the same as JSON)
    class VarToStr:
        def __getitem__(self, name):
            return name
    return eval(data, {}, VarToStr())


class BjsComSpider(BaseSpider):
    name = 'bjs.com'
    allowed_domains = ['bjs.com']
    user_agent = 'Googlebot/2.1 (+http://www.google.com/bot.html)'

    def start_requests(self):
        search_url = 'http://www.bjs.com/webapp/wcs/stores/servlet/Search' \
                     + '?catalogId=10201&storeId=10201&langId=-1&pageSize=120&currentPage=1&searchKeywords='
        for brand in ('Keter', 'SUNCAST', 'RUBBERMAID', 'LIFETIME', 'STEP 2', 'STEP2', 'STERILITE'):
            yield Request(search_url + urllib.quote_plus(brand),
                          meta={'brand': brand}, callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        links = hxs.select(u'//div[@class="item"]/a/@href').extract()
        for url in links:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, meta=response.meta, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_xpath('name', u'//h1[@id="itemNameID"]/text()')
        product_loader.add_xpath('sku', u'//input[@id="cmItemNumber"]/@value')
        product_loader.add_xpath('image_url', '//*[@id="pThumbnail"]/@src')
        category = hxs.select('//*[@id="pagepath"]/a[2]/text()').extract()
        if category:
            product_loader.add_value('category', category[0].strip())
        product_loader.add_xpath('identifier', '//form[@id="OrderItemAddForm"]/input[@name="catEntryId"]/@value')

        price = hxs.select('//td[@class="yourpricenumber"]/text()').extract()
        if not price:
            price = hxs.select('//tr/td[contains(text(),"Your Price") and position() = 1]/../td[2]/text()').extract()
        product_loader.add_value('price', price[0])

        product_loader.add_value('url', response.url)
        product_loader.add_value('brand', response.meta['brand'].lower())
        product = product_loader.load_item()

        metadata = KeterMeta()
        metadata['brand'] = response.meta['brand']

        metadata['reviews'] = []
        product['metadata'] = metadata
        response.meta['product'] = product

        n_reviews = hxs.select(u'//a/span[@class="imageontab"]/text()').extract()

        if n_reviews and n_reviews[0].strip('(0)'):
            n_reviews = int(n_reviews[0].strip('()'))
            review_sku = hxs.select(u'//input[@id="partNumber"]/@value').extract()[0]
            # 10 reviews per page
            pages = n_reviews / 10
            if n_reviews % 10 > 0:
                pages += 1
            response.meta['review_sku'] = review_sku
            response.meta['review_pages'] = pages
            response.meta['review_n'] = 1

            yield Request(review_url(response.meta['review_sku'], response.meta['review_n']),
                          meta=response.meta, callback=self.parse_review)
        else:
            yield product

    def parse_review(self, response):
        product = response.meta['product']

        body = response.body.split('] = ')[1]
        body = body.rstrip(';')
        data = load_js_objects(body)

        for r in data:
            r = r['r']
            review = Review()

            date = r['db']
            review['date'] = date[8:10] + '/' + date[5:7] + '/' + date[:4]

            comments = r['p']
            bottom_line = r['h']
            pros = cons = best_uses = []
            for short in r.get('g', []):
                k = short['k']
                if k == 'cons':
                    cons = short['v']
                elif k == 'pros':
                    pros = short['v']
                elif k == 'bestuses':
                    bestuses = short['v']

            review['full_text'] = u'%s\nBottom Line: %s\nPros: %s\nCons: %s\nBest Uses: %s\n' % (comments, bottom_line, u', '.join(pros), u', '.join(cons), u', '.join(best_uses))

            review['rating'] = r['r']

            review['url'] = response.url
            product['metadata']['reviews'].append(review)
        # XXX maybe there is a better way to yield product after all review have been fetched
        if response.meta['review_n'] == response.meta['review_pages']:
            yield product
        else:
            response.meta['review_n'] = response.meta['review_n'] + 1
            yield Request(review_url(response.meta['review_sku'], response.meta['review_n']),
                    meta=response.meta, callback=self.parse_review)

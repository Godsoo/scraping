import urllib
import logging
import re
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from keteritems import KeterMeta, Review

def function_Z(CM):
    """
    Reimplementation of JS-based hash function for review URLs
    function
    Z(CM){var CL=0;var CK;for(CK=0;CK<CM.length;CK++){var
    CJ=CM.charCodeAt(CK);CJ=CJ*Math.abs(255-CJ);CL+=CJ;}CL=CL%1023;CL=CL+"";var
    CN=4;var
    CI=CL.split("");for(CK=0;CK<CN-CL.length;CK++){CI.unshift("0");}CL=CI.join("");CL=CL.substring(0,CN/2)+"/"+CL.substring(CN/2,CN);return
    CL;}
    """

    CL = 0
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
    # http://www.hayneedle.com/js/pwr/content/00/99/KNA017-en_US-2-reviews.js
    return 'http://www.hayneedle.com/js/pwr/content/%s/%s-en_US-%d-reviews.js' % (
        function_Z(product), product, page)

def load_js_objects(data):
    """
    Loads JS objects (not the same as JSON)
    """
    class VarToStr:
        def __getitem__(self, name):
            return name
    return eval(data, {}, VarToStr())

# TODO: Get rid of even more parameters
# urllib.quote('''{"Brand":[],"Customer Reviews":["5 Stars - Highest Rated;productreviewavg^~5,*$;9;customerreviews_5stars-highestrated;unchecked","4 - 5 Stars;productreviewavg^~4,5$;7;customerreviews_4-5stars;unchecked","3 - 4 Stars;productreviewavg^~3,4$;2;customerreviews_3-4stars;unchecked","1 - 2 Stars;productreviewavg^~1,2$;2;customerreviews_1-2stars;unchecked"],"Price":["Under $30;price^~*,30$;71;price_underd30;unchecked","$30-$80;price^~30,80$;80;price_d30-d80;unchecked","$80-$200;price^~80,200$;76;price_d80-d200;unchecked","$200-$500;price^~200,500$;87;price_d200-d500;unchecked","$500 and up;price^~500,*$;40;price_d500andup;unchecked"],"More":[],"Narrow By":[]}''')
json_search_params = '%7B%22Brand%22%3A%5B%5D%2C%22Customer%20Reviews%22%3A%5B%225%20Stars%20-%20Highest%20Rated%3Bproductreviewavg%5E%7E5%2C%2A%24%3B9%3Bcustomerreviews_5stars-highestrated%3Bunchecked%22%2C%224%20-%205%20Stars%3Bproductreviewavg%5E%7E4%2C5%24%3B7%3Bcustomerreviews_4-5stars%3Bunchecked%22%2C%223%20-%204%20Stars%3Bproductreviewavg%5E%7E3%2C4%24%3B2%3Bcustomerreviews_3-4stars%3Bunchecked%22%2C%221%20-%202%20Stars%3Bproductreviewavg%5E%7E1%2C2%24%3B2%3Bcustomerreviews_1-2stars%3Bunchecked%22%5D%2C%22Price%22%3A%5B%22Under%20%2430%3Bprice%5E%7E%2A%2C30%24%3B71%3Bprice_underd30%3Bunchecked%22%2C%22%2430-%2480%3Bprice%5E%7E30%2C80%24%3B80%3Bprice_d30-d80%3Bunchecked%22%2C%22%2480-%24200%3Bprice%5E%7E80%2C200%24%3B76%3Bprice_d80-d200%3Bunchecked%22%2C%22%24200-%24500%3Bprice%5E%7E200%2C500%24%3B87%3Bprice_d200-d500%3Bunchecked%22%2C%22%24500%20and%20up%3Bprice%5E%7E500%2C%2A%24%3B40%3Bprice_d500andup%3Bunchecked%22%5D%2C%22More%22%3A%5B%5D%2C%22Narrow%20By%22%3A%5B%5D%7D'

class HayneedleComSpider(BaseSpider):
    name = 'hayneedle.com'
    allowed_domains = ['hayneedle.com']
    user_agent = 'Googlebot/2.1 (+http://www.google.com/bot.html)'

    def start_requests(self):
        search_url = 'http://search.hayneedle.com/search/index.cfm?Ntt=%s&x=0&y=0&se=sa'
        for brand in ('Keter', 'SUNCAST', 'RUBBERMAID', 'LIFETIME', 'STEP 2', 'STERILITE'):
            yield Request(search_url % urllib.quote_plus(brand.lower()),
                    meta={'brand': brand.lower()},
                    callback=self.parse_search)

        self._search_url = u'http://search.hayneedle.com/shop-redirect.cfm?%s'

        search_defaults = {
            u'ajax': u'dumps_fluid',
            u'function': u'getGcsData',
            u'ipp': u'36',
            u'view': u'36',
            u'startIndex': u'1',
            u'endIndex': u'36',
            u'totalIndex': u'1000',
            u'sortBy': u'preferred',
            u'clickedFacets': u'',
            u'gcsRestrict': u'',
            u'altnavpage': u'false',
            u'CHS': u'',
        }

        brand_profiles = (
            (u'keter', {u'searchTerm': u'keter',
                        u'restrictBy': u'brand^Keter',
                        u'facetId': u'cell_brand_keter'}
             ),
            (u'rubbermaid', {u'searchTerm': u'rubbermaid',
                             u'restrictBy': u'brand^Rubbermaid',
                             u'facetId': u'cell_brand_rubbermaid'}
             ),
            (u'suncast', {u'searchTerm': u'suncast',
                          u'restrictBy': u'brand^Suncast',
                          u'facetId': u'cell_brand_suncast'}
             ),
            (u'lifetime', {u'searchTerm': u'lifetime',
                           u'restrictBy': u'brand^Lifetime',
                           u'facetId': u'cell_brand_lifetime'}
             ),
            (u'sterilite', {u'searchTerm': u'sterilite',
                            u'restrictBy': u'brand^Sterilite',
                            u'facetId': u'cell_brand_sterilite'}
             ),
        )

        for brand, profile in brand_profiles:
            search_params = search_defaults.copy()
            search_params.update(profile)
            yield Request(self._search_url % urllib.urlencode(search_params),
                          meta={'brand': brand.lower(),
                                'search_params': search_params},
                          callback=self.parse_second)

    def parse_search(self, response):
        hxs = HtmlXPathSelector(response)

        # Handle brand page, Keter has one
        cats = hxs.select(u'//div//a[contains(@href,"/brands/")]/@href').extract()
        if cats:
            for url in cats:
                url = urljoin_rfc(get_base_url(response), url)
                yield Request(url, meta=response.meta, callback=self.parse_first)
            return

        for x in self.parse_first(response):
            yield x

    def parse_first(self, response):
        hxs = HtmlXPathSelector(response)
        items = hxs.select(u'//a[contains(@class, "HN_PRL_GItemL")]/@href').extract()
        for item in items:
            yield Request(item, meta=response.meta, callback=self.parse_item)

        next_page = hxs.select(u'//a[contains(@href, "change_page")]').extract()
        if next_page:
            indexes = re.findall(r'\d+', hxs.select(u'//div[@id="product_count"]/text()').extract()[0].strip())
            startIndex = indexes[0]
            lastIndex = indexes[1]
            totalIndex = indexes[2]
            if int(lastIndex) < int(totalIndex):
                search_params = response.meta.get('search_params')
                if not search_params:
                    url = ('http://search.hayneedle.com/shop-redirect.cfm?ajax=dumps_fluid&function=getGcsData&searchTerm=%s'
                           '&ipp=36&view=36&startIndex=%d&endIndex=36&totalIndex=%d&sortBy=preferred&clickedFacets=&gcsRestrict='
                           '&altnavpage=false&CHS=')\
                    % (response.meta['brand'].lower(), int(startIndex) + 36, int(totalIndex))
                else:
                    search_params[u'startIndex'] = int(startIndex) + 36
                    url = self._search_url % urllib.urlencode(search_params)

                yield Request(url, meta=response.meta, callback=self.parse_second)

    def parse_second(self, response):
        """
        Called when navigating to the next search result page.
        This handles json(?) response and turns it into
        regular html response that can be handled by parse()
        to avoid duplication of fragile pagination code
        """
        try:
            body = json.loads(response.body)
        except:
            logging.error('Failed to parse: ' + repr(response.body))

        # Emulate "normal" HTML response
        body = ('<html><body>%s' +
                '%s' +
                '<div id="dump_paging"><a href=""><span>NEXT</span></a></div></body></html>') % (body[9], body[2])

        response2 = HtmlResponse(url=response.url, body=str(body.encode('utf-8')))
        response2.request = response.request
        for x in self.parse_first(response2):
            yield x

    def parse_item(self, response):
        hxs = HtmlXPathSelector(response)

        # Ensure the search matched brand, not some part of name or description
        brand = hxs.select(u'//div/div/p/b[contains(text(),"Brand")]/../../../div[2]/p/text()').extract()
        brand = brand and brand[0].strip().lower()

        # XXX No brand field for some suncast products, but they have brand in name
        if not brand:
            logging.warning('Brand not found [%s]' % response.url)
            brand = ''
            name = hxs.select(u'//h1/text()').extract()[0].strip()
            if response.meta['brand'].lower() in name.lower():
                logging.warning('Assume [%s] from name' % response.meta['brand'])
                brand = response.meta['brand'].lower()

        if 'keter' in brand.lower():
            brand = 'keter'

        if response.meta['brand'].lower() != brand:
            logging.warning('Brand [%s] not equal to search result brand [%s] [%s]' % (
                        response.meta['brand'], brand, response.url))
            return

        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_xpath('name', u'//h1/text()')
        sku = hxs.select(u'//meta[@property="eb:id"]/@content').extract()[0]
        product_loader.add_value('sku', sku)
        product_loader.add_value('identifier', sku)

        price = hxs.select('//span[@class="ppPrice"]/text()').extract()[0]
        price += hxs.select('//span[@class="ppPrice"]/span/text()').extract()[0]
        product_loader.add_value('price', price)
        product_loader.add_value('brand', brand.lower())
        product_loader.add_xpath('image_url', '//*[@id="jqzoom"]/@href')
        product_loader.add_value('url', response.url)
        product = product_loader.load_item()

        metadata = KeterMeta()
        metadata['brand'] = brand
        metadata['reviews'] = []
        product['metadata'] = metadata
        response.meta['product'] = product

        n_reviews = hxs.select(u'//div[@class="prSnippetReadReviews"]/a/text()').extract()

        if n_reviews:
            n_reviews = int(n_reviews[0].split()[1])
            review_sku = hxs.select(u'//div[@id="HN_PP"]/@ppskunum').extract()[0]
            # 5 reviews per page
            pages = n_reviews / 5
            if n_reviews % 5 > 0:
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
            header = r['h']
            pros = cons = best_uses = []
            for short in r.get('g', []):
                k = short['k']
                if k == 'cons':
                    cons = short['v']
                elif k == 'pros':
                    pros = short['v']
                elif k == 'bestuses':
                    bestuses = short['v']

            bottom = {"yes":"Yes, I would recommend this to a friend",
                "no":"No, I would not recommend this to a friend"}
            try: bottom_line = bottom[r['b']['k'].lower()]
            except: bottom_line = ''

            review['full_text'] = u'%s\n%s\nBottom Line: %s\nPros: %s\nCons: %s\nBest Uses: %s\n' % (
                    header, comments, bottom_line, u', '.join(pros), u', '.join(cons), u', '.join(best_uses))

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

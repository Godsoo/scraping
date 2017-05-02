import re
import urllib
import logging
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from keteritems import KeterMeta, Review, ReviewLoader
import urlparse

from phantomjs import PhantomJS

class CanadiantireCaSpider(BaseSpider):
    name = 'canadiantire.ca'
    allowed_domains = ['canadiantire.ca', 'bazaarvoice.com']
    user_agent = 'Googlebot/2.1 (+http://www.google.com/bot.html)'

    def start_requests(self):
        search_url = 'http://www.canadiantire.ca/en/search-results.html?count=16&searchByTerm=true&viewMode=grid&q=%(brand)s'
        for brand in ('Keter', 'Suncast', 'Rubbermaid', 'Lifetime', 'Step 2', 'Step2', 'Sterilite'):
            yield Request(search_url % {'brand': urllib.quote(brand)},
                    meta={'brand': brand}, callback=self.parse_product_list)

    # This search by brand skips valid products, suck
    def parse_search(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        brands = hxs.select(u'//h1[@class="ls-menu-block__header" and contains(text(), "Brand")]'
                            u'/following-sibling::ul[@class="ls-menu-block__list"]/li')
        for brand in brands:
            brand_name = brand.select(u'./a/text()').extract()
            if brand_name[0].lower().startswith(response.meta['brand'].lower()):
                yield Request(urljoin_rfc(base_url, brand.select(u'./a/@href').extract()[0]),
                              meta=response.meta, callback=self.parse_product_list)
        if not brands:
            for x in self.parse_product_list(response):
                yield x

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        links = hxs.select(u'//h2/a/@href').extract()
        for url in links:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, meta=response.meta, callback=self.parse_product)

        pages = hxs.select('//li[@class="pagination"]//a/@href').extract()
        if pages:
            # next_page = int(re.search(u'page=(\d+)', response.url).group(1)) + 1
            # url = re.sub(u'page=(\d+)', 'page=' + str(next_page), response.url)
            for page_url in pages:
                yield Request(urljoin_rfc(base_url, page_url),
                              meta=response.meta,
                              callback=self.parse_product_list)

    def parse_product(self, response):
        browser = PhantomJS()
        self.log('>>> BROWSER: GET => %s' % response.url)
        browser.get(response.url)
        self.log('>>> BROWSER: OK!')

        hxs = HtmlXPathSelector(text=browser.driver.page_source)

        browser.close()
        self.log('>>> BROWSER: Closed')

        sku = hxs.select(u'//*[@class="displaySkuCode"]//text()').extract()

        sku = sku[0].replace('#', '')

        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_xpath('name', u'//div[contains(@class,"title")]//h1/text()')
        product_loader.add_value('sku', sku)
        product_loader.add_xpath('category', u'//ul[contains(@class, "pd-breadcrumbs")]/li[2]/a/text()')
        product_loader.add_value('identifier', sku)
        price = hxs.select(u'//div[contains(@class, "product-price__reg-price")]/text()').extract()
        product_loader.add_value('price', price[0].replace('Reg.', ''))
        product_loader.add_value('brand', response.meta['brand'].lower())
        product_loader.add_value('url', response.url)
        image_url = hxs.select(u'/html/head/link[@rel="image_src"]/@href').extract()
        if image_url:
            product_loader.add_value('image_url', image_url[0])
        product = product_loader.load_item()

        metadata = KeterMeta()
        metadata['brand'] = response.meta['brand']
        metadata['reviews'] = []
        product['metadata'] = metadata
        response.meta['product'] = product

        brand = response.meta['brand'].lower()
        if brand not in product['name'] and brand not in response.body.lower():
            return

        # http://www.canadiantire.ca/AST/browse/2/OutdoorLiving/3/OutdoorStorage/Sheds/PRD~0600292P/Keter+Rattan+Vertical+Shed.jsp?locale=en
        # http://canadiantire.ugc.bazaarvoice.com/9045/0600292P/reviews.djs?format=embeddedhtml
        # <script language="JavaScript" src="http://canadiantire.ugc.bazaarvoice.com/static/9045/bvapi.js" type="text/javascript"></script>
        part1 = hxs.select(u'//script[starts-with(@src,"http://canadiantire.ugc.bazaarvoice.com/static/")]/@src').extract()[0].split('/')[-2]
        part2 = hxs.select('//div[@id="bazaarVoiceConfig"]/@data-product-code').extract()[0]

        yield Request('http://canadiantire.ugc.bazaarvoice.com/%s/%s/reviews.djs?format=embeddedhtml' % (part1, part2),
                meta=response.meta, callback=self.parse_review_js)

    def parse_review_js(self, response):
        for line in response.body.split('\n'):
            if line.startswith('var materials='):
                body = line.lstrip('var materials=').rstrip(',')
                break

        try:
            body = eval(body)
        except:
            logging.error('Failed to parse: ' + repr(response.body))

        # Emulate "normal" HTML response
        body = ('<html><body>' +
                '%s' +
                '</body></html>') % (body['BVRRSourceID'].replace('\\/', '/'))

        response2 = HtmlResponse(url=response.url, body=body)
        response2.request = response.request

        for x in self.parse_review(response2):
            yield x

    def parse_review(self, response):
        hxs = HtmlXPathSelector(response)
        product = response.meta['product']

        for review in hxs.select(u'//div[starts-with(@id, "BVRRDisplayContentReviewID_")]'):
            review_loader = ReviewLoader(item=Review(), selector=review, date_format="%B %d, %Y")
            review_loader.add_value('date', review.select(u'.//span[contains(@class,"BVRRReviewDate")]/text()').extract()[1])

            title = review.select(u'.//span[contains(@class,"BVRRCustomFullTitle")]/text()').extract()
            text = ' '.join(review.select(u'.//span[contains(@class,"BVRRReviewText")]/text()').extract())

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
            rating = review.select(u'.//img[@class="BVImgOrSprite"]/@title').extract()[0]
            review_loader.add_value('rating', rating.split()[0])
            review_loader.add_value('url', response.url)

            product['metadata']['reviews'].append(review_loader.load_item())

        next_url = hxs.select(u'//a[contains(@name,"BV_TrackingTag_Review_Display_NextPage")]/@data-bvjsref').extract()
        if next_url:
            yield Request(next_url[0],
                    meta=response.meta, callback=self.parse_review_js)

        else:
            yield product

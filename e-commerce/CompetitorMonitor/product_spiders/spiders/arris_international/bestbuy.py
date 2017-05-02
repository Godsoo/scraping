'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5555
'''

import demjson
import re
from datetime import datetime


import pandas as pd
from urllib import quote

from scrapy.spiders import Spider
from scrapy.selector import HtmlXPathSelector, Selector
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter, url_query_parameter
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from scrapy.http import Request
from arrisitems import *

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from scrapy import log



def extract_html(response):
    review_html = ''
    for line in response.body.split('\n'):
        if 'var materials=' in line:
            review_html = line.split('"BVRRSecondaryRatingSummarySourceID":" ')[-1].split('\n}')[0].replace('\\', '')
    return review_html
    
    
class Review(Item):
    date = Field()
    rating = Field()
    full_text = Field()
    url = Field()
    author = Field()
    author_location = Field()


class ReviewLoader(XPathItemLoader):
    date_in = MapCompose(unicode, unicode.strip, extract_date, date_format='%d/%m/%Y')
    date_out = TakeFirst()

    rating_in = MapCompose(unicode, extract_rating)
    rating_out = TakeFirst()

    full_text_in = MapCompose(unicode, unicode.strip, remove_entities, fix_spaces)
    full_text_out = Join(' ')

    url_in = MapCompose(unicode, unicode.strip)
    url_out = TakeFirst()

    author_in = MapCompose(unicode, unicode.strip)
    author_out = TakeFirst()
    
    author_location_in = MapCompose(unicode, unicode.strip)
    author_location_out = TakeFirst()    
    
    
class BestBuySpider(Spider):
    name = 'arris_international-bestbuy.com'
    allowed_domains = ['bestbuy.com', 'bestbuy.ugc.bazaarvoice.com']
    start_urls = ('http://www.bestbuy.com',)
    errors = []

    options_identifiers = []

    keywords = ('surfboard SB6141',
                'surfboard SB6183',
                'surfboard SB6190',
                'surfboard SBG6400',
                'surfboard SBG6580',
                'surfboard SBG6700',
                'surfboard SBG6900',
                'surfboard SBG7580',
                'surfboard SBR AC1200P',
                'surfboard SBR AC1900P',
                'surfboard SBR AC3200P',
                'surfboard SBX AC1200P',
                'surfboard SBX 1000P')
    
    def __init__(self, *args, **kwargs):
        super(BestBuySpider, self).__init__(*args, **kwargs)

        dispatcher.connect(self.spider_idle, signals.spider_idle)

        self.new_ids = []

        self.try_deletions = False

    def _get_prev_crawl_filename(self):
        filename = None
        if hasattr(self, 'prev_crawl_id'):
            filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
        return filename

    def spider_idle(self, spider):
        if self.try_deletions:
            self.try_deletions = False

            filename = self._get_prev_crawl_filename()
            if filename and os.path.exists(filename):
                old_products = pd.read_csv(filename, dtype=pd.np.str)
                deletions = old_products[old_products.isin(self.new_ids) == False]
                log.msg('INFO >>> Retry product deletions')
                for url in deletions['url']:
                    request = Request(url, callback=self.parse_product)
                    self._crawler.engine.crawl(request, self)

    def start_requests(self):
        for keyword in self.keywords:
            search_url = 'http://www.bestbuy.com/site/searchpage.jsp?st=%s&_dyncharset=UTF-8&id=pcat17071&type=page&sc=Global&cp=1&nrp=&sp=&qp=soldby_facet=Sold By~Best Buy^condition_facet=Condition~New&list=n&iht=y&usc=All+Categories&ks=960&keys=keys' % quote(keyword)
            yield Request(search_url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = response.css('div.list-items h4 a::attr(href)').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

        nextp = hxs.select('//li[@class="pager-next"]/a/@href').extract()
        if nextp:
            current_page = int(url_query_parameter(response.url, 'cp', '0')) + 1
            next_page = add_or_replace_parameter(response.url, 'cp', str(current_page))
            yield Request(urljoin_rfc(base_url, next_page))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        options = hxs.select('//div[@class="variation-group"]//a/@href').extract()
        for option in options:
            option_url = urljoin_rfc(base_url, option)
            log.msg('INFO >>> OPTION FOUND: ' + option_url)
            yield Request(option_url, callback=self.parse_product)

        one_seller = hxs.select('//div[@class="marketplace-shipping-message"]//a[@class="bbypopup"]').extract()
        one_seller = True if one_seller else False

        identifier = hxs.select('//span[@itemprop="productID"]/text()').extract()

        if not identifier:
            request = self.retry(response, "ERROR >>> No identifier for product URL: " + response.url)
            if request:
                yield request
            return

        identifier = identifier[0]

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        price = ''.join(hxs.select('//div[@class="item-price"]/text()').extract()).strip()
        loader.add_value('price', price)
        loader.add_xpath('name', '//div[@itemprop="name"]/h1/text()')
        image_url = hxs.select('//meta[@property="og:image"]/@content').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])

        categories = response.xpath('//ol[@id="breadcrumb-list"]/li/a/text()').extract()[-3:]
        loader.add_value('category', categories)

        brand = hxs.select('//div[@itemprop="brand"]/meta[@itemprop="name"]/@content').extract()
        brand = brand[0].strip() if brand else ''
        loader.add_value('brand', 'Surfboard')

        sku = hxs.select('//span[@itemprop="model"]/text()').extract()
        sku = sku[0] if sku else ''
        loader.add_value('sku', sku)

        out_of_stock = hxs.select('//div[@class="cart-button" and @data-button-state-id="SOLD_OUT_ONLINE"]')

        item = loader.load_item()
        item['metadata'] = {'reviews': []}

        reviews_url = 'http://bestbuy.ugc.bazaarvoice.com/3545w/%s/reviews.djs?format=embeddedhtml'
        yield Request(reviews_url % identifier, meta={'product': item}, callback=self.parse_review_page)

    def parse_review_page(self, response):
        item_ = response.meta.get('product', '')
        review_selector = Selector(text=extract_html(response))
        reviews = review_selector.xpath('//div[@class="BVRRReviewDisplayStyle5"]')
        for review in reviews:
            l = ReviewLoader(item=Review(), response=response, date_format='%m/%d/%Y')
            rating = review.select(".//span[contains(@class,'BVRRRatingNumber')]/text()").extract()[0]
            date = review.select(".//span[contains(@class,'BVRRValue BVRRReviewDate')]/text()").extract()[0]
            review_text = review.select(".//span[contains(@class,'BVRRReviewText')]/text()").extract()
            location = review.css('span.BVRRValue.BVRRUserLocation::text').extract_first()
            author = review.css('span.BVRRNickname::text').extract_first()

            l.add_value('rating', rating)
            l.add_value('url', response.url)
            l.add_value('date', datetime.strptime(date, '%B %d, %Y').strftime('%m/%d/%Y'))
            l.add_value('full_text', review_text)
            l.add_value('author', author)
            l.add_value('author_location', location)
            item_['metadata']['reviews'].append(l.load_item())

        nextp = review_selector.css('span.BVRRPageLink.BVRRNextPage a::attr(data-bvjsref)').extract_first()
        if nextp:
            yield Request(nextp, callback=self.parse_review_page, meta={'product': item_})
        else:
            yield item_

    def parse_warranty_price(self, response):
        dealers_url = response.url.partition(';')[0] + ';template=_buyingOptionsNewTab'
        yield Request(dealers_url, callback=self.parse_dealers, meta=response.meta)

    def parse_dealers(self, response):
        item = response.meta['item']

        try:
            hxs = HtmlXPathSelector(response)
            dealers = hxs.select('//div[@class="product-list" and @data-condition="new"]')
        except Exception:
            dealers = []

        if not dealers and response.meta['one_seller']:
            log.msg('ERROR >>> ONE SELLER: ' + item['url'])
            return

        for dealer in dealers:
            dealer_name = ''.join(dealer.select('.//div[@class="seller-name"]/span/text()').extract()).strip()
            if dealer_name.upper() == 'BEST BUY':
                log.msg('INFO >>> COLLECT BEST BUY ITEM: ' + item['url'])

                out_of_stock = dealer.select('.//div[@class="cart-button" and @data-button-state-id="SOLD_OUT_ONLINE"]')
                if out_of_stock:
                    item['stock'] = 0

                price = dealer.select('.//div[@class="medium-item-price"]//text()').extract()
                if not price:
                    log.msg('ADD TO CART PRICE >>> ' + item['url'])
                    price = dealer.select('@data-price').extract()
                item['price'] = extract_price(price[-1])
                shipping_cost = dealer.select('.//div[@class="shipping-cost-puck"]//text()').extract()
                if shipping_cost:
                    item['shipping_cost'] = extract_price(shipping_cost[0])
                break

        if item['identifier']:
            self.new_ids.append(item['identifier'])
            yield item

    def retry(self, response, error="", retries=3):
        meta = response.meta.copy()
        retry = int(meta.get('retry', 0))
        if 'redirect_urls' in meta and meta['redirect_urls']:
            url = meta['redirect_urls']
        else:
            url = response.request.url
        if retry < retries:
            log.msg(error)
            retry += 1
            meta['retry'] = retry
            meta['recache'] = True
            return Request(url, dont_filter=True, meta=meta, callback=response.request.callback)
                
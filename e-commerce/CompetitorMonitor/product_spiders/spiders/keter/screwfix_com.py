import urllib
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from keteritems import KeterMeta, Review, ReviewLoader


class ScrewfixComSpider(BaseSpider):
    name = 'screwfix.com'
    allowed_domains = ['screwfix.com']
    user_agent = 'Googlebot/2.1 (+http://www.google.com/bot.html)'
    start_urls = ('http://www.screwfix.com',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//a/@href').extract():
            if 'forceUserMode=UK' in url:
                url = urljoin_rfc(get_base_url(response), url)
                yield Request(url, callback=self.start_search)
                return
        self.log('Force user mode = UK not found!')
        for x in self.start_search(response):
            yield x

    def start_search(self, response):
        search_url = 'http://www.screwfix.com/search.do?fh_search='
        # The site search engine is bad. We need search by keter term
        # followed by another thing so we get all products of keter brand (??)
        # This may be temporary
        for brand in ('Keter', 'Keter plastic', 'SUNCAST', 'RUBBERMAID', 'LIFETIME', 'STEP 2', 'STERILITE'):
            yield Request(search_url + urllib.quote_plus(brand),
                          meta={'brand': brand.replace('Keter plastic', 'Keter')},
                          callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        links = hxs.select(u'//div[@class="gallery-product-title"]/h2/a/@href').extract()
        for url in links:
            yield Request(url, meta=response.meta, callback=self.parse_product)

        next_page = hxs.select('//*[@id="next_page_link"]/@href').extract()
        if next_page:
            yield Request(next_page[0], meta=response.meta, callback=self.parse_product_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        product_loader = ProductLoader(item=Product(), response=response)
        name = hxs.select(u'//h1/text()').extract()[0]
        attrs = hxs.select(u'//td[starts-with(@id,"product_selling_attribute_value_")]/text()').extract()
        if [a for a in attrs if response.meta['brand'].lower() in a.lower()]:
            # got brand match
            pass
        elif not response.meta['brand'].lower() in name.lower():
            return
        product_loader.add_value('name', name)
        product_loader.add_xpath('sku', u'//span[@itemprop="productID"]/text()')
        product_loader.add_xpath('identifier', u'//span[@itemprop="productID"]/text()')
        product_loader.add_xpath('image_url', '//*[@id="product_image"]/@src')
        product_loader.add_xpath('category', '//*[@id="breadcrumb_item_cat_top_1"]/text()')

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
            loader.add_xpath('date', u'.//span[contains(@class,"BVRRReviewDate") and position()=1]/text()')
            loader.add_value('rating', r.select(u'.//div[@class="BVRRRatingNormalImage"]/img/@title').extract()[0].split()[0])
            loader.add_value('url', response.url)
            product['metadata']['reviews'].append(loader.load_item())

        next_url = hxs.select(u'//span[contains(@class,"BVRRNextPage")]/a/@href').extract()
        if next_url:
            yield Request(next_url[0], meta=response.meta, callback=self.parse_review)
        else:
            yield product
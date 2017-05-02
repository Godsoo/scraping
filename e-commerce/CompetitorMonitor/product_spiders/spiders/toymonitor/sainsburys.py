'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5312
'''

from datetime import datetime
from w3lib.url import url_query_cleaner

from scrapy.spider import CrawlSpider, Rule
from scrapy.selector import Selector
from scrapy.linkextractor import LinkExtractor
from scrapy.http import Request

from product_spiders.items import ProductLoaderWithoutSpaces as ProductLoader, Product
from product_spiders.phantomjs import PhantomJS

from toymonitoritems import ToyMonitorMeta, Review, ReviewLoader


class Sainsburys(CrawlSpider):
    name = 'toymonitor-sainsburys'
    allowed_domains = ['sainsburys.co.uk',
                       'sainsburysgrocery.ugc.bazaarvoice.com']
    start_urls = ['http://www.sainsburys.co.uk/shop/gb/groceries/home/all-toys-281914-44']
    
    pages = LinkExtractor(restrict_css='ul.pages')
    products = LinkExtractor(restrict_css='div.product div.productInfo h3')
    
    rules = (Rule(pages, callback='parse_page'),
             Rule(products, callback='parse_product'))
    
    def parse(self, response):
        browser = PhantomJS()
        browser.get(response.url)
        selector = Selector(text=browser.driver.page_source)
        products = selector.css('div.product div.productInfo h3 a::attr(href)').extract()
        for url in products:
            yield Request(url, self.parse_product)
        pages = selector.css('ul.pages a::attr(href)').extract()
        for url in pages:
            yield Request(url)
        browser.close()
        if not (products or pages):
            for request in self.parse(response):
                yield request
        
    def parse_product(self, response):
        loader = ProductLoader(Product(), response=response)
        identifier = response.xpath('//input[@name="productId"]/@value').extract_first()
        if not identifier:
            loader.add_value('stock', 0)
            identifier = response.xpath('//text()').re('productId=(.+?)&')
        loader.add_value('identifier', identifier)
        loader.add_value('url', url_query_cleaner(response.url))
        loader.add_css('name', 'div.productTitleDescriptionContainer h1::text')
        loader.add_css('price', 'p.pricePerUnit::text')
        loader.add_css('sku', 'p.itemCode::text', re='Item code:(.+)')
        category = response.xpath('//ul[@id="breadcrumbNavList"]//a/span/text()').extract()
        if 'Home' in category:
            category.remove('Home')
        loader.add_value('category', category)
        image_url = response.css('img#productImageID::attr(src)').extract_first()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url))
        item = loader.load_item()
        item['metadata'] = {'reviews': []}
            
        review_id = response.xpath('//text()').re_first("productId: '(.+?)'")
        reviews_url = 'http://sainsburysgrocery.ugc.bazaarvoice.com/8076-en_gb/%s/reviews.djs?format=embeddedhtml' %review_id
        yield Request(reviews_url, 
                      callback=self.parse_review_page, 
                      meta={'item': item})

    def parse_review_page(self, response):
        item_ = response.meta.get('item', '')
        hxs = Selector(text=self._extract_html(response))
        reviews = hxs.xpath('//div[@class="BVRRReviewDisplayStyle5"]')
        for review in reviews:
            l = ReviewLoader(item=Review(), response=response, date_format='%d/%m/%Y')
            rating = review.select(".//span[contains(@class,'BVRRRatingNumber')]/text()").extract()[0]
            date = review.select(".//span[contains(@class,'BVRRValue BVRRReviewDate')]/text()").extract()[0]
            title = review.select(".//span[contains(@class,'BVRRReviewTitle')]/text()").extract()
            review_text = review.select(".//span[contains(@class,'BVRRReviewText')]/text()").extract()[0]

            if title:
                full_text = title[0].strip() + '\n' + review_text.strip()
            else:
                full_text = review_text.strip()

            l.add_value('rating', rating)
            l.add_value('url', item_['url'])
            l.add_value('date', datetime.strptime(date, '%d %B %Y').strftime('%d/%m/%Y'))
            l.add_value('full_text', full_text)
            item_['metadata']['reviews'].append(l.load_item())

        nextp = hxs.xpath('//span[@class="BVRRPageLink BVRRNextPage"]/a/@data-bvjsref').extract()
        if nextp:
            yield Request(nextp[0], callback=self.parse_review_page, meta={'item': item_})
        else:
            yield item_

    def _extract_html(self, response):
        review_html = ''
        for line in response.body.split('\n'):
            if 'var materials=' in line:
                review_html = line.split('"BVRRSecondaryRatingSummarySourceID":" ')[-1].split('\n}')[0].replace('\\', '')
        return review_html

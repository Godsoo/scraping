"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/5305

Extract all products including product options.
"""
import scrapy
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from toymonitoritems import ToyMonitorMeta, Review, ReviewLoader
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
from HTMLParser import HTMLParser


class DisneystoreSpider(scrapy.Spider):
    name = 'toymonitor-disneystore.co.uk'
    allowed_domains = ['disneystore.co.uk', 'disneystore.ugc.bazaarvoice.com']
    start_urls = ('http://www.disneystore.co.uk/departments', 'http://www.disneystore.co.uk/characters')

    def parse(self, response):
        for url in response.xpath('//div[@class="categoryContainerWrap"]//a/@href').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse_product_list)
        for url in response.xpath('//div[@class="charindex-full-container"]//a/@href').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse_product_list)

    def parse_product_list(self, response):
        for url in response.xpath('//div[@class="pageNavigation"]/a/@href').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse_product_list)
        for url in response.xpath('//div[contains(@class, "productItem")]/a/@href').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse_product)

    def parse_product(self, response):
        variations = None
        if not response.meta.get('no_variations', False):
            variations = response.xpath('//select[@class="variation-select"]/option')
            name_add = ''
        else:
            name_add = response.meta.get('name', '')
        if variations:
            h = HTMLParser()
            for option in variations[1:]:
                name = option.xpath('./text()').extract_first()
                url = option.xpath('./@data-url').extract_first()
                self.log(url)
                url = h.unescape(url)
                meta = {'name': name, 'no_variations': True}
                yield scrapy.Request(url, meta=meta, callback=self.parse_product)
        else:
            identifier = response.xpath('//*[@id="pid"]/@value').extract_first()
            identifier2 = response.xpath('//*[@id="pid"]/@data-variant-id').extract_first()
            if identifier != identifier2:
                identifier += '_' + identifier2
            stock = response.xpath('//span[@class="in-stock-msg information"]').extract_first()
            name = response.xpath('//h1[@itemprop="name"]/text()').extract_first()
            if name_add != '':
                if '(Out of stock)' in name_add:
                    name_add = name_add.replace('(Out of stock)', '')
                    stock = None
                name += ' ' + name_add
            price = response.xpath('//span[@itemprop="price"]/text()').extract_first()
            if not price:
                price = 0
                stock = None
            category = response.xpath('//div[@class="breadcrumbs"]/a/text()').extract()
            image_url = response.xpath('//img[@itemprop="image"]/@src').extract_first()

            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', name)
            loader.add_value('identifier', identifier)
            loader.add_value('sku', identifier)
            loader.add_value('brand', 'Disney')
            loader.add_value('category', category)
            loader.add_value('url', response.url)
            loader.add_value('image_url', response.urljoin(image_url))
            loader.add_value('price', price)
            if not stock:
                loader.add_value('stock', 0)
            if loader.get_output_value('price') < 50:
                loader.add_value('shipping_cost', '3.95')

            product = loader.load_item()

            metadata = ToyMonitorMeta()
            metadata['reviews'] = []
            product['metadata'] = metadata

            reviews_url = 'http://disneystore.ugc.bazaarvoice.com/4848-en_gb/%s/reviews.djs?format=embeddedhtml&page=1&scrollToTop=true'
            yield scrapy.Request(reviews_url % product['identifier'], callback=self.parse_review_page, meta={'item': product})

    def parse_review_page(self, response):
        item_ = response.meta.get('item', '')
        hxs = HtmlXPathSelector(text=self._extract_html(response))
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

        next_ = hxs.xpath('//span[@class="BVRRPageLink BVRRNextPage"]/a/@data-bvjsref').extract()
        if next_:
            yield scrapy.Request(next_[0], callback=self.parse_review_page, meta={'item': item_})
        else:
            yield item_

    @staticmethod
    def _extract_html(response):
        review_html = ''
        for line in response.body.split('\n'):
            if 'var materials=' in line:
                review_html = line.split('"BVRRSecondaryRatingSummarySourceID":" ')[-1].split('\n}')[0].replace('\\',
                                                                                                                '')
        return review_html
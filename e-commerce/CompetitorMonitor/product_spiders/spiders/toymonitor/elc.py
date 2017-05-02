"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/5304

Extract all products including product options.
"""
import scrapy
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from toymonitoritems import ToyMonitorMeta, Review, ReviewLoader
from datetime import datetime


class ElcSpider(scrapy.Spider):
    name = 'toymonitor-elc.co.uk'
    allowed_domains = ['elc.co.uk', 'mark.reevoo.com']
    start_urls = ('http://www.elc.co.uk/',)

    def parse(self, response):
        for url in response.xpath('//*[@id="navigation"]/ul/li/a/@href').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse_categories)

    def parse_categories(self, response):
        for url in response.xpath('//*[@id="category-level-2"]/li/a/@href').extract():
            yield scrapy.Request(response.urljoin(url + '?sz=90'), callback=self.parse_product_list)

    def parse_product_list(self, response):
        for url in response.xpath('//ul[@class="b-pagination"]//a/@href').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse_product_list)
        for url in response.xpath('//div[@class="b-product_title"]/a/@href').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse_product)

    def parse_product(self, response):
        identifier = response.xpath('//*[@id="pid"]/@value').extract_first()
        name = response.xpath('//*[@id="product-name"]/@value').extract_first()
        price = response.xpath('//meta[@itemprop="price"]/@content').extract_first()
        category = response.xpath('//ul[@class="b-breadcrumbs-list"]//a/text()').extract()[1:]
        image_url = response.xpath('//div[@class="b-product_details-print_image"]/img/@src').extract_first()
        brand = response.xpath('//span[@class="b-brand_title"]/text()').extract_first()
        stock = response.xpath('//span[@class="m-in_stock js-availability_msg"]/text()').extract_first()
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', name)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('brand', brand)
        loader.add_value('category', category)
        loader.add_value('url', response.url)
        loader.add_value('image_url', response.urljoin(image_url))
        loader.add_value('price', price)
        if not stock:
            loader.add_value('stock', 0)
        if loader.get_output_value('price') < 40:
            loader.add_value('shipping_cost', '3.95')

        product = loader.load_item()

        metadata = ToyMonitorMeta()
        metadata['reviews'] = []
        product['metadata'] = metadata

        reviews_url = 'http://mark.reevoo.com/reevoomark/en-GB/product.html?page=1&sku=%s&tab=reviews&trkref=MLC'
        meta = {'dont_retry': True,
                'handle_httpstatus_list': [404, 302],
                'product': product}
        yield scrapy.Request(reviews_url % identifier, callback=self.parse_review_page, meta=meta)

    def parse_review_page(self, response):
        item_ = response.meta.get('product', '')

        if response.status != 200:
            yield item_
            return

        rating_mapping = {'1': '1', '2': '1', '3': '2', '4': '2', '5': '3',
                          '6': '3', '7': '4', '8': '4', '9': '5', '10': '5'}

        reviews = response.xpath('//article[contains(@id, "review_")]')
        for review in reviews:
            l = ReviewLoader(item=Review(), response=response, date_format='%d/%m/%Y')
            rating = ''.join(review.xpath('.//div[@class="overall_score_stars"]/@title').extract())
            date = review.xpath('.//section[@class="purchase_date"]/span/text()').extract()
            if not date:
                date = review.xpath('.//p[@class="purchase_date"]/span/text()').extract()
            date = date[0].strip() if date else ''
            review_pros = ''.join(
                review.xpath('.//section[@class="review-content"]//dd[@class="pros"]//text()').extract()).strip()
            if review_pros != '':
                review_pros = 'Pro: ' + review_pros
            review_cons = ''.join(
                review.xpath('.//section[@class="review-content"]//dd[@class="cons"]//text()').extract()).strip()
            if review_cons != '':
                review_cons = 'Cons: ' + review_cons
            if review_cons == '' and review_pros == '':
                review = 'Reviewer left no comment'
            else:
                review = review_pros + ' ' + review_cons

            l.add_value('rating', rating_mapping[rating])
            l.add_value('url', response.url)
            l.add_value('date', datetime.strptime(date, '%d %B %Y').strftime('%d/%m/%Y'))
            l.add_value('full_text', review)
            item_['metadata']['reviews'].append(l.load_item())

        next_ = response.xpath('//a[@class="next_page"]/@href').extract()

        if next_:
            meta = {'dont_retry': True,
                    'handle_httpstatus_list': [404, 302],
                    'product': item_}
            yield scrapy.Request(response.urljoin(next_[0]), callback=self.parse_review_page, meta=meta)
        else:
            yield item_
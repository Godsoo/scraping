import os
import re
import logging
from datetime import datetime

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from demoritems import DemoRMeta, Review, ReviewLoader

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import demjson

HERE = os.path.abspath(os.path.dirname(__file__))

class DebenhamsSpider(BaseSpider):
    name = 'demo_r-debenhams.com'
    allowed_domains = ['debenhams.com', 'debenhamsplus.com', 'debenhams.ugc.bazaarvoice.com']
    start_urls = [
        'http://www.debenhams.com',
    ]

    user_agent = 'spd'

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        categories = response.xpath('//li[div[contains(text(), "Audio, vision & technology")]]//a/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category))

        categories = response.xpath('//div[@id="subCategorycategories"]/ul/li/a/@href').extract()
        categories += response.xpath('//li[@id="categories"]/ul/li/a/@href').extract()
        categories += response.xpath('//div[@class="cat_detail"]/div/a/@href').extract()
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category)
            yield Request(url)

        # products new parse method
        products = response.xpath('//div[contains(@id, "PSPProductList")]')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)

            name = "".join(product.xpath(".//div[contains(@class, 'product_name')]//text()").extract()).strip()
            brand = product.xpath('div/a/div[@class="brand_name"]/text()').extract()[0].strip()

            url = product.xpath(".//a/@href").extract()
            url = urljoin_rfc(get_base_url(response), url[0])

            sku = product.xpath(".//div[contains(@id, 'psp')]/@id").re("psp_(.+)")[0]

            price = product.xpath(".//span[@class='price_now']/text()").re(u'Now\xa0\xa3(.*)')
            if not price:
                price = product.xpath(".//span[@class='price-actual' and @itemprop='price']/text()").extract()

            if price:
                price = price[0]
            else:
                price = ''
                loader.add_value('stock', 0)

            category = response.xpath('//div[@id="box_productSelectionPage"]/div/h1/text()').extract()
            category = category[0].strip() if category else ''

            loader.add_value('name', name)
            loader.add_value('brand', brand)
#            loader.add_value('category', category)
            loader.add_value('url', url)
            loader.add_xpath('image_url', 'div//img[@class="proImg"]/@src')
            loader.add_value('sku', sku)
            loader.add_value('identifier', sku)
            loader.add_value('price', price)


            item = loader.load_item()
            metadata = DemoRMeta()
            metadata['reviews'] = []
            metadata['promotion'] = ''.join(product.xpath('.//span[@class="discount_savings"]/text()').extract())
            item = loader.load_item()
            item['metadata'] = metadata

            yield Request(item['url'], meta={'item':item}, callback=self.parse_product)

        for page in response.xpath('//div[@id="pagination"]/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), page)
            yield Request(url)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        item = response.meta['item']

        item['category'] = ' > '.join([x.strip() for x in response.xpath('//div[@class="breadcrumb_links"]//a/text()').extract()])

        # stock
        stock_data = response.xpath('//div[contains(@id, "entitledItem_")]/text()').extract()
        if stock_data:
            data = demjson.decode(stock_data[0])
            if data:
                stock = data[0]['inventory_stock']
                try:
                    if float(stock):
                        #item['stock'] = 1
                        pass
                    else:
                        item['stock'] = 0
                except ValueError:
                    item['stock'] = 0

        reviews_url = 'http://debenhams.ugc.bazaarvoice.com/9364redes-en_gb/%s/reviews.djs?format=embeddedhtml&scrollToTop=true'
        part_number = response.url.split('_')[-2]
        yield Request(reviews_url % part_number, callback=self.parse_review_page, meta={'product': item})

    def parse_review_page(self, response):
        item_ = response.meta.get('product', '')
        hxs = HtmlXPathSelector(text=self._extract_html(response))
        reviews = response.xpath('//div[@class="BVRRReviewDisplayStyle5"]')
        for review in reviews:
            l = ReviewLoader(item=Review(), response=response, date_format='%m/%d/%Y')
            rating = review.select(".//span[contains(@class,'BVRRRatingNumber')]/text()").extract()[0]
            date = review.select(".//span[contains(@class,'BVRRValue BVRRReviewDate')]/text()").extract()[0]
            review = review.select(".//span[contains(@class,'BVRRReviewText')]/text()")[0].extract()

            l.add_value('rating', rating)
            l.add_value('url', response.url)
            l.add_value('date', datetime.strptime(date, '%d %B %Y').strftime('%m/%d/%Y'))
            l.add_value('full_text', review)
            item_['metadata']['reviews'].append(l.load_item())

        next = response.xpath('//span[@class="BVRRPageLink BVRRNextPage"]/a/@data-bvjsref').extract()
        if next:
            yield Request(next[0], callback=self.parse_review_page, meta={'product': item_})
        else:
            yield item_

    def _extract_html(self, response):
        review_html = ''
        for line in response.body.split('\n'):
            if 'var materials=' in line:
                review_html = line.split('"BVRRSecondaryRatingSummarySourceID":" ')[-1].split('\n}')[0].replace('\\', '')
        return review_html

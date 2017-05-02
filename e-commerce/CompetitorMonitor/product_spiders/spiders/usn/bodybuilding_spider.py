import os
import json
import re
from copy import deepcopy

from scrapy import log

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.base_spiders.primary_spider import PrimarySpider


from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class BodyBuildingSpider(PrimarySpider):
    name = 'usn-bodybuilding.com'
    allowed_domains = ['bodybuilding.com']
    start_urls = ['http://uk.bodybuilding.com']

    csv_file = 'bodybuilding.com_crawl.csv'

    def start_requests(self):
        brands = {'USN': 'http://uk.bodybuilding.com/store/usn.html',
                  'Optimum Nutrition': 'http://uk.bodybuilding.com/store/opt/opt.htm',
                  'BSN': 'http://uk.bodybuilding.com/store/bsn/bio.htm',
                  'PhD': 'http://uk.bodybuilding.com/store/phd/phd.html',
                  'Maxi Nutrition': 'http://uk.bodybuilding.com/store/maxinutrition.html',
                  'Reflex': 'http://uk.bodybuilding.com/store/reflex-nutrition.html',
                  'Mutant': 'http://uk.bodybuilding.com/store/mutant/mutant.html',
                  'Cellucor': 'http://uk.bodybuilding.com/store/cellucor/cellucor.htm',
                  'Sci-MX': 'http://uk.bodybuilding.com/store/sci-mx-nutrition.html'}

        for brand, url in brands.iteritems():
            yield Request(url, meta={'brand': brand})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        products = hxs.select('//div[@class="product-details"]/h3/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product, meta=response.meta)

        next_page = hxs.select('//li[@class="next button"]/a/@href').extract()
        if next_page:
            next_page = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(next_page, callback=self.parse, meta=response.meta)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        name = response.css('h1.fn::text').re('\S+')
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        loader.add_value('brand', response.meta.get('brand', ''))
        categories = hxs.select('//a[@class="bb-crumb__link"]/text()').extract()[3:]
        if not categories:
            categories = hxs.select('//div[@id="breadcrumbs"]//a/text()').extract()[3:]
        loader.add_value('category', categories)
        image_url = hxs.select('//img[@class="Product__img img-responsive"]/@src').extract()
        if not image_url:
            image_url = hxs.select('//img[@class="photo"]/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])

        item = loader.load_item()

        options = response.xpath('//div[@class="SkuList"]/div[contains(@class,"SkuGroup")]')
        if not options:
            options = response.xpath('//div[@id="right-content-prod"]/table[contains(@class, "flavor-table flava-flav")]')
        if options:
            for option in options:
                option_item = deepcopy(item)
                option_name = option.select('.//span[@class="SkuGroup__heading__name"]/text()').extract()
                if not option_name:
                    option_name = option.select('./tr/td/span/text()').extract()
                option_name = option_name[0].strip()
                option_item['name'] += ' ' + option_name
                price = ''.join(option.select('.//span[@class="SkuGroup__sale-price"]/text()').extract()).strip()
                if not price:
                    price = ''.join(option.select('./tr/td[contains(@class, "size-price")]//span[@class="price"]/text()').extract()).strip()
                option_item['price'] = extract_price(price)
                sub_options = option.select('.//tr[td[@class="availability"]]')
                if not sub_options:
                    sub_options = option.select('.//tr[@class="SkuGroup__sku"]')
                if sub_options: 
                    for sub_option in sub_options:
                        sub_item = deepcopy(option_item)
                        identifier = sub_option.select('.//meta[@itemprop="sku"]/@content').extract()
                        if not identifier:
                            identifier = sub_option.select('.//form/input[contains(@name, "catalogRefIds") and @value!=" "]/@value').extract()
                        sub_item['identifier'] = identifier[0]
                        name = sub_option.select('.//td[@class="SkuGroup__sku__flavor"]/text()').extract()
                        if not name:
                            name = sub_option.select('.//td/h5/text()').extract()
                        if name:
                            sub_item['name'] += ' ' + name[0].strip()
                        price = ''.join(sub_option.select('./tr/td[contains(@class, "size-price")]/span/span[@class="price"]/text()').extract())
                        if not price:
                            price = ''.join(sub_option.select('./td[contains(@class, "size-price")]/span[@class="price"]/text()').extract())
                        if price:
                            sub_item['price'] = extract_price(price.strip())
                        in_stock = sub_option.select('.//td[@class="SkuGroup__sku__availability" and contains(text(), "In Stock")]').extract()
                        if not in_stock:
                            in_stock = sub_option.select('.//td[@class="availability" and contains(text(), "In Stock")]').extract()
                        if not in_stock:
                            sub_item['stock'] = 0
                        yield sub_item

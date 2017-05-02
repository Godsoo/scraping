from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.utils import extract_price
import re
from product_spiders.lib.schema import SpiderSchema


class ForlagidSpider(CrawlSpider):
    name = 'forlagid.is'
    allowed_domains = ['forlagid.is']
    start_urls = ['http://forlagid.is']

    categories = LinkExtractor(restrict_css='div.fusion-main-menu')
    products = LinkExtractor(restrict_css='.product-title')
    pages = LinkExtractor(restrict_css='.page-numbers')

    rules = (Rule(categories),
             Rule(pages),
             Rule(products, callback='parse_product'))

    def parse_product(self, response):
        data = SpiderSchema(response).get_product()

        options = response.xpath('//div[@class="summary-container"]/table//tr[not(th)]')
        for option in options:
            loader = ProductLoader(item=Product(), response=response)
            opt_name = option.xpath('.//td[contains(@class,"optionscol")]/text()')[0].extract()
            opt_name = u'{} - {}'.format(data['name'], opt_name)
            opt_identifier = option.xpath('@class')[0].extract().split(' ')[0]
            opt_price = option.xpath('@data-price').extract()

            loader.add_value('name', opt_name)
            loader.add_value('url', response.url)
            loader.add_value('sku', data['sku'])
            loader.add_value('identifier', opt_identifier)
            if 'image' in data:
                loader.add_value('image_url', data['image'])
            else:
                loader.add_xpath('image_url', '//meta[@itemprop="og:image"]/@content')
            stock = option.xpath('@class').re('instock')
            if not stock:
                loader.add_value('stock', 0)
            loader.add_value('price', opt_price)
            loader.add_css('category', 'div.product_meta span.posted_in a::text')

            yield loader.load_item()

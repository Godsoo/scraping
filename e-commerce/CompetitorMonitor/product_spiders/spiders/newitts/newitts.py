import os
import csv
from copy import deepcopy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor

from scrapy.http import Request

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class NewittsSpider(CrawlSpider):
    name = 'newitts-newitts.com'

    allowed_domains = ['newitts.com']

    start_urls = ('http://www.newitts.com/',)

    categories = LinkExtractor(restrict_css=('div#nav', 'ul.categories', 'div.products-index'))
    products = LinkExtractor(restrict_css='ul.product-list')
    
    rules = (Rule(categories),
             Rule(products, callback='parse_product'))

    def parse_product(self, response):
        loader = ProductLoader(response=response, item=Product())
        loader.add_value('url', response.url)
        sku = response.xpath('//input[@id="productSku"]/@value').extract_first()
        loader.add_value('identifier', sku)
        loader.add_value('sku', sku)
        loader.add_xpath('brand', '//span[@itemprop="brand"]/text()')
        category = response.xpath('//div[@class="breadcrumbs"]//li/a/text()').extract()[-3:]
        loader.add_value('category', category)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        loader.add_xpath('price', '//span[@id="price-displayed"]/text()')
        image_url = response.xpath('//a[@id="productImage"]/img/@src').extract()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url[0]))

        item = loader.load_item()
        
        attributes = response.xpath('//br/preceding-sibling::label[@for!="input-quantity"]/text()').extract()
        options = response.xpath('//tr[@itemprop="offers"]')
        headers = map(lambda x:x.lower(), response.xpath('//table[@id="variant-table"]//th/text()').extract())
        attr_indexes = {headers.index(attr.lower()): attr for attr in attributes}

        if not options:
            yield item
            return
        
        for option in options:
            metadata = dict()
            option_name = []
            for idx in sorted(attr_indexes):
                value = option.xpath('.//td')[idx].xpath('.//text()').re_first(' *\S+.+')
                if value:
                    option_name.append(value.strip())
                    metadata[attr_indexes[idx]] = value.strip()
            
            loader = ProductLoader(Product(), selector=option)
            loader.add_value(None, item)
            loader.add_value('name', option_name)
            loader.replace_xpath('price', './/span[@itemprop="price"]/text()')
            loader.add_value('price', 0)
            loader.replace_xpath('identifier', './/input[contains(@name, "VariantSku")]/@value')
            loader.replace_xpath('sku', './/input[contains(@name, "VariantSku")]/@value')
            
            option_item = loader.load_item()
            option_item['metadata'] = metadata
            yield option_item


                
                

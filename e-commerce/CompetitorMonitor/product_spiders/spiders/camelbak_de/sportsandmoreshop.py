import re
import json
from copy import deepcopy

try:
    from scrapy.spiders import Spider as BaseSpider
except ImportError:
    from scrapy.spider import BaseSpider

from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.utils.response import get_base_url
from scrapy.utils.url import url_query_parameter, add_or_replace_parameter
from product_spiders.utils import extract_price_eu as extract_price

from copy import deepcopy


class SportsAndMoreShopSpider(BaseSpider):
    name = 'camelbak_de-sportsandmoreshop.de'
    allowed_domains = ['sportsandmoreshop.de']	
    start_urls = ('http://www.sportsandmoreshop.de/suche/camelbak.htm?n_vl=camelbak',)

    def parse(self, response):
        products = response.xpath('//div[@class="title_max2"]/a/@href').extract()
        for url in products:
            yield Request(response.urljoin(url), callback=self.parse_product)

        pages = response.xpath('//select[@id="ddlpages"]/option/@value').extract()
        for page in pages:
            page_url = add_or_replace_parameter(response.url, "n_pg", page)
            yield Request(page_url)

    def parse_product(self, response):
        base_url = get_base_url(response)
        
        options = response.xpath('//div[@class="versionlist"]/a/@href').extract()
        ignore_options = response.meta.get('ignore_options', False)
        if options and not ignore_options:
            for option in options:
                yield Request(option, callback=self.parse_product, meta={'ignore_options': True})
            return

        loader = ProductLoader(item=Product(), response=response)

        name = response.xpath('//h1[@itemprop="name"]/text()').extract()[0]
        option_name = response.xpath('//div[@class="versionlist"]/a[contains(@class, "versionitemactive")]/text()').extract()
        if option_name:
            option_name = option_name[0].strip()
            if option_name.replace(' ', '').upper() not in name.replace(' ', '').upper():
                name += ' ' + option_name

        loader.add_value('name', name)
        identifier = response.xpath('//input[contains(@id, "tbQuantity_")]/@id').re('tbQuantity_(\d+)')[0]
        variant_id = response.xpath('//input[@id="hfVersionId"]/@value').extract()
        if variant_id and variant_id[0] !='0':
            identifier += '-' + variant_id[0]
        loader.add_value('identifier', identifier)
        sku = response.xpath('//span[contains(@id, "ItemId")]/text()').extract()[0]
        loader.add_value('sku', sku)
        loader.add_value('brand', 'CamelBak')
        loader.add_value('url', response.url)
        image_url = response.xpath('//div[@class="img_detail"]/img/@src').extract()[0]
        loader.add_value('image_url', image_url)
        categories = map(lambda x: x.strip(), response.xpath('//div[contains(@class, "breadcrumb")]/div/a/text()').extract())
        loader.add_value('category', categories)
        price = response.xpath('//span[@class="priceDetail"]/span[@itemprop="price"]/text()').extract()
        price = extract_price(price[0])
        loader.add_value('price', price)

        out_of_stock = response.xpath('//span[@itemprop="availability"]/div[@class="bg_stock av_red"]')
        if out_of_stock:
            loader.add_value('stock', 0)
   
        item = loader.load_item()

        options = response.xpath('//div[@class="versionfilter"]/a[contains(@class, "versionitemactive")]')
        if options:
            for option in options:
                option_item = deepcopy(item)
                name = option.xpath('@data-filter').extract()[0]
                option_item['name'] += ' ' + name
                yield option_item
        else:
            yield item
 

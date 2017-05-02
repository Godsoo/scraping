import os
import csv
import json
from urlparse import urljoin

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from product_spiders.utils import extract_price_eu as extract_price
from merckgroupitems import MerckGroupMeta



HERE = os.path.abspath(os.path.dirname(__file__))

class NaturesBestSpider(BaseSpider):
    name = 'naturesbest.co.uk-merckgroup'
    allowed_domains = ['naturesbest.co.uk']
    start_urls = (
        'http://www.naturesbest.co.uk/page/productdirectory/',
        'http://www.naturesbest.co.uk/pharmacy/page/productdirectory/',
    )

    cost_prices = {}

    def __init__(self, *args, **kwargs):
        super(NaturesBestSpider, self).__init__(*args, **kwargs)

        file_path = os.path.join(HERE, 'merckgroup_costprices.csv')
        with open(file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row['SKU'].upper().strip()
                self.cost_prices[sku] = row['COST']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in filter(lambda url: '/pharmacy/' not in url, hxs.select('//a[contains(@id, "prod_")]/@href').extract()):
            yield Request(url, callback=self.parse_product)

        for url in filter(lambda url: '/pharmacy/' in url, hxs.select('//a[contains(@id, "prod_")]/@href').extract()):
            yield Request(url, callback=self.parse_pharmacy_product)
            
        for url in hxs.select('//li[@class="parent"]/a/@href').extract():
            yield Request(url, callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        
        for url in hxs.select('//ul[@class="pharmList"]//h3/a/@href').extract():
            yield Request(url, callback=self.parse_pharmacy_product)
        
        for url in hxs.select('//li[@class="prodNAME"]/h3/a/@href').extract():
            yield Request(url, callback=self.parse_product)
            
        for url in hxs.select('//li[@class="level2"]/a/@href').extract():
            yield Request(url, callback=self.parse_category)
            
        for url in hxs.select('//span[@class="showall"]/a/@href').extract():
            if url != response.url:
                yield Request(url, callback=self.parse_category)
                return
        
    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        name = hxs.select(u'//div[@class="productTITLE"]/h1/text()').extract()
        if name:
            url = response.url
            url = urljoin(get_base_url(response), url)
            skus = hxs.select('//input[@name="sku"]/@value').extract()
            options = hxs.select('//td[@class="skuname"]/label/text()').extract()
            prices = hxs.select('//td[@class="price"]/text()').extract()
            options_prices = zip(options, skus, prices)
            for option, sku, price in options_prices:
                loader = ProductLoader(item=Product(), selector=hxs)
                loader.add_value('url', url)
                loader.add_value('name', (name[0].strip() + ' ' + option.strip()).replace(u'\xa0', ' '))
                loader.add_value('identifier', sku)
                loader.add_value('sku', sku)
                loader.add_value('price', price)
                category = hxs.select('//div[@id="crumb"]/span/a/text()').extract()
                category = category[-1] if category else ''
                loader.add_value('category', category)
                out_stock = 'OUT OF STOCK' in ''.join(hxs.select('//div[@itemprop="description"]/font//strong/text()').extract()).upper()
                if out_stock:
                    loader.add_value('stock', 0)
                image_url = hxs.select('//img[@id="productImage"]/@src').extract()
                if image_url:
                    image_url = urljoin(get_base_url(response), image_url[0])
                    loader.add_value('image_url', image_url)
                item = loader.load_item()
                metadata = MerckGroupMeta()
                cost_price = self.cost_prices.get(sku.upper().strip(), None)
                metadata['cost_price'] = str(extract_price(cost_price)) if cost_price else ''
                item['metadata'] = metadata
                yield item

    def parse_pharmacy_product(self, response):

        hxs = HtmlXPathSelector(response)

        name = hxs.select(u'//div[@class="productTITLE"]/h1/text()').extract()
        sku = hxs.select('//input[@id="sku"]/@value').extract()
        if name and sku:
            name = name[0]
            sku = sku[0]
            price = hxs.select('//div[@class="priceopt"]/text()').extract()[0].strip()
            in_stock = hxs.select('//span[@class="instock"]/text()').extract()
            in_stock2 = hxs.select('//link[@itemprop="availability" and contains(@href, "InStock")]').extract()
            category = hxs.select('//div[@id="crumb"]//span/a/text()').extract()
            category = category[-1] if category else ''
            image_url = hxs.select('//img[@id="productImage"]/@src').extract()
            if image_url:
                image_url = urljoin(get_base_url(response), image_url[0])
            url = response.url
            url = urljoin(get_base_url(response), url)

            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('url', url)
            loader.add_value('name', name.strip())
            loader.add_value('identifier', sku)
            loader.add_value('sku', sku)
            loader.add_value('price', price)
            loader.add_value('category', category)
            if not in_stock and not in_stock2:
                loader.add_value('stock', 0)
            if image_url:
                loader.add_value('image_url', image_url)
            item = loader.load_item()

            metadata = MerckGroupMeta()
            cost_price = self.cost_prices.get(sku.upper().strip(), None)
            metadata['cost_price'] = str(extract_price(cost_price)) if cost_price else ''
            item['metadata'] = metadata
            yield item

            options = hxs.select("//script[contains(text(), 'json_variant')]/text()").re('var json_variant = (\{.*\});')
            if options:
                options = json.loads(options[0])['jsonprod']

                for option in options:
                    json_sku = option['json_sku']
                    json_url = option['json_url']
                    if sku == json_sku:
                        continue
                    yield Request(json_url, callback=self.parse_pharmacy_product)
import re
import json

try:
    from scrapy.spiders import Spider as BaseSpider
except ImportError:
    from scrapy.spider import BaseSpider

from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price_eu as extract_price

from copy import deepcopy


class RoseBikesSpider(BaseSpider):
    name = 'camelbak_de-rosebikes.de'
    allowed_domains = ['rosebikes.de']
    start_urls = ('http://www.rosebikes.de/?nogeo=1',)

    def parse(self, response):
        camelbak_url = 'http://www.rosebikes.de/produkte/brand/camelbak/?count=9999'
        yield Request(camelbak_url, callback=self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//a[@class="products-details-content-title-title"]/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)

        name = hxs.select('//h1[@id="product_title"]/text()').extract()[0]
        loader.add_value('name', name)
        identifier = hxs.select('//input[@id="product-id"]/@value').extract()
        loader.add_value('identifier', identifier)
        loader.add_value('brand', 'CamelBak')
        loader.add_value('url', response.url)
        image_url = hxs.select('//div[contains(@class, "productimagebox")]/div/a/@href').extract()[0]
        loader.add_value('image_url', image_url)
        categories = hxs.select('//a[@class="breadcrumb"]/span/text()').extract()[-3:]
        loader.add_value('category', categories)
        price = hxs.select('//div[@id="product_price"]/text()').extract()
        price = extract_price(price[0])
        loader.add_value('price', price)

        out_of_stock = hxs.select('//span[@id="product_availability_text" and contains(text(), "Artikel ist ausverkauft")]').extract()
        if out_of_stock:
            loader.add_value('stock', 0)
   
        item = loader.load_item()

        options = []
        options_data = map(lambda x: x.split(' = ')[-1], re.findall('arrArticles(.*);', response.body))
        for option_data in options_data:
            if 'lieferartikelnummer' in option_data:
                data = json.loads(option_data)
                options.append(data)
        self.log('Logging %s' %response.url)
        for option in options:
            option_item = deepcopy(item)
            identifier = option['lieferartikelnummer']
            option_item['identifier'] = identifier
            produktauspraegung_id = option['produktauspraegung_id']
            color = hxs.select('//tr[contains(@id, %s)]//div[contains(@class, "name")]/text()' %produktauspraegung_id).extract() or hxs.select('//div[contains(@id, %s)]/img/@title' %produktauspraegung_id).extract()
            image_url = hxs.select('//tr[contains(@id, %s)]//img/@src' %produktauspraegung_id).extract() or hxs.select('//div[contains(@id, %s)]/img/@data-src' %produktauspraegung_id).extract()
            
            self.log('Identifier is %s' %identifier)
            self.log('produktauspraegung_id is %s' %produktauspraegung_id)
            self.log('Color is %s' %color)
            self.log('Image url is %s' %image_url)
          
            if image_url:
                option_item['image_url'] = image_url[0]

            if color:
                option_item['name'] += ' ' + color[0]
            option_item['name'] += ' ' + option['groesse']
            option_item['price'] = option['priceUnformatted']
            if option['built_stock']<=0:
                option_item['stock'] = 0
        
            yield option_item

import re
import json
import urlparse
from urllib import quote
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu, extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class CultFurnitureSpider(BaseSpider):
    name = 'voga_sw-cultfurniture'
    allowed_domains = ['cultfurniture.se', 'translate.google.com', 'xe.com']
    start_urls = ('http://www.cultfurniture.se/',)

    def _start_requests(self):
        yield Request('http://www.cultfurniture.se/inredning-c13/pace-matta-p1927', callback=self.parse_product, meta={'product': Product()})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for cat in hxs.select('//ul[@class="menu"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse)
        for cat in hxs.select('//p[@class="pagination"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse)

        for productxs in hxs.select('//div[@id="search_results_products"]/div[starts-with(@id, "product_")]'):
            price = extract_price_eu(productxs.select('.//div[contains(@class,"product_price") and @class!="product_price_percentage_saved"]//span[@class="inc"]/span[@class="SEK"]/text()').extract()[-1])
            yield Request(urljoin_rfc(get_base_url(response), productxs.select('.//a/@href').extract()[0]), callback=self.parse_product, meta = {'price':price})
#            yield self.fetch_product(request, self.add_shipping_cost(product))

            
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(Product(), selector=hxs)

        name = hxs.select('//h1//text()').extract()
        category = hxs.select('//div[@id="breadcrumb_container"]//a/text()').extract()

        loader.add_value('price', response.meta['price'])
        loader.add_value('stock', 1)
        loader.add_xpath('identifier', '//input[@id="parent_product_id"]/@value')
        loader.add_xpath('sku', '//span[@id="product_reference"]/text()')
        loader.add_value('url', response.url)

        img = hxs.select('//img[@itemprop="image"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        try:
            loader.add_value('shipping_cost', extract_price_eu(hxs.select('//span[@id="product_shipping_price"]//span[@class="inc"]/span[@class="SEK"]/text()').extract()[-1]))
        except:
            try:
                loader.add_value('shipping_cost', extract_price_eu(re.search('(Leverans.*till|Frakt) (.*)', response.body).group(2)))
            except:
                pass

        loader.add_value('brand', ([''] + hxs.select('//div[@id="breadcrumb_container"]//a[contains(@href, "-m")]/text()').extract())[-1])

        translate_url = 'https://translate.google.com/translate_a/single?client=t&sl=sv&tl=en&hl=ru&dt=bd&dt=ex&dt=ld&dt=md&dt=qca&dt=rw&dt=rm&dt=ss&dt=t&dt=at&ie=UTF-8&oe=UTF-8&source=btn&srcrom=0&ssel=4&tsel=3&kc=0&tk=522106|171915&q='
        url = ''
        for word in name+category:
            url = url + word + '\n'
        url = quote(url.encode('utf-8'), '')
        yield Request(translate_url+url, callback=self.translate, meta={'loader':loader}, dont_filter=True)

    def translate(self, response):
        loader = response.meta['loader']
        names = response.body.replace(',,,', ',')
        idx = names.find(']]')
        names = eval(names[1:idx+2])
        loader.add_value('name', names.pop(0)[0].decode('utf-8'))
        for category in names:
            loader.add_value('category', category[0].strip().decode('utf-8'))
            
        product = loader.load_item()
        price = product['price']
        url = 'http://www.xe.com/currencyconverter/convert/?Amount=%s&From=SEK&To=GBP' %str(price)
        yield Request(url, callback=self.convert, meta={'product':product}, dont_filter=True)

    def convert(self, response):
        hxs = HtmlXPathSelector(response)
        product = response.meta['product']
        price = extract_price(hxs.select('//tr[@class="uccRes"]/td[@class="rightCol"]/text()').extract()[0])
        try:
            rate = product['shipping_cost']/product['price']
            product['shipping_cost'] = (price*rate).quantize(Decimal('1.00'))
        except:
            pass
        product['price'] = price.quantize(Decimal('1.00'))
        yield self.add_shipping_cost(product)


    def add_shipping_cost(self, item):
        return item

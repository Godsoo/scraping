import re
import os
import csv
import shutil
from decimal import Decimal
from cStringIO import StringIO

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.item import Item, Field

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)

from scrapy.http import Request, HtmlResponse


HERE = os.path.abspath(os.path.dirname(__file__))


class StaplesMeta(Item):
    exclusive_online = Field()
    delivery_time = Field()
    promotion_price = Field()

class StaplesSpider(BaseSpider):
    name = 'na1-staples.pt'
    allowed_domains = ['staples.pt']
    start_urls = ('http://www.staples.pt',)


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@id="showallprods"]//a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url))

        next_page = hxs.select('//a[@id="lnkSeguinte"]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

        products = hxs.select('//td[@class="name"]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        identifier = hxs.select('//div[contains(@class,"skuinfo")]//input[@id="hdfProduto"]/@value').extract()
        sku = hxs.select('//li[contains(text(),"Fornecedor")]//text()').extract()
        if sku:
            sku = re.search(':(.*)', re.sub('[\r\n\t]', '', sku[0])).group(1)
        else:
            sku = hxs.select('//label[@id="lblRefereniaMBS"]/text()')[0].extract()
        loader.add_value('identifier', identifier)
        loader.add_value('sku', sku)
        name = hxs.select('//label[@id="lblTituloProduto"]/text()').extract()[0].strip()
        try:
            loader.add_value('name', name)
        except:
            loader.add_value('name', name.decode('utf-8', 'replace'))
        category = hxs.select('//div[@class="n03"]//a/text()').extract()
        loader.add_value('category', ' > '.join(category[:3]))
        image_url = hxs.select('//img[@id="productimage-0"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        brand = hxs.select('//li[contains(text(),"Marca")]//text()').extract()
        if brand:
            brand = re.search(':(.*)', re.sub('[\r\n\t]', '', brand[0])).group(1)
            loader.add_value('brand', brand)
        loader.add_value('url', response.url)
        
        price = hxs.select('//label[@id="MainContent_ucPreco_lblProdutoPrecoFinal"]/text()').extract()
        
        price = price[0].replace('.', '').replace(',', '.').strip() if price else '0.00'
        loader.add_value('price', price)
        out_of_stock = hxs.select('//span[@class="stock-red"]')
        if out_of_stock:
            loader.add_value('stock', 0)
        price = loader.get_output_value('price')
        if price:
            price = Decimal(price)
            if price <= 48.99:
                loader.add_value('shipping_cost', '3.00')

        metadata = StaplesMeta()
        metadata['exclusive_online'] = 'Yes' if hxs.select('//label[@id="lblTituloProduto"]/font[contains(text(),"Exclusivo Internet")]') else ''
        delivery_time = hxs.select('//label[@id="lblEntregaPrevista"]/text()').extract()
        metadata['delivery_time'] = delivery_time[0] if delivery_time else ''
        promotion_price = hxs.select('//label[@id="MainContent_ucPreco_lblPrecoProdutoAntes"]/text()').extract()
        metadata['promotion_price'] = promotion_price[0].replace('.', '').replace(',', '.').replace(u'\u20ac', '') if promotion_price else ''
        product = loader.load_item()
        product['metadata'] = metadata
        yield product

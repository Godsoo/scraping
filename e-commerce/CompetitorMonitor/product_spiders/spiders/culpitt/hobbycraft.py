from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from scrapy.http import Request
import re
import json


class Hobbycraft(BaseSpider):
    name = "culpitt-hobbycraft"
    allowed_domains = ['hobbycraft.co.uk']
    start_urls = ['http://www.hobbycraft.co.uk/baking']
    
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//div[@class="categories"]//a/@href').extract():
            yield Request(url, callback=self.parse_category)
    
    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//div[@class="categories"]//a/@href').extract():
            yield Request(urljoin(base_url, url), callback=self.parse_category)
        next_page_url = hxs.select('//a[contains(@id, "topPagination_NextPageLink")]/@href').extract()
        if next_page_url:
            yield Request(urljoin(base_url, next_page_url[0]), callback=self.parse_category)
        for url in hxs.select('//div[@class="row"]/div[contains(@class, "list_element")]/a[@id]/@href').extract():
            yield Request(urljoin(base_url, url.replace('../', '')), callback=self.parse_product)
            
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        data = hxs.select('//script[@type="text/javascript"]/text()[contains(., "window.universal_variable")]').extract()[0]
        data = data.replace('\r\n', '')
        data = re.findall('window.universal_variable = ({.+})', data)[0]
        data = json.loads(data)
        product = data['product']
        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('url', product['url'])
        loader.add_value('name', product['name'])
        loader.add_value('price', product['unit_price'])
        loader.add_value('identifier', product['sku_code'])
        loader.add_value('sku', product['id'])
        loader.add_value('stock', int(product['stock']))
        loader.add_value('category', data['page']['breadcrumb'][1:-1])
        loader.add_value('image_url', urljoin(base_url, hxs.select('//a[@id="ctl00_con1_ctl00_prodimg1_imglnk1"]/@href').extract()[0]))
        item = loader.load_item()
        if item['price'] < 30:
            item['shipping_cost'] = 3.50
        yield item
        for url in hxs.select('//option/@value').extract():
            yield Request(url, callback=self.parse_product)

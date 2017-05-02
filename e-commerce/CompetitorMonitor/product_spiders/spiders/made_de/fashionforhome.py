from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from urlparse import urljoin
import json

class FashionForHomeDE(BaseSpider):
    name = 'fashionforhome.de'
    allowed_domains = ['fashionforhome.de']
    start_urls = ['http://www.fashionforhome.de/', 'http://www.fashionforhome.de/aktuelle-aktionen']
    
    def start_requests(self):
        for url in self.start_urls:
            yield Request(url)
        yield Request('http://www.fashionforhome.de/sitemap', callback=self.parse_sitemap)
    
    def parse_sitemap(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        for url in hxs.select('//div[@id="tabBoxContainer"]//a/@href').extract():
            yield Request(urljoin(base_url, url), callback=self.parse_category)
        
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        categories = hxs.select('//ul[@id="ffh-yodanavigation"]//a/@href').extract()
        categories += hxs.select('//a/@href').extract()
        for url in categories:
            yield Request(urljoin(base_url, url), callback=self.parse_category)
            
    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for url in hxs.select('//ul[@id="item-stage"]//a/@href').extract():
            yield Request(urljoin(base_url, url), callback=self.parse_product)
            
        categories_id = hxs.select('//span/@id').re('countLink:main_category:(\d+)')
        categories_id += hxs.select('//script[@type="text/javascript"]/text()').re('{"categories":"(\d+)",')
        for cat_id in categories_id:
            yield Request('http://www.fashionforhome.de/static/s.php?channel=overview&params[category]=%s&limit=199' %cat_id, callback=self.parse_php, meta={'cat_id': cat_id})
        
    def parse_php(self, response):
        data = json.loads(response.body)
        html = data['hits']['big']
        if not html:
            return
        hxs = HtmlXPathSelector(text=html)
        base_url = get_base_url(response)

        for url in hxs.select('//a/@href').extract():
            yield Request(urljoin(base_url, url), callback=self.parse_product)
            
        cat_id = response.meta.get('cat_id', '')
        if cat_id:
            url = 'http://www.fashionforhome.de/static/s.php?channel=overview&params[category]=%s&limit=199&skip=199' %cat_id
        else:
            url = 'http://www.fashionforhome.de/static/s.php?channel=overview&limit=199&skip=199'
            
        if data['hits']['count'] == 199:
            yield Request(url, callback=self.parse_php, meta=response.meta)
        
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        try:
            data = json.loads(hxs.select('//script[@type="text/javascript"]/text()').re('var utag_data = ({.+})')[0])
        except IndexError:
            return
        
        loader = ProductLoader(item=Product(), selector=hxs)
        try:
            loader.add_value('name', data['product_name'])
        except KeyError:
            return
        loader.add_value('identifier', data['product_id'])
        loader.add_value('sku', data['product_id'])
        loader.add_value('brand', data['product_attribute_trademark'])
        loader.add_value('url', urljoin(base_url, data['internal_url']))
        loader.add_value('price', data['product_price'][0] + data['product_taxes'][0])
        categories = hxs.select('//div[@class="breadcrumbs"]//a/text()').extract()[1:]
        loader.add_value('category', categories)
        loader.add_xpath('image_url', '//img[@id="image"]/@src')
        item = loader.load_item()
        if item['price'] < 75:
            item['shipping_cost'] = 7.50
        yield item
        
        for url in hxs.select('//div[@id="slice_options"]//a/@href[.!="#"]').extract():
            yield Request(urljoin(base_url, url), callback=self.parse_product)
        yield Request('http://www.fashionforhome.de/static/s.php?channel=child&limit=199&single_item_type=k&chunk_type=big&params[product_id]=%s&params[lazy]=1' %data.get("parent_product_id", [''])[0], callback=self.parse_php)
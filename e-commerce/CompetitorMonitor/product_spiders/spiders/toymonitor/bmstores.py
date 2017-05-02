'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5329
'''

import json
import hashlib
from w3lib.url import add_or_replace_parameter
from scrapy.spider import CrawlSpider as Spider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request
from scrapy.selector import Selector

from product_spiders.items import ProductLoaderWithoutSpaces as ProductLoader, Product

class BMStores(Spider):
    name = 'toymonitor-bmstores'
    allowed_domains = ['bmstores.co.uk']
    start_urls = ['http://www.bmstores.co.uk/products/toys-and-games']
    
    categories = LinkExtractor(restrict_css='ul.aside-list')
    products = LinkExtractor(restrict_css='a.product')
    
    rules = (Rule(categories, callback='parse_pages', follow=True),
             Rule(products, callback='parse_product'))
    
    def parse_pages(self, response):
        category_id = response.xpath('//script/text()').re("categoryID: '(.+)'")[0]
        for page in response.css('div.pagination ::attr(data-pageto)').extract():
            url = 'http://www.bmstores.co.uk/hpcProduct/productbyfilter/ajaxmode/1?categoryID=%s&sort=datehigh&perPage=36&pageNum=%s' %(category_id, page)
            yield Request(url, self.parse_page)
            
    def parse_page(self, response):
        data = json.loads(response.body)
        if not data['success']:
            self.logger.warning('Failed pagination %s' %response.url)
        selector = Selector(text=data['paginationLink'])
        for page in selector.css('div.pagination ::attr(data-pageto)').extract():
            url = add_or_replace_parameter(response.url, 'pageNum', page)
            yield Request(url, self.parse_page)
        selector = Selector(text=data['pageHTML'])
        for url in selector.css('a.product::attr(href)').extract():
            yield Request(response.urljoin(url), self.parse_product)
            
    def parse_product(self, response):
        if 'login.cfm' in response.url:
            return
        loader = ProductLoader(Product(), response=response)
        identifier = response.url.split('/')[-1]
        identifier = hashlib.md5(identifier).hexdigest()
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        loader.add_css('name', 'h1.content-title::text')
        loader.add_xpath('price', '//script/text()', re='price": "(.+)"')
        loader.add_xpath('sku', '//script/text()', re='sku": "(.+)"')
        category = response.xpath('//ul[@id="breadcrumbs"][1]//a/text()').extract()[1:-1]
        loader.add_value('category', category)
        image_url = response.css('div.product-detail-feature-img img::attr(src)').extract_first()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url))
        loader.add_xpath('brand', '//meta[@property="og:brand"]/@content')
        stock = response.xpath('//script/text()').re('availability": "(.+)"')
        if stock and stock[0] != 'In stock':
            loader.add_value('stock', 0)      
        yield loader.load_item()

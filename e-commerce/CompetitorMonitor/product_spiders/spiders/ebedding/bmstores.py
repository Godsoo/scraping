'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5218
'''

import json
import re
from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request
from scrapy.selector import Selector
from product_spiders.items import ProductLoaderWithoutSpaces as ProductLoader, Product
from w3lib.url import add_or_replace_parameter, url_query_cleaner


class BMStores(CrawlSpider):
    name = 'e-bedding-bmstores'
    allowed_domains = ['bmstores.co.uk']
    start_urls = ('http://www.bmstores.co.uk/products/home-and-living/soft-furnishings',
                  'http://www.bmstores.co.uk/products/home-and-living/bedding')
    
    categories = LinkExtractor(('/soft-furnishings/', '/bedding/'))
    products = LinkExtractor(restrict_css='.product')
    
    rules = (
        Rule(categories, callback='parse_category', follow=True),
        Rule(products, callback='parse_product')
        )
    
    def parse_category(self, response):
        try:
            category_id = response.xpath('//script/text()').re("categoryID: *'(.+)'")[0]
        except IndexError:
            return
        per_page = response.xpath('//script/text()').re("var showInput *= *'(.+)'")[0]
        sort = response.xpath('//script/text()').re("var sortInput *= *'(.+)'")[0]
        url = 'http://www.bmstores.co.uk/hpcProduct/productbyfilter/ajaxmode/1'
        parameters = ('categoryID', 'perPage', 'sort')
        values = (category_id, per_page, sort)
        for parameter, value in zip(parameters, values):
            url = add_or_replace_parameter(url, parameter, value)
        pages = response.xpath('//@data-pageto').extract()
        for page in pages:
            yield Request(add_or_replace_parameter(url, 'pageNum', page),
                          self.parse_json_products)
            
    def parse_json_products(self, response):
        data = json.loads(response.body)
        if data['success'] != 'true':
            self.logger.warning('Not success request %s' %response.url)
            
        html = data['pageHTML']
        selector = Selector(text=html)
        products = selector.css('a.product::attr(href)').extract()
        for url in products:
            yield Request(response.urljoin(url),
                          self.parse_product)
            
        html = data['paginationLink']
        selector = Selector(text=html)
        pages = selector.xpath('//@data-pageto').extract()
        for page in pages:
            yield Request(add_or_replace_parameter(response.url, 'pageNum', page),
                          self.parse_json_products)

    def parse_product(self, response):
        re_data = re.compile(r'\{.+\}', re.DOTALL)
        json_data = response.xpath('//script[@type="application/ld+json"]/text()').re(re_data)
        data = json.loads(json_data[0].replace('\n', ' '))
        identifier = re.search('\d\d\d+$', response.url).group(0)
        loader = ProductLoader(Product(), response=response)
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        loader.add_value('name', data['name'])
        loader.add_value('price', data['offers']['price'])
        loader.add_value('sku', data['sku'])
        category = response.css('ul#breadcrumbs:first-of-type a::text').extract()
        loader.add_value('category', category[1:-1])
        loader.add_value('image_url', data['image'])
        loader.add_value('brand', data['brand']['name'])     
        yield loader.load_item()
"""
E-Bedding account
Littlewoods spider
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4954
"""

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.selector import Selector
from scrapy.http import FormRequest, Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from w3lib.url import url_query_parameter, url_query_cleaner, add_or_replace_parameter
import json

class Tesco(CrawlSpider):
    name = 'e-bedding-tesco'
    allowed_domains = ['tesco.com']
    start_urls = ['http://www.tesco.com/direct/home-furniture/bedding-bed-linen/cat3376418.cat?catId=4294722486',
                  'http://www.tesco.com/direct/home-furniture/bedding-bed-linen/cat3376418.cat']
    
    categories = LinkExtractor(restrict_css=('div#page-container div.accordion', 'div.kiosk-hide'))
    products = LinkExtractor(allow='\.prd', process_value=url_query_cleaner)
    
    rules = [
        Rule(products, callback='parse_product'),
        Rule(categories, callback='parse_categories')
        ]
    
    def _start_requests(self):
        yield Request('http://www.tesco.com/direct/silentnight-single-duvet-tog-ultrabounce/798-1878.prd?pageLevel=&skuId=394-5861', self.parse_product)
        return
    
    def parse_categories(self, response):
        products_count = response.xpath('//@data-maxcount').extract_first()
        if not products_count:
            return
        products_count = int(products_count)
        pages = products_count/20
        catid = response.xpath('//@data-endecaid').extract_first()
        url = 'http://www.tesco.com/direct/blocks/catalog/productlisting/infiniteBrowse.jsp?&view=grid&catId=%s&sortBy=1&searchquery=&offset=%d&lazyload=true&pageViewType=grid'
        for page in xrange(1, pages+1):
            yield Request(url %(catid, 20*page), self.parse_json)
        
        for link in self.products.extract_links(response):
            yield Request(link.url, self.parse_product)
    
    def parse_json(self, response):
        data = json.loads(response.body)
        selector = Selector(text=data['products'])
        for url in selector.xpath('//a/@href[contains(., ".prd")]').extract():
            yield Request(url_query_cleaner(response.urljoin(url), ('skuId',)), self.parse_product)
            
    def parse_product(self, response):
        if response.url.endswith('page-not-found.page'):
            return
        formdata = {}
        for inp in response.xpath('//form[@id="variant-form"]//input'):
            formdata[inp.xpath('@name').extract_first()] = inp.xpath('@value').extract_first()
        if not formdata:
            self.logger.warning('No data on %s' %response.url)
            return
        del formdata[None]
        options = response.css('.vContainer .variantDataElement')
        for option in options:
            formdata[option.xpath('@name').extract_first()] = option.xpath('@data-variant-value').extract_first()
            r = FormRequest.from_response(response, 
                                          formxpath='//form[@id="variant-form"]',
                                          formdata=formdata,
                                          callback=self.parse_product)
            yield r
            
        loader = ProductLoader(item=Product(), response=response)
        sku = response.xpath('//input[@id="skuIdVal"]/@value').extract_first()
        if sku != url_query_parameter(response.url, 'skuId'):
            url = add_or_replace_parameter(url_query_cleaner(response.url), 'skuId', sku)
            yield Request(url, self.parse_product)
            return
        loader.add_value('identifier', sku)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1[@id="productLabel"]//text()')
        #loader.add_css('name', '.selected .variantDisplayName_title ::text')
        loader.add_css('price', '.current-price ::text')
        loader.add_value('sku', sku)
        category = response.xpath('//div[@id="breadcrumb"]//li//span[@itemprop="title"]/text()').extract()
        loader.add_value('category', category[-4:-1])
        image_url = response.xpath('//img[@itemprop="image"]/@src').extract_first()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url))
        loader.add_xpath('brand', '//div[@itemprop="brand"]//span[@itemprop="name"]/text()')
        loader.add_value('shipping_cost', 3)
        #if not response.css('.stock-tag.in-stock') and not response.xpath('//link[@href="http://schema.org/InStock"]') and not response.css('.available-from'):
        if not response.css('.add-to-basket'):
            loader.add_value('stock', 0)
        if loader.get_output_value('price'):
            yield loader.load_item()
        
    
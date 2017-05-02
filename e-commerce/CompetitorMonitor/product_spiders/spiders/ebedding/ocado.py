'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5189
'''

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request
from product_spiders.items import ProductLoaderWithoutSpaces as ProductLoader, Product
from w3lib.url import add_or_replace_parameter, url_query_cleaner


class Ocado(CrawlSpider):
    name = 'e-bedding-ocado'
    allowed_domains = ['ocado.com']
    start_urls = ['https://www.ocado.com/webshop/getCategories.do?tags=|30931|126580']
    
    categories = LinkExtractor(restrict_css='#navigationSidebar .superNav')
    products = LinkExtractor(restrict_css='.productTitle', 
                             allow='/product/',
                             process_value=url_query_cleaner)
    
    rules = (
        Rule(categories, callback='parse_category', follow=True),
        Rule(products, callback='parse_product')
        )
    
    def parse_category(self, response):
        count = response.css('#productCount em::text').re('\d+')[0]
        for idx in xrange(int(count)):
            url = add_or_replace_parameter(response.url, 'index', idx)
            yield Request(url)
            
    def parse_product(self, response):
        options = response.css('.pg_select')
        if options:
            selected_option = options.xpath('option[@selected]')
            if not selected_option:
                for url in options.xpath('.//@data-href').extract():
                    yield Request(response.urljoin(url_query_cleaner(url)),
                                  self.parse_product)
                return
            
        loader = ProductLoader(Product(), response=response)
        sku = response.xpath('//div[@id="content"]//input[@name="sku"]/@value').extract_first()
        loader.add_value('identifier', sku)
        loader.add_value('sku', sku)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//strong[@itemprop="name"]/text()')
        loader.add_css('price', 'div.show h5 ::text')
        loader.add_css('price', '.nowPrice ::text')
        loader.add_css('price', '.typicalPrice h5 ::text')
        category = response.xpath('//input[@name="productDetailsDTO"]/@value').re('"category":"(.+?)"')
        if category:
            loader.add_value('category', category[0].split('/'))
        image_url = response.css('ul#galleryImages a::attr(href)').extract_first()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url))
        loader.add_xpath('brand', '//span[@itemprop="brand"]//span[@itemprop="name"]/text()')
        if response.css('div#content p.oos'):
            loader.add_value('stock', 0)     
        yield loader.load_item()
from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request, FormRequest

from w3lib.url import add_or_replace_parameter, url_query_cleaner

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
import json


class MattressNextDayCoUkSpider(CrawlSpider):
    name = 'colourbank-mattressnextday.co.uk'
    allowed_domains = ['mattressnextday.co.uk']
    start_urls = ['http://www.mattressnextday.co.uk/']

    categories = LinkExtractor(restrict_css=('nav', 'div.mega-dropdown'))
    products = LinkExtractor(restrict_css='div.product-info')
    
    rules = (Rule(categories),
             Rule(products, callback='parse_product'))

    def parse_product(self, response):
        select = response.css('ul.options')
        if len(select) != 1:
            self.logger.debug('Selects: %d' %len(select))
        
        base_url = url_query_cleaner(response.url).split('&option')[0]
        option_ids = select.xpath('li/@data-option-value-id').extract()
        for idx in option_ids:
            url = add_or_replace_parameter(base_url, 'option', idx)
            yield Request(url, self.parse_product)
        
        option_id = select.css('li.selected::attr(data-option-value-id)').extract_first()
        if not option_id:
            return
        
        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_value('url', response.url)
        img = response.css('div.extra-thumbnail img::attr(src)').extract_first()
        if img:
            product_loader.add_value('image_url', response.urljoin(img))

        brand = response.xpath('//noscript/iframe').re('u10=(.+?);')
        product_loader.add_value('brand', brand)
        product_loader.add_xpath('name', '//span[@id="product-title"]/text()')
        option_name = select.css('li.selected::text').extract_first()
        product_loader.add_value('name', '-')
        product_loader.add_value('name', option_name)
        product_loader.add_xpath('name', '//span[@id="selected-label"]/text()')

        categories = response.css('ul.breadcrumb a::text').extract()[1:-1] or response.xpath('//script/text()').re('u3=(.+?);')
        product_loader.add_value('category', categories)
        
        product_id = response.xpath('//input[@name="product_id"]/@value').extract_first()
        identifier = '-'.join((product_id, option_id))
        product_loader.add_value('identifier', identifier)
        sku = select.css('li.selected::attr(value)').extract_first()
        product_loader.add_value('sku', sku)
        price = select.css('li.selected::attr(data-option-price)').extract_first()
        product_loader.add_value('price', price)
        
        url = '/index.php?route=product/product/getStockStatus'
        data = {'product_id': product_id, 'option_value_ids': option_id}
        yield FormRequest(response.urljoin(url),
                          self.parse_stock,
                          formdata=data,
                          meta={'loader': product_loader})
        
    def parse_stock(self, response):
        stock = json.loads(response.body)['stock']
        loader = response.meta['loader']
        if stock == 'Auto':
            product_id, option_id = loader.get_output_value('identifier').split('-')
            url = '/index.php?route=product/product/getQuantity'
            data = {'product_id': product_id, 'option_value_ids': option_id}
            yield FormRequest(response.urljoin(url),
                          self.parse_quantity,
                          formdata=data,
                          meta={'loader': loader})
            return
        elif stock != 'In Stock':
            loader.add_value('stock', 0)
        yield loader.load_item()
    
    def parse_quantity(self, response):
        quantity = int(json.loads(response.body)['quantity'])
        loader = response.meta['loader']
        if quantity <= 0:
            loader.add_value('stock', 0)
        yield loader.load_item()
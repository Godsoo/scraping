'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5345
'''

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import ProductLoaderWithoutSpaces as ProductLoader, Product


class LowryJewellers(CrawlSpider):
    name = 'bablas-lowryjewellers'
    allowed_domains = ['lowryjewellers.com']
    start_urls = ['http://www.lowryjewellers.com/']
    
    categories = LinkExtractor(restrict_css='li>a.top_level_link')
    pages = LinkExtractor(restrict_css='.pagination')
    products = LinkExtractor(restrict_css='div.product__details__title>a')
    
    rules = (Rule(categories),
             Rule(pages),
             Rule(products, callback='parse_product'))
    
    def parse_product(self, response):
        loader = ProductLoader(Product(), response=response)
        identifier = response.xpath('//script/text()').re('ecomm_prodid: *(\d+),')
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        name = ' '.join(''.join(response.xpath('//h1//text()').extract()).split())
        loader.add_value('name', name)
        loader.add_css('price', 'span.GBP::attr(content)')
        loader.add_xpath('sku', '//span[@id="js-product-reference"]/@data-ref')
        category = response.xpath('//div[contains(@class, "breadcrumb")]//a/span/text()').extract()[1:]
        loader.add_value('category', category)
        image_url = response.xpath('//a[@class="product__image__zoom-link"]/@href').extract()
        image_url = response.urljoin(image_url[0]) if image_url else ''
        loader.add_value('image_url', image_url)
        brand = response.xpath('//span[@class="product-content__title--brand"]/text()').extract()
        brand = brand[0].strip() if brand else ''
        loader.add_value('brand', brand)
        stock = response.xpath('//span[@id="js-product-in-stock-default" and contains(text(), "in Stock")]')
        if not stock:
            loader.add_value('stock', 0)
        yield loader.load_item()

"""
This spider was moved from FMS
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4188-lego-usa--lego_usa_cptoy_com-issue/details

Reworked price extraction, reworked to scrapy 1.x, code clean up by Sergey Egorov 19.05.2016
"""

from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price


class CpToySpider(CrawlSpider):
    name = 'lego_usa_cptoy_com'
    allowed_domains = ['cptoy.com']
    start_urls = ('http://products.cptoy.com/search?p=Q&lbc=cptoy&uid=460652038&ts=custom&w=Lego&isort=score&method=and&view=list&sli_jump=1&af=cat:&nocrosssite=true',)
    
    products = LinkExtractor(allow = '/catalog/product/')
    pages = LinkExtractor(restrict_css = 'a.pageselectorlink')

    rules = (Rule(products, callback='parse_product'),
             Rule(pages))

    @staticmethod
    def parse_product(response):
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('identifier', '//table[attribute::id="product-attribute-specs-table"]//th[attribute::class="label" and contains(text(), "SKU")]/following-sibling::td/text()')
        loader.add_xpath('name', '//form[attribute::id="product_addtocart_form"]/div[2]/div[1]/div[1]/div[2]/h1[1]/text()')
        loader.add_value('brand', 'Lego')
        loader.add_xpath('sku', '//form[attribute::id="product_addtocart_form"]/div[2]/div[1]/div[1]/p[1]/text()', re='([\d]+)')
        loader.add_value('url', response.url)
        price = response.xpath('//*[contains(@id,"product-price")]//span[contains(@class, "price") and last()]/text()|//*[contains(@id,"product-price")]/text()').extract()
        price = ''.join(price)
        loader.add_value('price', extract_price(price.strip()))
        image_url = response.xpath('//div[attribute::class="product-img-box"]//a[@id="main-image"]/img/@src').extract_first()
        for category in response.xpath('//div[@class="breadcrumbs"]/ul/li/a/text()')[1:].extract():
            loader.add_value('category', category)
        stock = response.xpath('//p[@class="availability in-stock"]')
        if not stock:
            loader.add_value('stock', 0)
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url))
        yield loader.load_item()

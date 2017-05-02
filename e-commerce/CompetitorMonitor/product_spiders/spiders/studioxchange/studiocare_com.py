from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
import re
from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.contrib.loader.processor import TakeFirst, Compose

def onlyDecimal(a):
    return re.sub(r'[^0-9.]','', a)


class StudioCareComSpider(BaseSpider):
    name = 'www.studiocare.com'
    allowed_domains = ['studiocare.com', 'www.studiocare.com']
    start_urls = ['http://www.studiocare.com']
    
    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        xpath_str = '//ul[@id="vertnav"]/li/span/a'
        pages = hxs.select(xpath_str)

        for page in pages:
            link = page.select('@href').extract().pop()
            text = page.select('.//text()').extract().pop()
            
            request = Request(urljoin_rfc(base_url, link.strip('? ') + "?limit=100"),
                          callback=self.parse_category)
            request.meta['category'] = text
            yield request
            
    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        xpath_str = '//h2[@class="product-name"]/a/@href'
        pages = hxs.select(xpath_str).extract()

        for page in pages:
            request = Request(urljoin_rfc(base_url, page),
                          callback=self.parse_product)
            request.meta['category'] = response.meta['category']
            yield request
            
        # parse next page
        xpath_str = '//div[@class="pages"]/ol/li/a[@title="Next"]/@href'
        pages = hxs.select(xpath_str).extract()

        if pages and len(pages) > 0: 
            request = Request(urljoin_rfc(base_url, pages[0]),
                          callback=self.parse_category)
            request.meta['category'] = response.meta['category']
            yield request
            
    
    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        
        loader = ProductLoader(response=response, item=Product())
        loader.add_xpath('price', '(//span[@class="price-including-tax"])[1]/span/text()', TakeFirst(), Compose(onlyDecimal))
        loader.add_xpath('identifier', '//form[@id="product_addtocart_form"]//input[@name="product"]/@value')
        loader.add_xpath('sku', '//table[@id="product-attribute-specs-table"]//tr[contains(th/text(), "SKU")]/td/text()')
        loader.add_xpath('brand', '//table[@id="product-attribute-specs-table"]//tr[contains(th/text(), "Manufacturer")]/td/text()')
        loader.add_value('url', urljoin_rfc(base_url, response.url))
        loader.add_xpath('name', '//div[@class="product-name"]/h1/text()')
        loader.add_xpath('image_url', '//p[@class="product-image"]//img/@src')
        loader.add_value('category', response.meta['category'])
 
        yield loader.load_item()

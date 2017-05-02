import os
import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class ConradUkSpider(BaseSpider):
    name = 'conrad-uk.com'
    allowed_domains = ['conrad-uk.com']
    
    start_urls = ['http://www.conrad-uk.com/ce/en/brand/PROXXON-MICROMOT?perPage=100',
                  'http://www.conrad-uk.com/ce/en/brand/PROXXON-INDUSTRIAL?perPage=100']

    def parse(self, response):
        ''' First goes into the main categories, this site stores in cache 
            the current page, this is necessary to go to the next page.
        '''
        hxs = HtmlXPathSelector(response)
        next_page = hxs.select('//div[@class="page-navigation"]/a[contains(text(),"Next")]/@href').extract()
        if next_page:
            next_page = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(next_page)
        products =  hxs.select('//div[@id="list-product-list"]//div[contains(@class,"list-product-item")]')
        if products:
            for product in products:
                loader = ProductLoader(item=Product(), selector=product)
                name = ''.join(product.select('.//div[@class="name"]/a/text()').extract())
                if name:
                    loader.add_value('name', name)
                    # identifier = product.select('').extract()
                    #  if identifier:
                        # identifier = identifier[0]
                    # loader.add_value('identifier', identifier)
                    url = ''.join(product.select('.//div[@class="name"]/a/@href').extract())
                    if url:    
                        url = urljoin_rfc(get_base_url(response), url.split(';')[0])
                    loader.add_value('url', url)
                    price = product.select('.//div[@class="price-info"]//span[@class="current-price"]/text()').extract()
                    if price:
                        price = round(float(re.findall("\d+.\d+", price[0].replace(',', ''))[0])/1.2, 2)
                    loader.add_value('price', price)
                    yield Request(loader.get_output_value('url'), meta={'loader': loader}, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = response.meta['loader']
        sku = hxs.select('//div[@id="productdetail"]//div[@class="number"]/span/strong/text()')[0].extract()
        loader.add_value('identifier', sku)
        yield loader.load_item()

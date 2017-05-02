from product_spiders.spiders.express_gifts.expressgiftsitems import ExpressGiftsBaseSpider
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from urlparse import urljoin
from scrapy.utils.response import get_base_url


class ToysRUs(ExpressGiftsBaseSpider):
    name = 'expressgifts-toysrus'
    allowed_domains = ['toysrus.co.uk']
    
    def start_requests(self):
        for row in super(ToysRUs, self).start_requests():
            url = row['TOYS_R_US'].strip()
            if url:
                yield Request(url, callback=self.parse_product, meta={'id':row['PRODUCT_NUMBER']})
                
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        xpath = '//script[@type="text/javascript"]/text()'
        pattern = '%s:.*?"(.+)"'
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', xpath, re=pattern %'product_name')
        identifier = response.meta['id']
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('url', response.url)
        loader.add_xpath('price', xpath, re=pattern %'product_base_price')
        loader.add_xpath('image_url', '//a[@id="mainImage"]/img/@src')
        loader.add_xpath('category', '//ul[@class="breadcrumbs"]/li[position()>1]/a/text()')
        loader.add_xpath('brand', xpath, re=pattern %'product_brand')
        if hxs.select('//span[text()="Delivery"]/../span[2][contains(text(), "out of stock")]'):
            loader.add_value('stock', 0)
        
        yield loader.load_item()
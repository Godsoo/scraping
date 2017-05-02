from product_spiders.spiders.express_gifts.expressgiftsitems import ExpressGiftsBaseSpider
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from urlparse import urljoin
from scrapy.utils.response import get_base_url


class KidsElectricCars(ExpressGiftsBaseSpider):
    name = 'expressgifts-kidselectriccars'
    allowed_domains = ['kidselectriccars.co.uk']
    
    def start_requests(self):
        for row in super(KidsElectricCars, self).start_requests():
            url = row['KIDSELECTRICTOYCARS.CO.UK'].strip()
            if url:
                yield Request(url, callback=self.parse_product, meta={'id':row['PRODUCT_NUMBER']})
                
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//h1[@class="product_head"]/text()', re='\w+')
        identifier = response.meta['id']
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('url', response.url)
        loader.add_xpath('price', '//div[@class="product_price"]//div[@class="single_price"]/text() | //div[@class="product_price"]//span[@class="productSpecialPrice"]/text()')
        image = hxs.select('//div[@id="productMainImage"]//img/@src').extract()[0]
        loader.add_value('image_url', urljoin(get_base_url(response), image))
        loader.add_xpath('category', '//div[@id="navBreadCrumb"]/ul/li[position()>1]/a/text()')
        loader.add_value('shipping_cost', 4.95)
        if not hxs.select('//div[@class="cart_button"]//@value'):
            loader.add_value('stock', 0)
        
        yield loader.load_item()
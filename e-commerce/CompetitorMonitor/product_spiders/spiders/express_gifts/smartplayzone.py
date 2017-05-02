from product_spiders.spiders.express_gifts.expressgiftsitems import ExpressGiftsBaseSpider
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from urlparse import urljoin
from scrapy.utils.response import get_base_url


class KidsElectricCars(ExpressGiftsBaseSpider):
    name = 'expressgifts-smartplayzone'
    allowed_domains = ['smartplayzone.com']
    
    def start_requests(self):
        for row in super(KidsElectricCars, self).start_requests():
            url = row['SMART_PLAY_ZONE'].strip()
            if url:
                yield Request(url, callback=self.parse_product, meta={'id':row['PRODUCT_NUMBER']})
                
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//meta[@property="og:title"][1]/@content')
        identifier = response.meta['id']
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('url', response.url)
        loader.add_xpath('price', '//span[@class="price-including-tax"]/span[@class="price"]/text()')
        loader.add_xpath('image_url', '//div[@class="product-img-box"]//img/@src')
        loader.add_xpath('category', '//div[@class="breadcrumbs"]/ul/li[position()>1]/a/text()')
        brand = hxs.select('//th[text()="Manufacturer"]/../td/text()').extract()
        if brand:
            loader.add_value('brand', brand[0])
        if not hxs.select('//p[@class="availability in-stock"]/span'):
            loader.add_value('stock', 0)
        
        yield loader.load_item()
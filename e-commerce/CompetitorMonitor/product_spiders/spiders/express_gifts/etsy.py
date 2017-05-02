from product_spiders.spiders.express_gifts.expressgiftsitems import ExpressGiftsBaseSpider
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

class Etsy(ExpressGiftsBaseSpider):
    name = 'expressgifts-etsy'
    allowed_domains = ['etsy.com']
    
    def start_requests(self):
        for row in super(Etsy, self).start_requests():
            url = row['ETSY'].strip()
            if url:
                yield Request(url, callback=self.parse_product, meta={'id':row['PRODUCT_NUMBER']})
                
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//meta[@property="og:title"]/@content')
        identifier = response.meta['id']
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('url', response.url)
        loader.add_xpath('price', '//meta[@itemprop="price"]/@content')
        loader.add_xpath('image_url', '//div[@id="image-main"]//@src')
        loader.add_xpath('brand', '//div[@class="shop-name"]/a/text()')
        
        yield loader.load_item()
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from urlparse import urljoin
from scrapy.utils.response import get_base_url
from scrapy.item import Item, Field

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

class MetaData(Item):
    Promotions = Field()
    
class VictorianPlumbing(BaseSpider):
    name = 'victorian-plumbing'
    allowed_domains = ['victorianplumbing.co.uk']
    start_urls = ['http://www.victorianplumbing.co.uk/']
    
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        for url in hxs.select('//div[@id="mainMenu"]/ul//a/@href').extract():
            yield Request(urljoin(base_url, url), callback=self.parse_category)
            
    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        cat_key = hxs.select('//input[@id="hdnCatKey"]/@value').extract()
        
        pages = hxs.select('//a[contains(@class, "lblPgIng")]/@href').extract()
        categories = pages + hxs.select('//div[@class="SubCategoryList"]//a/@href').extract()
        categories += hxs.select('//ul[@class="leftNav"]//a/@href').extract()
        categories += hxs.select('//div[@id="BrandsList"]//a/@href').extract()
        for url in categories:
            yield Request(urljoin(base_url, url), callback=self.parse_category)
        
        for url in hxs.select('//li[@id="liProductList"]//a/@href').extract():
            yield Request(urljoin(base_url, url), callback=self.parse_product)
            
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        url = hxs.select('//link[@rel="canonical"]/@href').extract()[0]
        
        options = hxs.select('//div[@class="BBFLW100 pdSelections"]/select/option[@selected="selected"][@value="0"]')
        if options:
            for option in options.select('../option[@value!="0"]'):
                event = option.select('../@name').extract()[0]
                formdata = {
                    '__VIEWSTATE': hxs.select("//input[@id='__VIEWSTATE']/@value").extract()[0],
                    '__VIEWSTATEGENERATOR': hxs.select("//input[@id='__VIEWSTATEGENERATOR']/@value").extract()[0],
                    '__EVENTTARGET': event,
                    event: option.select('@value').extract()[0]
                    }
                yield FormRequest(url, formdata=formdata, callback=self.parse_product, dont_filter=True, meta={'event':event})
            return
            
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('url', '//link[@rel="canonical"]/@href')
        loader.add_xpath('name', '//h1[@id="h1ProdName"]/text()')
        loader.add_xpath('category', '//div[@id="Breadcrumb"]//span[@itemprop="title"]/text()[.!="Home" and .!="Offers"]')
        loader.add_xpath('image_url', '//img[@id="imgProdMainImg"]/@src')
        loader.add_xpath('brand', '//div[@id="pnlManufacturer"]/meta[@itemprop]/@content')
        loader.add_xpath('shipping_cost', '//div[@id="pdEstmtdDlvrDesc"]/ul[1]/li[@class="charges"]/text()')
        if not hxs.select('//div[@id="pdStock"]/span[text()="In Stock"]').extract():
            loader.add_value('stock', 0)
        loader.add_xpath('identifier', '//span[@id="lblProdCode"]/text()')
        loader.add_xpath('price', '//div[@id="pnlProdPriceNStock"]//span[@itemprop="price"]/text()')
        loader.add_xpath('sku', '//span[@id="lblProdCode"]/text()')
        
        item = loader.load_item()
        promotions = hxs.select('//div[@class="was-saveprice FL"]/style/text()').re('{content:"(.+)"}')
        if promotions:
            metadata = MetaData()
            metadata['Promotions'] = promotions[0]
            item['metadata'] = metadata
        yield item

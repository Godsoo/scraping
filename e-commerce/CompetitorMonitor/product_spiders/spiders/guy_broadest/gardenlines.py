import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from productloader import load_product
from scrapy.http import FormRequest
from product_spiders.items import ProductLoader, Product

from scrapy.exceptions import DontCloseSpider
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

class gardenlinesSpider(BaseSpider):

    name = "gardenlines.co.uk"
    allowed_domains = ["www.gardenlines.co.uk"]
    start_urls = ("http://www.gardenlines.co.uk/",)

    def __init__(self, *args, **kwargs):
        super(gardenlinesSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.process_subcategories, signals.spider_idle)

        self.subcategories = []

    def process_subcategories(self, spider):
        if spider.name == self.name:
            self.log("Spider idle. Processing subcategories")
            url = None
            if self.subcategories:
                url = self.subcategories.pop(0)

            if url:
                r = Request(url, dont_filter=True, callback=self.parse_subcat_after_brands, meta={'brand':''})
                self._crawler.engine.crawl(r, self)
                raise DontCloseSpider
    
    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        items = hxs.select("//div[@class='item-list']/ul/li/a/@href").extract()
                    
        for item in items:
            yield Request(urljoin_rfc(base_url,item), callback=self.parse_items)
            
    def parse_subcat(self,response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        content = hxs.select("//div[@class='Menu']/ul/li/ul[@class='SubMenu']/li")
        items = content.select(".//a/@href").extract()
                    
        for item in items:
            yield Request(urljoin_rfc(base_url,item), callback=self.parse_items)
            
    def parse_items(self,response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
 
        self.subcategories.append(response.url)

        brands = hxs.select('//h2[text()="Shop by brand"]/../div//a/@href').extract()
        for brand in brands:
            yield Request(urljoin_rfc(base_url,brand), callback=self.parse_brands, meta={'category_url': response.url})
 
    def parse_brands(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        items = hxs.select('//div[@class="prod-row-mid"]/h3/a/@href').extract()
        brand = hxs.select('//div[contains(@class, "current-search-item")]/ul/li/text()').extract()[-1]
        category = hxs.select('//div[contains(@class, "current-search-item")]/ul/li/text()').extract()[0]
        for item in items:
            yield Request(urljoin_rfc(base_url,item), callback=self.parse_item, meta={'brand':brand, 'category':category})
        next_page = hxs.select('//li[contains(@class, "pager__item--next")]/a/@href').extract()
        if next_page:
	    yield Request(urljoin_rfc(base_url, next_page[0]), callback=self.parse_brands)

    def parse_subcat_after_brands(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        items = hxs.select('//div[@class="MoreInfo"]/p/a/@href').extract()
        for item in items:
            yield Request(urljoin_rfc(base_url,item), callback=self.parse_item, meta={'brand':''})
        
            
    def parse_item(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select('//h1/text()').extract()
        image_url = hxs.select('//a[@id="cloud-zoom"]/@href').extract()
        category = response.meta['category']
        
        url = response.url
        price = hxs.select('//div[contains(@class, "commerce-price")]/div[@class="field__items"]/div/text()').extract()

        l = ProductLoader(item=Product(), response=response)
        l.add_value('name', name)        
        l.add_value('url', url)
        l.add_value('image_url', image_url)
        l.add_value('category', category)
        l.add_value('identifier', response.url.split('/')[-1])
        l.add_value('brand', response.meta['brand'])
        l.add_value('price', price)
        out_of_stock = 'OUT OF STOCK' in ''.join(hxs.select('//h6[@itemprop="description"]/strong/text()').extract()).upper()
        if out_of_stock:
            l.add_value('stock', 0)
        yield l.load_item()

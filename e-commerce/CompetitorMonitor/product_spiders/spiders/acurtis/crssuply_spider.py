import os
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

#from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class CrssupplySpider(BaseSpider):
    name = 'crssupply.com'
    allowed_domains = ['crssupply.com']
    start_urls = ['http://crssupply.com/', 'http://crssupply.com/sitemap.php']

    def __init__(self, *a, **kw):
        super(CrssupplySpider, self).__init__(*a, **kw)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

        self.big_categories_parsed = False

    def spider_idle(self, spider):
        """
        Runs after all pages and items processed but before closing
        Populates all 'out of stock' items as they were just stored in attribute
        """
        self.log("Spider idle")

        #request = Request('http://crssupply.com/sitemap.php', callback=self.parse_sitemap)

        #if not self.big_categories_parsed:
        #    self.big_categories_parsed = True
        #    request = Request(self.start_urls[0], dont_filter=True, callback=self.parse2)
        #    self._crawler.engine.crawl(request, self)

    #def parse(self, response):
    #    hxs = HtmlXPathSelector(response)
    #    categories = hxs.select('//div[@class="mainNav"]/ul/li/ul/li/a')
    #    for category in categories:
    #        url = urljoin_rfc(get_base_url(response), category.select('@href').extract()[0])
    #        yield Request(url, callback=self.parse_category, meta={'category':category.select('text()').extract()})

    def parse2(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//div[@class="mainNav"]/ul/li[not(@class) or @class!="cart"]/a')
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category.select('@href').extract()[0])
            yield Request(url, callback=self.parse_category, meta={'category':category.select('text()').extract()})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        for url in hxs.select("//div[@class='middle']/li//a/@href").extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="productsWrap"]/div/div[@class="item " or @class="item end"]')
        for product in products:
            url = urljoin_rfc(get_base_url(response), product.select('a[not(@class)]/@href').extract()[0])
            yield Request(url, callback=self.parse_product)

        pagination = hxs.select('//div[@class="barTop"]/ul/li')
        if pagination:
            next = pagination[-1].select('a/@href').extract()
            if next:
                url =  urljoin_rfc(get_base_url(response), next[0])
                yield Request(url, callback=self.parse_category)

        sub_categories = hxs.select('//div[@class="left"]/div/a[not(@class="back")]')
        if sub_categories:
            for sub_category in sub_categories:
                url =  urljoin_rfc(get_base_url(response), sub_category.select('@href').extract()[0])
                yield Request(url, callback=self.parse_category)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        log.msg('PRODUCT')
        loader = ProductLoader(item=Product(), response=response)
        image = hxs.select('//a[@id="mainImageLink"]/img/@src').extract()[0]
        category = hxs.select("//div[@id='bcrumb']/a[last()]/text()").extract()
        if category:
            category = category[0]
        else:
            category = None
        loader.add_value('image_url', urljoin_rfc(get_base_url(response), image))
        loader.add_value('category', category)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//div[@class="details"]/h1/text()')
        loader.add_xpath('sku', '//div[@class="details"]/span[@class="model"]/text()')
        identifier = hxs.select('//input[@name="pid"]/@value').extract()
        identifier = identifier[0] if identifier else response.url.split('p-')[1].split('-')[0]
        loader.add_value('identifier', identifier)
        price = hxs.select('//div[@class="details"]/span[@class="price"]/text()').extract()
        if price:
            price = price[0]  
        else:
            price = 0
        loader.add_value('price', price)
        out_of_stock = hxs.select('//div[@class="product-not-available"]')
        if out_of_stock:
            loader.add_value('stock', 0)
        yield loader.load_item()

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher


class CommershusetSeSpider(BaseSpider):

    name = 'commershuset.se'
    allowed_domains = ['commershuset.se']
    start_urls = ('http://www.commershuset.se/leksaker/lego-byggsatser',)
    seen = []
    without_categories_crawled = False


    def __init__(self, *args, **kwargs):
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def spider_idle(self, spider):
        if not self.without_categories_crawled:
            self.without_categories_crawled = True
            self.crawler.engine.crawl(self.create_request(), spider)

    def create_request(self):
        return Request(url='http://www.commershuset.se/leksaker/lego-byggsatser?limit=100', callback=self.parse_products)


    def parse(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//h3[contains(text(),"kningen")]/following::div[1]//a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)


    def parse_category(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select("//div[@class='product-thumb']//h4")
        for product in products:
            url = product.select("./a/@href").extract()[0]
            price = product.select("./following::p[@class='price'][1]/text()").extract()[0]
            yield Request(urljoin_rfc(base_url, url), meta={'price': price}, callback=self.parse_product)

        #parse pagination
        urls = hxs.select('//a[text()=">"]/@href').extract()
        urls = list(set(urls)) if urls else ''
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)


    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_loader = ProductLoader(item=Product(), selector=hxs)

        product_name = hxs.select('//*[@id="content"]//h1/text()').extract()[0]
        identifier = hxs.select('//input[@name="product_id"]/@value').extract()
        identifier = identifier[0] if identifier else ''
        sku = hxs.select("//*[contains(text(),'Artikelnummer:')]/text()").extract()
        sku = sku[0].split(':')[1].strip() if sku else ''
        image_url = hxs.select('//a[@class="thumbnail"]/img/@src').extract()
        image_url = image_url[0] if image_url else ''
        price = response.meta.get('price')
        categories = hxs.select("//ul[@class='breadcrumb']/li/a/text()").extract()[1:-1]

        product_loader.add_value('image_url', image_url)
        product_loader.add_value('name', product_name)
        product_loader.add_value('url', response.url)
        product_loader.add_value('shipping_cost', '29')
        product_loader.add_value('identifier', identifier)
        product_loader.add_value('sku', sku)
        product_loader.add_value('price', extract_price(price))
        for category in categories:
            product_loader.add_value('category', category)


        product = product_loader.load_item()

        if not identifier in self.seen:
            self.seen.append(identifier)
            yield product



    def parse_products(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select("//div[@class='product-thumb']//h4")
        for product in products:
            url = product.select("./a/@href").extract()[0]
            price = product.select("./following::p[@class='price'][1]/text()").extract()[0]
            yield Request(urljoin_rfc(base_url, url), meta={'price': price}, callback=self.parse_product)

        #parse pagination
        urls = hxs.select('//a[text()=">"]/@href').extract()
        urls = list(set(urls)) if urls else ''
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products)

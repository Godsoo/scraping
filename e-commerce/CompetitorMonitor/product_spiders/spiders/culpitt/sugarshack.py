from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import DontCloseSpider


class SugarshackSpider(BaseSpider):
    name = 'sugarshack'
    allowed_domains = ['sugarshack.co.uk']
    start_urls = ('http://www.sugarshack.co.uk/',)
    ids = []

    def _start_requests(self):
        yield Request('http://www.sugarshack.co.uk/whats-cooking/brownies/wilton-drizzle-icing-tube-283g.html', callback=self.parse_product)

    def __init__(self, *args, **kwargs):
        super(SugarshackSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.process_subcategories, signals.spider_idle)

        self.subcategories = []

    def process_subcategories(self, spider):
        if spider.name == self.name:
            self.log("Spider idle. Processing subcategories")
            url = None
            if self.subcategories:
                url = self.subcategories.pop(0)
            if url:
                r = Request(url, callback=self.parse_list)
                self._crawler.engine.crawl(r, self)
                raise DontCloseSpider

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # parse categories
        urls = response.css('.level1').xpath('a/@href').extract()
        for url in urls:
            url = urljoin_rfc(base_url, url)
            if url not in self.subcategories:
                self.subcategories.append(url)
            # yield Request(urljoin_rfc(base_url, url), callback=self.parse_list)

    def parse_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # subcats
        urls = response.xpath('//*[@id="category-header"]//a/@href').extract()
        for url in urls:
            url = urljoin_rfc(base_url, url)
            if url not in self.subcategories:
                self.subcategories.append(url)
            # yield Request(urljoin_rfc(base_url, url), callback=self.parse_list)
        urls = response.css('.category-products').xpath('.//h2/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        if urls:
            # pagination
            urls = response.css('.pager').xpath('.//a/@href').extract()
            for url in urls:
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_name = hxs.select('//*[@id="product_addtocart_form"]//h1/text()').extract()[0].strip()
        image_url = response.css('.product-img-box').xpath('.//@src').extract_first()
        identifier = hxs.select('//*[@id="product_addtocart_form"]//input[@name="product"]/@value').extract()[0]
        category = response.xpath('(//ul[@id="breadcrumbs"]//a)[2]/text()').extract()

        options = response.css('.grouped-item')
        if not options:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('name', product_name)
            product_loader.add_value('url', response.url)
            product_loader.add_value('identifier', identifier)
            product_loader.add_xpath('sku', '//meta[@itemprop="sku"]/@content')
            price = hxs.select('//span[contains(@id, "product-price-' + identifier + '")]/span/text()').extract()
            if not price:
                price = hxs.select('//span[contains(@id, "product-price-' + identifier + '")]/text()').extract()
            if not price:
                price = ['']
            product_loader.add_value('price', extract_price(price[0]))
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))
            if category:
                product_loader.add_value('category', category[0])
            if response.css('.out-of-stock'):
                product_loader.add_value('stock', 0)
            if identifier not in self.ids:
                self.ids.append(identifier)
                product = product_loader.load_item()
                yield product
        else:
            for option in options:
                main_out_of_stock = response.css('.out-of-stock')
                product_loader = ProductLoader(item=Product(), selector=option)
                option_name = option.select('div[1]/text()').extract()[0].strip()
                if product_name not in option_name:
                    option_name = product_name + ' ' + option_name
                product_loader.add_value('name', option_name)
                product_loader.add_value('url', response.url)
                identifier = option.select('.//span/@id').re('product-price-(.+)')[0]
                product_loader.add_value('identifier', identifier)
                sku = response.xpath('//meta[@itemprop="sku"]/@content').extract_first()
                product_loader.add_value('sku', sku)
                price = option.css('.price').xpath('text()').extract()
                product_loader.add_value('price', price)
                if image_url:
                    product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))
                if category:
                    product_loader.add_value('category', category[0])
                out_of_stock = option.select('.//*[contains(., "SOLD OUT")]')
                if main_out_of_stock or out_of_stock:
                    product_loader.add_value('stock', 0)
                if identifier not in self.ids:
                    self.ids.append(identifier)
                    product = product_loader.load_item()
                    yield product

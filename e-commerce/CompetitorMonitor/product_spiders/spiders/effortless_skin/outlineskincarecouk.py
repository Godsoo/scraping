from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import DontCloseSpider

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.primary_spider import PrimarySpider

from scrapy import log


class OutlineSkinCareSpider(PrimarySpider):
    name = 'outlineskincare.co.uk'
    allowed_domains = ['outlineskincare.co.uk']
    start_urls = ('http://www.outlineskincare.co.uk/catalog/seo_sitemap/product/',)

    errors = []

    csv_file = 'outlineskincare_crawl.csv'

    def __init__(self, *args, **kwargs):
        super(OutlineSkinCareSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.process_sitemap, signals.spider_idle)

        self.sitemap = ['http://www.outlineskincare.co.uk/catalog/seo_sitemap/product/']

    def process_sitemap(self, spider):
        if spider.name:
            self.log("Spider idle. Processing sitemap")
            url = None
            if self.sitemap:
                url = self.sitemap.pop(0)
            if url:
                r = Request(url, callback=self.parse_sitemap)
                self._crawler.engine.crawl(r, self)
                raise DontCloseSpider

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//li[a/span[contains(text(), "Browse by Brand")]]/div/div/ul/li/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), self.parse_products)

    def parse_sitemap(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        products_links = hxs.select('//ul[@class="sitemap"]//li/a/@href').extract()

        for product_url in products_links:
            yield Request(add_or_replace_parameter(urljoin_rfc(base_url, product_url), 'limit', 'all'),
                          callback=self.parse_product, meta={'sitemap': True})

        pages = hxs.select('//div[@class="pager"]//div[@class="pages"]//li/a/@href').extract()
        for url in pages:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_sitemap, meta={'sitemap': True})

    def parse_products(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        brand = response.meta.get('brand', None)
        if not brand:
            brand = hxs.select('//div[@class="page-title category-title"]/h1/text()').extract()[0]

        sorter = hxs.select('//div[@class="sorter"]')
        if not sorter:
            categories = hxs.select('//h2[@class="product-name"]/a/@href').extract()
            for category in categories:
                yield Request(category, callback=self.parse_products, meta={'brand': brand})

        products = hxs.select('//h2[@class="product-name"]/a/@href').extract()
        for product in products:
            yield Request(product, callback=self.parse_product, meta={'brand': brand})

        next = hxs.select('//li[@class="next"]/a/@href').extract()
        if next:
            yield Request(next[0], callback=self.parse_products)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        meta = response.meta

        try:
            identifier = hxs.select('//form[@id="product_addtocart_form"]//input[@name="product"]/@value').extract()[0]
            name = hxs.select('//div[@class="product-name"]/h1/text()').extract()[0].strip()
        except:
            # self.errors.append('WARNING: No name o No identifier in %s' % response.url)
            return

        try:
            category = hxs.select('//div[contains(@class, "breadcrumbs")]/ul/li/a/text()').extract()[-1].strip()
        except:
            category = None

        in_stock = True
        call2purchase = hxs.select('//div[contains(@class, "product-shop")]/a[contains(@alt, "Call to purchase") and contains(@href, "tel://")]')
        if not call2purchase:
            stock_ = hxs.select('//div[@class="product-type-data"]/p[contains(@class, "availability") and contains(@class,"in-stock")]')
            if not stock_:
                in_stock = False
                name = name + ' (Out of stock)'
        else:
            name = name + ' (Call for price)'

        price = hxs.select('//span[@id="product-price-%s"]/span[@class="price"]/text()' % identifier).extract()
        if not price:
            price = hxs.select('//span[@id="product-price-%s"]/text()' % identifier).extract()
        if not price:
            price = '0.00'
        else:
            price = price[0]

        if meta.get('sitemap', False):
            brand = hxs.select("//div[@class='box-brand']/a/img/@alt").extract()
            if brand:
                brand = brand[0]
            else:
                brand = ''
        else:
            brand = meta.get('brand', None)

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('identifier', identifier)
        loader.add_value('brand', brand)
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_xpath('image_url', '//div[contains(@class, "product-img-box")]//a[@id="zoom1"]/img/@src')
        loader.add_value('price', price)
        if category:
            loader.add_value('category', category)
        if not in_stock:
            loader.add_value('stock', 0)

        yield loader.load_item()

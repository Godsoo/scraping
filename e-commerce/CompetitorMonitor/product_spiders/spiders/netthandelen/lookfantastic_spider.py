from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class LookFantasticSpider(BaseSpider):
    name = 'lookfantastic.com'
    allowed_domains = ['lookfantastic.com']
    start_urls = ['http://www.lookfantastic.com/home.dept?switchcurrency=EUR']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories = hxs.select('//nav//a/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category),
                          callback=self.parse_page)

    # Can either a subcategory or product listing page
    def parse_page(self, response):
        hxs = HtmlXPathSelector(response)

        # Try to find products
        products = hxs.select('//div[@id="divSearchResults"]//div[contains(@class, "item")]//p[@class="product-name"]/a/@href').extract()
        if products:
            category = hxs.select('//div[@class="panel-head"]//h1[@class="tl-title"]/span/text()').extract()[0].strip()
            for url in products:
                yield Request(urljoin_rfc(response.url, url),
                              callback=self.parse_product,
                              meta={'category': category})

            next = hxs.select('//div[@id="hrefNext"][1]/a/@href').extract()
            if next:
                yield Request(urljoin_rfc(response.url, next[0]), callback=self.parse_page)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        name = hxs.select(u'//span[@itemprop="name"]/text()').extract()[0].strip()
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('identifier', response.url.split('/')[-1].split('.')[0])
        product_loader.add_value('url', response.url)
        product_loader.add_value('name', name)
        product_loader.add_xpath('brand', u'//meta[@itemprop="brand"]/@content')
        product_loader.add_xpath('price', u'//span[@itemprop="price"]/text()')
        product_loader.add_value('sku', response.url.split('/')[-1].split('.')[0])
        product_loader.add_value('category', response.meta.get('category'))
        img = hxs.select(u'//a/img[@class="product-img"]/@src').extract()
        if img:
            product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        yield product_loader.load_item()

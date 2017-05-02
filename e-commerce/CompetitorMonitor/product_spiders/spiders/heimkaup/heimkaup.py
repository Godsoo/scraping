# -*- coding: utf-8 -*-
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.prodcache import ProductCacheSpider

from heimkaupitems import HeimkaupMeta, HeimkaupProduct as Product

from hashlib import md5


class HeimkaupSpider(ProductCacheSpider):
    name = 'heimkaup'
    allowed_domains = ['heimkaup.is']

    start_urls = ('https://www.heimkaup.is/product/product-prices/?u=bot&p=omin1N',)

    cost_prices = {}

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        self.cost_prices = {p.select('td[1]/text()').extract()[0]: p.select('td[2]/text()').extract()[0] for p in hxs.select('//tr')}
        yield Request('http://heimkaup.is', callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)

        for cat in hxs.select('//ul[@id="big-menu"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse_cat)

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)

        for productxs in hxs.select('//div[contains(@class, "box-product")]'):
            product = Product()
            product['price'] = extract_price_eu(''.join(productxs.select('.//div[contains(@class,"product-price")]/strong/text()').extract()))

            request = Request(urljoin_rfc(get_base_url(response), productxs.select('.//a/@href').extract()[0]), callback=self.parse_product, meta=response.meta)
            yield self.fetch_product(request, self.add_shipping_cost(product))

        for page in hxs.select('//div[@class="paginator"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), page), callback=self.parse_cat)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=response.meta.get('product', Product()), selector=hxs)
        
        try:
            product_id = hxs.select('//form/input[@name="id"]/@value').extract()[-1]
        except IndexError:
            product_id = None

        loader.add_value('identifier', md5(response.url.replace('https', 'http')).hexdigest())
        sku = response.xpath(u'//div[@class="detail-part-info"]//label[text()="Vörunúmer"]/following-sibling::span/text()').extract_first()
        loader.add_value('sku', sku)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//div[@id="productitem-detail"]/h1/text()')
        loader.add_value('category', [x.strip() for x in hxs.select('//div[@class="breadcrumbs"]/a[position()>1]/text()').extract()])

        img = hxs.select('//img[@id="main_image"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_xpath('brand', 'normalize-space(//label[contains(text(),"Framlei")]/following-sibling::span/a/text())')

        in_stock = response.xpath('//div[contains(@itemtype, "Product")]//link[@itemprop="availability" and contains(@href,"InStock")]')
        if not in_stock:
            loader.add_value('stock', 0)

        item = loader.load_item()
        try:
            metadata = item['metadata']
        except KeyError:
            metadata = HeimkaupMeta()
        metadata['cost_price'] = str(self.cost_prices.get(str(product_id), ''))
        if product_id is not None:
            metadata['vid'] = product_id
        item['metadata'] = metadata

        yield self.add_shipping_cost(item)

    def add_shipping_cost(self, item):
        item['shipping_cost'] = 0
        return item

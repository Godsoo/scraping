# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc


class PullingersSpider(BaseSpider):
    name = u'pullingers.com'
    allowed_domains = ['www.pullingers.com']
    start_urls = ('http://www.pullingers.com', )

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        urls = hxs.select('//ul[@id="headNav"]/li/h2/a/@href').extract()
        for url in urls[1:]:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        urls = hxs.select('//div[@id="departmentContainer"]//div[@class="shopnow"]/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url + "?sort=salesrank&pagerSubmit1=True&pageSize1=9999&pagerListingType1=DEPT&pagerProductTemplateID1=1"),
                          method="GET",
                          callback=self.parse_categories)
        urls = hxs.select('//div[@class="productsContainer"]//div[@class="productstampdesc"]/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        url = urljoin_rfc(base_url, response.url)
        image_url = hxs.select('//*[@id="pict-1"]/img/@src').extract()
        category = hxs.select('//*[@id="global"]//div[@class="breadcrumbs"]/a[2]/text()').extract()
        prod_info = hxs.select('//div[@class="producttext"]/span/text()').extract()
        prod_sku = prod_info[0]
        brand = prod_info[1]
        options = hxs.select('//*[@id="catMatrixScroll"]/ul/li')
        if options:
            for option in options:
                loader = ProductLoader(item=Product(), selector=option)
                identifier = option.select('.//input[@name="cm_pid"]/@value').extract()[0]
                loader.add_value('identifier', identifier)
                name = option.select('.//div[@class="matrix_text"]/text()').extract()[0].strip()
                loader.add_value('url', url)
                loader.add_value('name', name)
                if image_url:
                    loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                if category:
                    loader.add_value('category', category[0])
                price = option.select('.//div[@class="matrix_price"]/p[2]/text()').extract()[0]
                price = extract_price(price.replace(u'\xa3', ''))
                loader.add_value('price', price)
                try:
                    sku = option.select('.//div[@class="matriximage"]/img/@src').extract()[0]
                    sku = sku.partition('small__')[2].replace('.jpg', '').strip()
                    if sku == '':
                        raise
                except:
                    sku = prod_sku
                loader.add_value('sku', sku)
                loader.add_value('brand', brand)
                stock = option.select('.//div[@class="matrix_stock"]/text()')
                if stock:
                    loader.add_value('stock', 0)
                if price <= 44.99:
                    loader.add_value('shipping_cost', 3.95)
                else:
                    loader.add_value('shipping_cost', 0)
                yield loader.load_item()
        else:
            loader = ProductLoader(item=Product(), selector=hxs)
            name = hxs.select('//*[@id="pageH1"]/h1/text()').extract()[0].strip()
            loader.add_value('url', url)
            loader.add_value('name', name)
            if image_url:
                loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            if category:
                    loader.add_value('category', category[0])
            price = hxs.select('//*[@id="pinc"]/text()').extract()[0]
            price = extract_price(price.replace(u'\xa3', ''))
            loader.add_value('price', price)
            identifier = hxs.select('//*[@id="id"]/@value').extract()[0]
            loader.add_value('identifier', identifier)
            loader.add_value('sku', prod_sku)
            loader.add_value('brand', brand)
            stock = ''.join(hxs.select('//*[@id="psm"]/@class').extract()).strip()
            if stock == 'oos':
                loader.add_value('stock', 0)
            if price <= 44.99:
                loader.add_value('shipping_cost', 3.95)
            else:
                loader.add_value('shipping_cost', 0)
            yield loader.load_item()

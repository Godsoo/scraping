# -*- coding: utf-8 -*-

from scrapy.spider import Spider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request, FormRequest
from scrapy.utils.response import get_base_url

from urlparse import urljoin
from product_spiders.utils import extract_price, fix_spaces

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class CostcoSpider(Spider):
    name = "legocanada-costco.ca"
    allowed_domains = ["costco.ca"]
    start_urls = ["http://www.costco.ca/CatalogSearch?storeId=10302&catalogId=11201&langId=-24&refine=&keyword=lego"]
  
    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        pages = hxs.select('//div[@class="pagination"]/ul/li/a/@href').extract()
        for page in pages:
            yield Request(urljoin(base_url, page), meta={'cookiejar': 1})

        products = response.css('.product-list a')
        for product in products:
            price = product.css('div.price::text').extract_first()
            url = product.css('::attr(href)').extract_first()
            yield Request(response.urljoin(url), 
                          callback=self.parse_product, 
                          meta={'price': price})

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response=response)

        loader = ProductLoader(selector=hxs, item=Product())

        name = response.xpath('//h1/text()').extract_first()
        name = fix_spaces(name)
        loader.add_value('name', name)
        loader.add_value('url', response.url)

        loader.add_value('price', response.meta['price'])

        img_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        if img_url:
            loader.add_value('image_url', urljoin(base_url, img_url[0]))

        loader.add_value('category', 'Lego')
        loader.add_value('brand', 'Lego')

        identifier = hxs.select('//div[@class="scProdId"]/@sc.prodid').extract()

        if not identifier:
            log.msg('ERROR >>> Product without identifier: ' + response.url)
            return

        loader.add_value('identifier', identifier[0])

        sku = response.css('span.data-model-number::text').extract_first()
        loader.add_value('sku', sku)

        
        if loader.get_output_value('price')<=0:
            loader.add_value('stock', 0)

        yield loader.load_item()

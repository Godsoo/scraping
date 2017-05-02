# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector, Selector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc


class VseinstrumentiRuSpider(BaseSpider):
    name = u'vseinstrumenti_ru'
    allowed_domains = ['vseinstrumenti.ru']
    start_urls = [
        'http://www.vseinstrumenti.ru/map.html'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for cats in hxs.select('//div[@class="content"]//ul[@class="subcats"]/li'):
            urls = cats.select('.//ul/li/a/@href')
            if urls:
                for url in urls.extract():
                    yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)
            else:
                url = cats.select('./a/@href').extract()
                if url:
                    yield Request(urljoin_rfc(base_url, url[0]), callback=self.parse_products_list)
                

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        category = hxs.select('//div[@class="content"]//h1/text()')
        if category:
            category = ''.join(category.extract()).strip()
        else:
            category = ''.join( hxs.select('//div[@class="nav"]/following-sibling::div[contains(@class, "c-gray3")]/text()').extract()).strip()


        product_urls = hxs.select('//div[@class="catalogItemName"]/a/@href').extract()
        product_urls += hxs.select('//div[@class="content"]//ul[@id="goodsListing"]/li[@itemprop="itemListElement"]//a[@itemprop="url"]/@href').extract()
        for url in product_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'category': category})
        pages = hxs.select('//div[contains(@class, "commonPagination")]')
        if pages:
            for url in pages[0].select('.//a/@href').extract():
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_data = hxs.select('//div[@id="goodCard"]').extract()
        if product_data:
            for product in self.parse_product_data(response.url, product_data[0], response.meta['category']):
                yield product

    def parse_product_data(self, url, product_data, category):
        hxs = Selector(text=product_data)
        image_url = hxs.select('//a[@data-type="imageGoods"]/@data-src-source').extract()
        product_identifier = hxs.select('//input[@name="vote-id"]/@value').extract()
        product_sku = hxs.select('//span[contains(@class, "codeToOrder")]/text()').extract()
        if not product_sku:
            return
        product_identifier = product_identifier[0].strip()
        product_name = hxs.select('//h1[@itemprop="name"]/text()').extract()[0].strip()
        brand = hxs.select('//div[@class="nav"]/div//span[@itemprop="title"]/text()').extract()
        brand = brand[-1].strip() if brand else ''

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('identifier', product_identifier)
        product_loader.add_value('name', product_name)
        product_loader.add_value('sku', product_sku)
        if image_url:
            product_loader.add_value('image_url', image_url[0])

        price = hxs.css('.price-value::text').extract()
        if not price:
            price = hxs.select('//div[contains(@class, "goodBlock")]//td[contains(@class, "c-price")]//span/text()').extract()

        if price:
            product_loader.add_value('price', price[0].strip().replace(" ",""))
        else:
            product_loader.add_value('price', 0)

        product_loader.add_value('url', url)
        product_loader.add_value('brand', brand)
        product_loader.add_value('category', category)
        product = product_loader.load_item()
        yield product

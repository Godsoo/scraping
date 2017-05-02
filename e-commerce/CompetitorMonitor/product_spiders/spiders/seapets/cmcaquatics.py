# -*- coding: utf-8 -*#
from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoader

class CmcaquaticsSpider(BaseSpider):
    name = 'cmcaquatics'
    allowed_domains = ['cmcaquatics.co.uk']
    start_urls = [
        'http://www.cmcaquatics.co.uk/index.php?route=information/sitemap&view=desktop']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        urls = [x.strip() for x in hxs.select(
                ".//div[@class='sitemap-info']//ul/li/a/@href"
                ).extract() if x.strip()]
        for url in set(urls):
            yield Request(url, callback=self.parse_listing_page)

    def parse_listing_page(self, response):
        hxs = HtmlXPathSelector(response)
        product_urls = [x for x in hxs.select(
                ".//*[@class='name']//@href").extract() if x]
        if product_urls:
            for product_url in product_urls:
                yield Request(product_url, callback=self.parse_product_page)

            next_page = hxs.select(
                    "//*[contains(text(), '>')]/@href").extract()
            if next_page:
                yield Request(next_page[0], callback=self.parse_listing_page)

    def parse_product_page(self, response):
        hxs = HtmlXPathSelector(response)
        url = response.url
        if hxs.select("//div[@class='description']/span[text()='MPN: ']"):
            sku = hxs.select("//div[@class='description']").extract()[0].split('MPN: </span> ')[-1].split('<br>')[0]
        else:
            sku= ''
        name = ''.join(hxs.select(".//h1/text()").extract()).strip()
        price = ''.join(hxs.select(
                "//div[@class='product-info']//div[@class='price']/strong[@class='price-new']/text()"
                ).extract()).strip()
        if not price:
            price = ''.join(hxs.select(
                    "//div[@class='product-info']//div[@class='price']/span[@class='price-new']/text()"
                    ).extract()).strip()
        if not price:
            price = ''.join(hxs.select(
                    "//div[@class='price']/text()"
                    ).extract()).split(":")[1]
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('sku', sku)
        identifier = hxs.select('//div[@class="cart"]/div/input[@name="product_id"]/@value').extract()[0]
        loader.add_value('identifier', identifier)
        loader.add_value('name', name)
        loader.add_value('url', url)
        loader.add_value('price', price)
        yield loader.load_item()

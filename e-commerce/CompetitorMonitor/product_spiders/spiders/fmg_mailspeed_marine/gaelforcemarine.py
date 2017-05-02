# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import Request, FormRequest
import re, json, logging


class GaelforcemarineSpider(BaseSpider):

    name = "gaelforcemarine"
    allowed_domains = ["gaelforcemarine.co.uk"]
    start_urls = ["http://www.gaelforcemarine.co.uk/SearchResults.aspx?Search="]
    base_url = "http://www.gaelforcemarine.co.uk"

    download_delay = 1
    seen = []


    def start_requests(self):
        yield Request('http://www.gaelforcemarine.co.uk/SetProperty.aspx?languageiso=en&currencyiso=GBP&shippingcountryid=1903')

    def parse(self, response):
        url = "http://www.gaelforcemarine.co.uk/SearchResults.aspx?Search="
        yield Request(url=url, callback=self.parse_page)


    def parse_page(self, response):

        hxs = HtmlXPathSelector(response=response)
        products = hxs.select("//table[@id='ProductDataList']//td[contains(@id,'ModelImageCell')]")

        for product in products:
            try:
                url = self.base_url + product.select(".//a/@href").extract()[0]
                yield Request(url=url, callback=self.parse_item)
            except:
                pass

        try:
            next_page = self.base_url + hxs.select("//a[@title='Go to Next Page']/@href").extract()[0]
            yield Request(next_page, callback=self.parse_page)
        except:
            pass



    def parse_item(self, response):

        hxs = HtmlXPathSelector(response)
        url = response.url

        brand = ''.join(hxs.select("//span[@itemprop='brand']/span/text()").extract())
        name = brand + ' ' + ''.join(hxs.select("//h1/span[@itemprop='name']/text()").extract()).strip()
        category = ''.join(hxs.select("//td[@class='right-links']/a[1]/text()").extract()).strip().replace('See All', '').strip()
        image_url = ''.join(hxs.select("//div[@id='DivModelImage']//img[1]/@src").extract())
        options = hxs.select("//div[@class='add-to-basket-container']//tr[contains(@class,'item-row')]")

        for option in options:

            l = ProductLoader(item=Product(), response=response)

            option_sku = ''.join(option.select("./td[1]/text()").extract()).strip()
            option_name = ''.join(option.select("./td[3]/a/text()").extract()).strip()
            if option_sku:
                stock = ''.join(option.select("./td[2]").extract()).strip()
                stock = 1 if 'stock' in stock.lower() or 'available' in stock.lower() else 0

                try:
                    price = ''.join(option.select("./td[4]//span[@class='price-label']/text()").extract()).strip()[1:]
                    if not price:
                        price = ''.join(option.select("./td[4]//span[@class='foreign-price-label']/text()").extract()).strip()[1:]
                    if not price:
                        price = hxs.select('//span[@itemprop="price"]/text()').extract()[0]
                    l.add_value('price', price)
                except:
                    pass

                l.add_value('brand', brand)
                l.add_value('name', "%s %s" %(name, option_name))
                l.add_value('category', category)
                l.add_value('image_url', image_url)
                l.add_value('url', url)
                l.add_value('stock', stock)
                l.add_value('sku', option_sku)
                l.add_value('identifier', option_sku)

                if not option_sku in self.seen:
                    self.seen.append(option_sku)
                    yield l.load_item()

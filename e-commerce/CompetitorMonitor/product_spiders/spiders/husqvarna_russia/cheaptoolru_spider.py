# -*- coding: utf-8 -*-
import re

from scrapy.contrib.spiders import CrawlSpider
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import ProductLoader, Product


class CheaptoolruSpider(CrawlSpider):
    name = 'cheaptoolru'
    base_address = 'http://cheaptool.ru'
    allowed_domains = ['cheaptool.ru']
    start_urls = ['http://www.cheaptool.ru']
    category_start_index = 12
    min_price_for_free_shipping = 10000
    shipping_price = 400

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        for pcategory_url_raw in hxs.select("//div[@class='cpt_category_tree']//ul//li[@class='parent']//div//ul//li/a/@href"):
            pcategory_url = pcategory_url_raw.extract()
            if '?categoryID=' in pcategory_url:
                cat_id = pcategory_url[self.category_start_index:]
                url = "{}/category/{}/all".format(self.base_address, cat_id)
            else:
                url = "{}{}all".format(self.base_address, pcategory_url)

            yield Request(url=url, callback=self.parse_child_category)            

    def parse_child_category(self, response):
        hxs = HtmlXPathSelector(response)
        for product_url in hxs.select("//div[@id='main']//table//ul[@class='product_list']//li//div[@class='prod_box']//div[@class='name']/a/@href"):
            url = "{}{}".format(self.base_address, product_url.extract())
            yield Request(url=url, callback=self.parse_item)

    def parse_item(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)
        sku = hxs.select('//div[@class="prd-code"]/span/text()').extract()[0]
        loader.add_value('sku', sku)
        price_raw = hxs.select('//input[@class="product_price"]/@value')
        if len(price_raw) != 0:
            price = float(''.join(re.findall(r'\d+', price_raw.extract()[0])))
            loader.add_value('price', price)
            # loader.add_value('currency', 'RUR')
            # In stock
            loader.add_value('stock', None)
            loader.add_value('shipping_cost', self.get_shipping_price(price))
        else:
            # Out of stock
            loader.add_value('stock', 0)
            loader.add_value('price', 0.0)
            loader.add_value('shipping_cost', None)

        category = hxs.select('//div[@id="main"]//div[@class="cpt_maincontent"]//div[@class="cpt_product_category_info"]//tr/td//a/text()')
        category1 = category.extract()[1]
        category2 = category.extract()[2]
        loader.add_value('category', category1)
        loader.add_value('category', category2)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//div[@id="product_info_main"]//h1/text()')
        id1 = filter(None, response.url.rsplit('/'))[-1]
        identifier = hxs.select('//input[@name="productID"]/@value').extract()[0]
  #      loader.add_value('identifier', '{} {}'.format(sku.encode('utf-8'), id1))
        loader.add_value('identifier', identifier)
        image_url = hxs.select('//div[@id="product_info_main"]//img/@src').extract()[0]
        image_full_url = "{}/{}".format(self.base_address, image_url)
        loader.add_value('image_url', image_full_url)

        yield loader.load_item()
    
    def get_shipping_price(self, price):
        if price < self.min_price_for_free_shipping:
            return self.shipping_price
        else:
            return None

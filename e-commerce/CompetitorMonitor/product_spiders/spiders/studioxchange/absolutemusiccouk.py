import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader

class AbsolutemusicCoUk(BaseSpider):

    name = 'absolutemusic.co.uk'
    allowed_domains = ['absolutemusic.co.uk', 'www.absolutemusic.co.uk']
    start_urls = ('http://www.absolutemusic.co.uk/',)

    def parse(self, response):

        if not isinstance(response, HtmlResponse):
            return

        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//nav[@class="catagories-navigation"]//ul[@class="mega-menu-links"]//li/a')
        for cat in categories:
            cat_url = cat.select('@href').extract()[0]
            cat_name = cat.select('text()').extract()
            if cat_name:
                cat_name = cat_name[0].strip()
            else:
                cat_name = ""
            yield Request(urljoin_rfc(base_url, cat_url),meta={"cat_name": cat_name}, callback=self.parse_cat)
            #return

        return

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)

        #self.log("parse_cat: " + response.url)

        next_page = hxs.select('//ul[@class="page-numbers"]//a[@title="Next"]/@href').extract()
        if next_page:
            yield Request(next_page[0], meta={"cat_name": response.meta["cat_name"]}, callback=self.parse_cat)

        products = hxs.select('//ul[@id="products-list"]/li[contains(@class,"product")]/div[@class="product-img"]')

        for product in products:
            prod_url = product.select('.//a/@href').extract()
            prod_img = product.select('.//a/img/@src').extract()

            if not prod_url:
                self.log("ERROR prod_url not found")
                continue

            if not prod_img:
                self.log("ERROR prod_img not found")
                continue

            yield Request(url=prod_url[0],
                          meta={"img": prod_img[0], "cat_name": response.meta["cat_name"]},
                          callback=self.parse_product)

        return

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        #self.log("parse_product: " + response.url)

        price = 0

        special_price = hxs.select('//div[@id="product-info-panel-inner"]//p[@class="special-price"]/span[@class="price"]/text()').extract()
        regular_price = hxs.select('//div[@id="product-info-panel-inner"]//span[@class="regular-price"]/span[@class="price"]/text()').extract()
        if special_price:
            price = special_price[0].strip("\r\n\t ")
        elif regular_price:
            price = regular_price[0].strip("\r\n\t ")
        else:
            self.log("ERROR price not found")
            return

        name = hxs.select('//div[@id="product-info-panel-inner"]//h1[@itemprop="name"]/text()').extract()
        if not name:
            self.log("ERROR name not found")
            return

        sku=''
        product_code = hxs.select('//div[@id="product-info-panel-inner"]//div[@class="product-code"]/text()').extract()
        if product_code:
            code = product_code[0].strip("\r\n\t ")
            #Product code: seerfbun2
            m = re.search('((?<=\:)(.*))',code)
            if m:
                sku = m.group(1).strip()

        product_id = hxs.select('//input[@name="product"]/@value').extract()

        brand = hxs.select('//table[@id="product-attribute-specs-table"]//tr/td[contains(../th/text(),"Brand")]/text()').extract()

        category = hxs.select('(//div[@id="product-info-panel-inner"]/div[@class="breadcrumbs"]//li[contains(@class,"category")]/a/text())[position()=last()]').extract()


        #hxs.select('(//div[@id="product-info-panel-inner"]/div[@class="breadcrumbs"]/ul/li/a/text())[position()=last()]').extract()


        loader = ProductLoader(response=response, item=Product())

        loader.add_value('url', response.url)
        loader.add_value('name', name[0].strip())
        loader.add_value('price', price)
        loader.add_value('image_url', response.meta["img"])
        if sku:
            loader.add_value('sku', sku)
        if product_id:
            loader.add_value('identifier', product_id[0])
        if brand:
            loader.add_value('brand', brand[0].strip())
        if category:
            loader.add_value('category', category[0].strip())
        else:
            self.log("ERROR category not found")
            loader.add_value('category', response.meta["cat_name"])

        loader.add_value('shipping_cost',0)
        loader.add_value('stock',1)

        yield loader.load_item()

        return
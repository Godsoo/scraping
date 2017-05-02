# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
import re, json


class MarinesuperstoreSpider(BaseSpider):

    name              = "marinesuperstore"
    allowed_domains   = ["marinesuperstore.com"]
    start_urls        = ["http://www.marinesuperstore.com/brands"]
    base_url          = "http://www.marinesuperstore.com"

    download_delay    = 1


    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//div[@class="menuitem_panelcolumn"]/a/@href').extract()
        for category in categories:
            link  = self.base_url + category
            yield Request(url=link, callback=self.parse_products, meta={'brand':''})

        brands = hxs.select('//ul[@class="brand_list"]/li/a')
        for brand in brands:
            link  = self.base_url + brand.select('@href').extract()[0]
            yield Request(url=link, callback=self.parse_products, meta={'brand': brand.select('text()').extract()[0]})


    def parse_products(self, response):
        hxs = HtmlXPathSelector(response=response)
        base_url = get_base_url(response)

        products = hxs.select('//div[contains(@class, "product_panel")]/div/h2/a')

        for product in products:

            name  = ''.join(product.select("text()").extract()).strip()
            url   = self.base_url + product.select("@href").extract()[0]

            yield Request(url=url, meta={'name': name, 'brand': response.meta.get('brand', '')}, callback=self.parse_item)

        try:
            next_page = hxs.select('//a[@class="nav_next"]/@href').extract()[0]
            yield Request(urljoin_rfc(base_url, next_page), callback=self.parse_products, meta=response.meta)
        except:
            pass



    def parse_item(self, response):
        hxs   = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name  = response.meta.get('name', "")
        #name  = hxs.select('//span[@class="productName"]/text()').extract()[0].strip() if not name else name
        url   = response.url
        sku   = hxs.select('//div[@class="product_right"]/form/@action').re('partno=(.*)')[0].replace('+', '')
        brand = response.meta.get('brand', '')

        #category    = ''.join(hxs.select("//a[@class='category']/text()").extract()).strip()
        #subcategory = ''.join(hxs.select("//a[@class='subCategory']/text()").extract()).strip()
        categories  = hxs.select('//h1[@class="breadcrumb"]/a/text()').extract()
        image_url   = hxs.select('//div[@class="image-set"]/a/img/@src').extract()
        options     = hxs.select("//table[@id='prodt_table']//tr[contains(@class, 'pd')]")

        for option in options:

            l = ProductLoader(item=Product(), response=response)

            option_sku = ''.join(option.select("./td[2]/text()").extract()).strip().replace('-', '')
            option_name = ''.join(option.select("./td[1]/text()").extract()).strip().replace('-', '')

            try:
                price = ''.join(option.select("./td[4]/text()").extract()).strip()
                price = re.findall(re.compile('\d*\,*\d*\.*\d+'), price)[0]
                stock = 1 if price else 0
                out_of_stock = hxs.select('//p[@class="product_outofstock"]')
                if out_of_stock:
                    stock = 0
                l.add_value('price', price)
                l.add_value('stock', stock)
            except:
                pass

            if option_sku  == sku:
                l.add_value('sku', sku)
                l.add_value('identifier', sku)
            else:
                l.add_value('sku', sku)
                l.add_value('identifier', sku + '-' + option_sku)


            l.add_value('brand',      brand)
            l.add_value('name',       "%s %s" % (name, option_name))
            if image_url:
                l.add_value('image_url',  urljoin_rfc(base_url, image_url[0]))
            l.add_value('url',        url)

            for category in categories:
                l.add_value('category', category)

            yield l.load_item()

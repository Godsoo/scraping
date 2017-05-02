import json
import re

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import canonicalize_url

from product_spiders.items import Product, ProductLoader


class GppGolfSpider(BaseSpider):
    name = "gppgolf.com"
    allowed_domains = ["www.gppgolf.com", ]
    start_urls = [
        # "http://www.gppgolf.com/catalog/seo_sitemap/category/",
        "http://www.gppgolf.com/catalog/seo_sitemap/product/",
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        next_page = hxs.select(
            "//div[@class='pages']/ol/li/a[@title='Next']/@href"
        ).extract()
        if next_page:
            yield Request(
                url=canonicalize_url(next_page[0]),
                callback=self.parse)

        products = hxs.select(
            "//div[@class='page-sitemap']/ul[@class='sitemap']/li"
            "/a/@href").extract()
        log.msg(">>>>>>>> PRODUCTS >>> %s" % len(products))
        for product in products:
            yield Request(
                url=canonicalize_url(product),
                callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        # cat_name = response.meta["cat_name"]

        # Fill up the Product model fields
        #identifier =
        url = response.url
        name = hxs.select(
            "//div[@class='product-main-info']"
            "/div[@class='product-name']/h1/text()"
        ).extract()
        price = hxs.select(
            "//div[@class='product-main-info']/div"
            "/p[@class='special-price']/span[@class='price']/text()"
        ).extract()
        if not price:
            price = hxs.select(
                "//div[@class='product-main-info']/div/span"
                "/span[@class='price']/text()"
            ).extract()
            if not price:
                price = ''.join(hxs.select("//script[contains(text(),'Price = new')]/text()").extract())
                if price:
                    log.msg(' ::::: Base price :::::')
                    log.msg(response.url)
                    price = price.split('OptionsPrice(')[1].split(');')[0]
                    price = json.loads(price)
                    if price:
                        price = price.get('productPrice', '')
                    else:
                        ''
                else:
                    price = ''
        #sku =
        #metadata =
        #category = cat_name
        image_url = hxs.select(
            "//div[@class='product-img-box']/div/a/img/@src"
        ).extract()
        if not image_url:
            image_url = hxs.select(
                "//div[@class='product-img-box']/div/p/img/@src"
            ).extract()
            if not image_url:
                image_url = ""
        #brand =
        #shipping_cost =
        '''
        l = ProductLoader(response=response, item=Product())

        l.add_value('url', url)
        l.add_value('name', name)
        l.add_value('price', price)
        l.add_value('image_url', image_url)
        '''
        sku = hxs.select(
            '//table[@id="product-attribute-specs-table"]//tr[.//th[contains(text(),"SKU")]]/td[1]/text()').extract()
        if not sku:
            self.log("ERROR sku not found")
        else:
            sku = sku[0].strip()
            #l.add_value('sku', sku[0].strip())

        product_id = hxs.select('//input[@name="product" and @value!=""]/@value').extract()
        if not product_id:
            self.log("ERROR product id not found")
        else:
            identifier = product_id[0]
            #l.add_value("identifier",product_id[0])

        brand = hxs.select(
            '//table[@id="product-attribute-specs-table"]//tr[.//th[contains(text(),"Manufacturer")]]/td[1]/text()').extract()
        if not brand:
            self.log("ERROR brand not found")
        else:
            brand = brand[0].strip()
            #l.add_value("brand",brand[0].strip())

        shipping_cost = None
        free_shipping = hxs.select(
            '//table[@id="product-attribute-specs-table"]//tr[.//th[contains(text(),"Free Shipping")]]/td[1]/text()').extract()
        if free_shipping and free_shipping[0].strip() != "N/A" and free_shipping[0].strip() != "No":
            shipping_cost = "0"
            #l.add_value("shipping_cost","0")

        category = hxs.select('(//div[@class="breadcrumbs"]/ul/li/a/span/text())[position()=last()]').extract()
        if not category:
            self.log("ERROR category not found")
        else:
            category = category[0].strip()
            #l.add_value("category",category[0].strip())

        stock = None
        instock = hxs.select('//input[@id="qty"]').extract()
        if instock:
            stock = int(1)
            #l.add_value("stock", int(1))
        else:
            outofstock = hxs.select(
                '//div[@class="product-main-info"]/p[contains(@class,"availability") and contains(@class,"out-of-stock")]/span[contains(text(),"Out of stock")]').extract()
            if outofstock:
                stock = int(0)
                #l.add_value("stock", int(0))
            else:
                self.log("ERROR outofstock not found, instock not found")

        options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)
        if options_config:
            product_data = json.loads(options_config.groups()[0])
            products = {}
            prices = {}
            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' - '.join((products.get(product, ''), option['label']))
                        prices[product] = prices.get(product, 0) +  float(option['price'])


            for option_identifier, option_name in products.iteritems():
                l = ProductLoader(response=response, item=Product())
                if not isinstance(price, float) and not isinstance(price, int):
                    price = float(re.findall("\d+.\d+", price[0])[0])

                l.add_value("identifier", identifier + '-' + option_identifier)
                l.add_value('name', name[0] + option_name)
                l.add_value('image_url', image_url)
                l.add_value('price', price + prices[option_identifier])
                l.add_value('url', url)
                l.add_value("brand", brand)
                l.add_value('category', category)
                if stock is not None:
                    l.add_value("stock", stock)
                if shipping_cost:
                    l.add_value("shipping_cost", shipping_cost)
                product = l.load_item()
                yield product

        else:
            l = ProductLoader(response=response, item=Product())
            l.add_value('name', name)
            l.add_value('price', price)
            l.add_value("identifier", identifier)
            l.add_value("brand", brand)
            if shipping_cost:
                l.add_value("shipping_cost", shipping_cost)
            l.add_value('category', category)
            l.add_value('image_url', image_url)
            l.add_value('url', url)
            if stock is not None:
                l.add_value("stock", stock)
            yield l.load_item()

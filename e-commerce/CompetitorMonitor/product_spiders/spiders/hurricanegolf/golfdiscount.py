import urllib
import re
import ast

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, canonicalize_url
from urlparse import urlparse, parse_qs

from product_spiders.items import Product, ProductLoader


class GolfDiscountSpider(BaseSpider):
    name = "golfdiscount.com"
    allowed_domains = ["www.golfdiscount.com",]
    start_urls = [
        'http://www.golfdiscount.com/'
        ]

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # Dive in categories
        cats = hxs.select("//div[@class='nav-holder']/ul[@id='nav']/li")[1:]
        scats = cats.select(".//ul/li/a")
        for cat in scats:
            yield Request(
                url=canonicalize_url(urljoin_rfc(
                    base_url, cat.select(".//@href").extract()[0])),
                meta={"cat_name": cat.select(".//text()"
                    ).extract()[0].title()},
                callback=self.parse_cat)

    def parse_cat(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # Dive in next page, if it is
        next_page = hxs.select(
            "//div[@class='pagination']/a[@class='next_page']/@href"
            ).extract()
        if next_page:
            yield Request(
                url=canonicalize_url(urljoin_rfc(base_url, next_page[0])),
                meta={"cat_name": response.meta["cat_name"]},
                callback=self.parse_cat)

        # Dive in product, if it is
        products = hxs.select("//ul[@class='items-list']/li/div/a/@href"
            ).extract()
        if products:
            for product in products:
                yield Request(
                    url=canonicalize_url(urljoin_rfc(base_url, product)),
                    meta={"cat_name": response.meta["cat_name"]},
                    callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        cat_name = response.meta["cat_name"]

        # Fill up the Product model fields
        #identifier =
        url = response.url
        name = hxs.select(
            "//div[contains(@class, 'details')]/h1/text()"
            ).extract()[0].replace("-", " ").strip()
        price = hxs.select(
            "//div[@class='price-info']/strong[@id='price']/text()"
            ).extract()[0].strip()

        #sku =
        #metadata =
        category = cat_name
        image_url = hxs.select("//div[@class='main-image']/a/@href"
            ).extract()
        if not image_url:
            image_url = hxs.select("//div[@class='main-image']/img/@src"
                ).extract()
            if not image_url:
                image_url = ""
        brand = hxs.select(
            "//div[contains(@class, 'details')]/h1/strong/text()").extract()
        shipping_cost = hxs.select(
            "//dl[@class='blue']/dd/text()").extract()[0].strip()
        self.log(price)
        if 'Cart' in price:
            products = []
            for line in hxs.extract().split('\n'):
                if "Add to Cart" in line:
                    product = re.findall('"([A-Za-z0-9 _\./\\-]*)"', line)
                    if product:
                        products.append(product[:1] + product[3:])

            if products:

                self.log("products: " + str(products))
                yield Request(url, dont_filter=True, callback=self.parse_add_products, meta={'products':products,
                                                                           'url':url,
                                                                           'brand':brand, 
                                                                           'category':category})
        else:

            b_product_id = hxs.select('//input[@id="b_product_id"]/@value').extract()



            o = urlparse(url)
            params = parse_qs(o.query)

            cur_option_id = ""
            if "v" in params:
                self.log("option v found")
                cur_option_name = params["v"]
                if cur_option_name:
                    cur_option_id = cur_option_name[0].strip().lower()


            product_id = hxs.select('//input[@id="product_id"]/@value').extract()
            if not b_product_id:
                self.log("ERROR b_product id not found")
            else:

                res_product_id = (b_product_id[0] + " " + cur_option_id).strip()

                #l.add_value('identifier', res_product_id)

            size_option =  hxs.select('//fieldset/div/div[label/text()="\r\n                        \r\n                            Size:\r\n                        "]/select')
            if size_option:
                sizes = []
                for line in response.body.split('\n'):
                    if 'products[' in line and 'new Array' in line:
                        sizes.append(ast.literal_eval(line.split('Array')[-1].split(';')[0]))
                 
                for size in sizes:
                    l = ProductLoader(response=response, item=Product())
                    #l.add_value('identifier', identifier)
                    l.add_value('url', url)
                    l.add_value('name', name +' '+ size[3] + ' ' + size[4])
                    l.add_value('identifier', res_product_id+'-'+size[0])
                    l.add_value('price', size[1])
                    l.add_value('category', category)
                    l.add_value('image_url', image_url)
                    l.add_value('brand', brand)
                    l.add_value('shipping_cost', shipping_cost)

                    if size[1]:
                        l.add_value('stock','1')
                    else:
                        l.add_value('stock','0')

                    yield l.load_item()    
            else:
                l = ProductLoader(response=response, item=Product())
                #l.add_value('identifier', identifier)
                l.add_value('url', url)
                l.add_value('identifier', res_product_id)
                l.add_value('name', name)
                l.add_value('price', price)
                #l.add_value('sku', sku)
                #l.add_value('metadata', metadata)
                l.add_value('category', category)
                l.add_value('image_url', image_url)
                l.add_value('brand', brand)
                l.add_value('shipping_cost', shipping_cost)

                if price:
                    l.add_value('stock','1')
                else:
                    l.add_value('stock','0')
  
                yield l.load_item()

    def parse_add_products(self, response):
        hxs = HtmlXPathSelector(response)
        products = response.meta['products']
        if products:
            product_options = products[0]
            formdata = {}
            formdata['product_id'] = product_options[0] 
            formdata['quantity'] = '1'
            for i, option in enumerate(product_options[1:], 1):
                formdata['opt'+ str(i)] = option
            request = FormRequest.from_response(response, 
                                                formdata=formdata,
                                                formnumber=1,
                                                dont_filter=True,
                                                callback=self.parse_basket_product,
                                                meta={'url':response.meta['url'],
                                                      'category':response.meta['category'],
                                                      'image_url':'',
                                                      'brand':response.meta['brand'], 
                                                      'shipping_cost':'',
                                                      'products':products[1:],
                                                      'identifier':product_options[0]})
            self.log('Request for option: ' + str(product_options))
            yield request

    def parse_basket_product(self, response):
        hxs = HtmlXPathSelector(response)
        name = hxs.select('//table[@class="cart_table"]/tr/td/div/a/text()').extract()
        if not name:
            self.log("ERROR name not found")
            return
        else:
            name = name[0].strip()

        url = response.meta['url']
        price = hxs.select('//td[@class="moneyNumeric"]/text()').extract()[0] 
        category = response.meta['category']
        image_url = ''
        brand = response.meta['brand']
        shipping_cost = response.meta['shipping_cost']
        clean = 'http://www.golfdiscount.com/cart_items/remove_all'
        yield Request(clean, 
                      dont_filter=True, 
                      callback=self.parse_save_and_clean,
                      meta={'name':name,
                            'url':url,
                            'price':price,
                            'category':category,
                            'image_url':image_url,
                            'brand':brand,
                            'shipping_cost':shipping_cost, 
                            'products':response.meta['products'],
                            'identifier':response.meta['identifier']})

    def parse_save_and_clean(self, response):
        hxs = HtmlXPathSelector(response)
        if response.meta['name']:
            self.log("Product on the basket: " + response.meta['name'])
            l = ProductLoader(response=response, item=Product())
            l.add_value('url', response.meta['url'])
            l.add_value('name', response.meta['name'])
            l.add_value('price', response.meta['price'])
            l.add_value('category', response.meta['category'])
            l.add_value('image_url', '')
            l.add_value('brand', response.meta['brand'])
            l.add_value('shipping_cost', '')
            l.add_value('identifier', response.meta['identifier'])

            if response.meta['price']:
                l.add_value('stock','1')
            else:
                l.add_value('stock','0')

            yield l.load_item()
        if response.meta['products']:
            yield Request(response.meta['url'], 
                          dont_filter=True, 
                          callback=self.parse_add_products, 
                          meta={'products':response.meta['products'],
                                'url':response.meta['url'],
                                'brand':response.meta['brand'], 
                                'category':response.meta['category']})


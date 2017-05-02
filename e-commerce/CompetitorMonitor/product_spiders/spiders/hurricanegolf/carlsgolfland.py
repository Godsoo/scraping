import ast
import re
import json
import itertools

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from scrapy.exceptions import DontCloseSpider

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from urlparse import urljoin as urljoin_rfc
from scrapy import log
from product_spiders.items import Product, ProductLoader

from product_spiders.utils import extract_price
import logging


class LongMcQuadeSpider(BaseSpider):
    name = "carlsgolfland.com"
    allowed_domains = ["www.carlsgolfland.com", ]
    start_urls = [
        # "http://www.carlsgolfland.com/shop/",
        # "http://www.carlsgolfland.com/wilson-personalized-golf-balls",
        "http://www.carlsgolfland.com/puma-cuadrado-web-belt"
    ]

    concurrent_requests = 1

    def __init__(self, *args, **kwargs):
        super(LongMcQuadeSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.process_products, signals.spider_idle)

        self.collect_products = []
        self.sync_calls = False

    def process_products(self, spider):
        if spider.name == self.name:
            if self.collect_products and not self.sync_calls:
                self.sync_calls = True
                product = self.collect_products[0]

                meta = product
                meta['collect_products'] = self.collect_products[1:]

                req = FormRequest(
                    'http://www.carlsgolfland.com/shop/cart.php?mode=add',
                    # formname='orderform',
                    formdata=product['formdata'],
                    # dont_click=True,
                    dont_filter=True,
                    callback=self.parse_basket_product,
                    meta=meta
                )

                log.msg('SEND REQ')
                self._crawler.engine.crawl(req, self)
                raise DontCloseSpider

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # Dive in categories
        cats = hxs.select('//li[contains(@class, "navigation-top-item")]//a[@class="sub-category-anchor"]')
        for cat in cats:
            yield Request(
                url=urljoin_rfc(base_url, cat.select(".//@href").extract()[0]),
                meta={"cat_name": cat.select(".//text()").extract()[0].title()},
                callback=self.parse_cat
            )

    def parse_cat(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # Dive in subcategories
        subcats = hxs.select('//ul[@class="category-listing"]/li//p[@class="category-title"]/a')
        if subcats:
            for subcat in subcats:
                try:
                    yield Request(
                        url=urljoin_rfc(base_url, subcat.select(".//@href").extract()[0]),
                        meta={"cat_name": response.meta["cat_name"]},
                        callback=self.parse_cat)
                except:
                    continue

        next_page = hxs.select('//div[@class="pages"]//a[contains(@class, "next")]/@href').extract()
        if next_page:
            yield Request(
                url=urljoin_rfc(base_url, next_page[0]),
                meta={"cat_name": response.meta["cat_name"]},
                callback=self.parse_cat
            )

        products = hxs.select('//ul[contains(@class, "products-grid")]//h2/a/@href').extract()
        products += hxs.select('//ul[contains(@class, "products-grid")]//span[contains(@class,"product-name")]/a/@href').extract()
        if products:
            for product in products:
                yield Request(
                    url=urljoin_rfc(base_url, product),
                    meta={"cat_name": response.meta["cat_name"]},
                    callback=self.parse_product
                )

    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)

        cat_name = response.meta.get("cat_name")
        # Fill up the Product model fields

        brand = hxs.select('//div[@class="product-name"]/div[@class="brand-img"]/img/@alt').extract()
        if not brand:
            brand = ''
            self.log("ERROR brands not found")

        name = ''.join(hxs.select('//div[@class="product-name"]/div/h1/text()').extract())
        if not name:
            self.log("ERROR name not found")
            return

        url = response.url
        image_url = hxs.select('//div[@id="selector-target-image"]/a/img/@src').extract()
        image_url = image_url[0] if image_url else ''
        sku = ''.join(hxs.select('//p[@class="product-ids"]/text()').extract()).strip()
        identifier = hxs.select('//div[@class="product-view"]//input[@name="product"]/@value').extract()[0]

        options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)
        if options_config:
            product_data = json.loads(options_config.groups()[0])
            products = {}
            prices = {}
            colours = {}
            options_ids = {}
            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' - '.join((products.get(product, ''), option['label']))
                        prices[product] = prices.get(product, 0) + extract_price(option['price'])
                        options_ids[product] = option['id']

        if options_config:
            for option_identifier, option_name in products.iteritems():
                loader = ProductLoader(response=response, item=Product())

                loader.add_value("identifier", identifier + '-' + option_identifier)
                loader.add_value('name', name + option_name)
                loader.add_value('image_url', image_url)
#                loader.add_value('price', extract_price(product_data['basePrice']) + prices[option_identifier])
		price = hxs.select('//div[@id="child-price"]//span[@id="product-price-%s"]//text()' %option_identifier).extract()
		loader.add_value('price', price)
                loader.add_value('url', response.url)
                loader.add_value('brand', brand)
                loader.add_value('sku', sku)
                loader.add_value('category', cat_name)
                product = loader.load_item()
                if not product.get('price', None):
		    if not hxs.select('//div[@class="price-box-call"]'):
			product['price'] = extract_price(product_data['basePrice']) + prices[option_identifier]
			if product['price'] <= 99:
			    product['shipping_cost'] = 5.99
			yield product
		    else:
			product['price'] = None
			yield product
                    #product_id = hxs.select("//input[@name='product']/@value").extract()[0]
                    #super_attr = hxs.select("//*[contains(concat('',@name,''), 'super')]/@name").extract()
                    #if super_attr:
                        #url = 'http://www.carlsgolfland.com/ajaxcart/index/add?product={}&related_product=&qty=1'.format(
                            #option_identifier)
                    #else:
                        #url = 'http://www.carlsgolfland.com/ajaxcart/index/add?product={}&related_product=&qty=1'.format(
                            #option_identifier)
                    #yield Request(
                        #url=url,
                        #meta={'loader': loader},
                        #callback=self.parse_basket,
                        #dont_filter=True
                    #)
                else:
                    if product['price'] <= 99:
                        product['shipping_cost'] = 5.99
                    yield product

        else:
            self.log("no options")
            price = hxs.select('//div[@id="selector-target-price"]//span[@class="price"]/text()').extract()
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('url', url)
            loader.add_value('name', name)
            loader.add_value('sku', sku)
            loader.add_value('category', cat_name)
            loader.add_value('image_url', image_url)
            loader.add_value('identifier', identifier)
            loader.add_value('brand', brand)
            loader.add_value('shipping_cost', 0)
            loader.add_value('stock', "1")

            if not price:
                product_id = hxs.select("//input[@name='product']/@value").extract()[0]
                url = 'http://www.carlsgolfland.com/ajaxcart/index/add?product={}&related_product=&qty=1'.format(
                    product_id)
                yield Request(
                    url=url,
                    meta={'loader': loader},
                    callback=self.parse_basket,
                    dont_filter=True
                )

            else:
                loader.add_value('price', price)
                product = loader.load_item()

                if product['price'] <= 99:
                    product['shipping_cost'] = 5.99

                yield product

    def parse_basket(self, response):
        hxs = HtmlXPathSelector(response)
        loader = response.meta['loader']
        url = loader.get_collected_values('url')[0]
        price = hxs.select(
            '//a[@href="%s"]/../../td[contains(@class, "price")]/span[@class="price"]/text()' % url).extract()
        loader.add_value('price', price)

        yield Request(
            url='http://www.carlsgolfland.com/checkout/cart/',
            meta={'loader': loader},
            callback=self.basket_page,
            dont_filter=True
        )

    def basket_page(self, response):

        hxs = HtmlXPathSelector(response)
        loader = response.meta['loader']
        price = hxs.select('//td[@class="a-right wee"]//span/text()').extract()
        loader.add_value('price', price)
        form_key = ''.join(hxs.select("//input[@name='form_key']/@value").extract())
        yield FormRequest(
            url='http://www.carlsgolfland.com/checkout/cart/updatePost/',
            formdata={
                'update_cart_action': "empty_cart",
                'form_key': "{}".format(form_key)
            },
            meta={'loader': response.meta['loader']},
            callback=self.clear_basket,
            dont_filter=True
        )

    def clear_basket(self, response):

        loader = response.meta['loader']
        product = loader.load_item()
        
        if not product.get('price'):
	    product['price'] = None
	elif product['price'] <= 99:
            product['shipping_cost'] = 5.99

        yield product

    def parse_basket_product(self, response):
        hxs = HtmlXPathSelector(response)
        logging.error('=' * 20)
        logging.error(response.meta)
        logging.error(''.join(hxs.select('//font[@class="ProductPrice"]').extract()))
        name = ''.join(hxs.select('//font[@class="ProductTitle"]/text()').extract().extract()).strip()
        price = ''.join(hxs.select('//font[@class="ProductPrice"]/span/text()').extract()).strip()
        if name:
            log.msg("Product on the basket: " + name[0])
            l = ProductLoader(response=response, item=Product())

            selected_opt = hxs.select('//td[contains(b/text(), "Selected options:")]/table/tr/td/text()').extract()
            full_opt_desc = ' '.join(filter(None, map(lambda x: x.strip() if x else None, selected_opt))).strip()
            if full_opt_desc:
                l.add_value('name', name[0] + ' ' + full_opt_desc)
            else:
                l.add_value('name', name[0])
            l.add_value('url', response.meta['url'])
            l.add_value('price', price)
            l.add_value('sku', response.meta['sku'])
            l.add_value('category', response.meta['category'])
            l.add_value('image_url', response.meta['image_url'])

            if response.meta['brand']:
                l.add_value('brand', response.meta['brand'])

            option_id = response.meta.get('option_id', '')
            if option_id:
                l.add_value('identifier', response.meta['identifier'] + option_id)
            else:
                l.add_value('identifier', response.meta['identifier'])

            l.add_value('shipping_cost', 0)

            if price:
                l.add_value('stock', '1')
            else:
                l.add_value('stock', '0')

            product = l.load_item()

            if product['price'] <= 99:
                product['shipping_cost'] = 5.99

            yield product
            clean = 'http://www.carlsgolfland.com/shop/cart.php?mode=clear_cart'
            yield Request(
                clean,
                callback=self.parse_sync_basket,
                dont_filter=True,
                meta={'collect_products': response.meta['collect_products']}
            )

    def parse_sync_basket(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        meta = response.meta
        collect_products = meta['collect_products']
        if collect_products:
            product = collect_products[0]
            meta = product
            meta['collect_products'] = collect_products[1:]

            req = FormRequest(
                'http://www.carlsgolfland.com/shop/cart.php?mode=add',
                # formname='orderform',
                formdata=product['formdata'],
                # dont_click=True,
                dont_filter=True,
                callback=self.parse_basket_product,
                meta=meta
            )
            yield req

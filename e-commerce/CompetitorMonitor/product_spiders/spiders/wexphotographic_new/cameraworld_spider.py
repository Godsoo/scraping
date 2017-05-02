from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.url import add_or_replace_parameter, url_query_parameter
import json
import re
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price


class WexCameraWorldSpider(BaseSpider):
    name = 'wexphotographic_new-cameraworld.co.uk'
    allowed_domains = ['cameraworld.co.uk']
    start_urls = ('http://www.cameraworld.co.uk/new-equipment.html?infinitescroll=1&p=1',
                  'http://www.cameraworld.co.uk/bags-tripods-straps.html?infinitescroll=1&p=1',
                  'http://www.cameraworld.co.uk/accessories.html?infinitescroll=1&p=1')
    download_delay = 1

    def parse(self, response):
        base_url = get_base_url(response)

        brands = response.xpath('//dl[@id="narrow-by-list"]//a[contains(@href, "manufacturer")]')
        for brand in brands:
            brand_name = brand.xpath('text()').extract()[0]
            brand_url = brand.xpath('@href').extract()[0]
            yield Request(brand_url+'&p=1', callback=self.parse_products, meta={'brand': brand_name})

        yield Request(response.url, dont_filter=True, callback=self.parse_products)

    def parse_products(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        last_page = int(hxs.select('//div[@class="lastpagenumber"]/@id').extract()[0][1:])
        cur_page = int(url_query_parameter(response.url,'p'))
        if cur_page <= last_page:
            cur_page += 1
            next_page_url = add_or_replace_parameter(response.url,'p', str(cur_page))
            yield Request(next_page_url, callback=self.parse_products)

        for url in hxs.select('//div[@class="products-set"]/ul/li/h4/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        try:
            product_identifier = hxs.select('//input[@name="product"]/@value').extract()[0].strip()
        except:
            product_identifier = hxs.select('//form[@id="product_addtocart_form"]/@action').re(r'/product/(\d+)')
            if not product_identifier:
                yield Request(response.url, callback=self.parse_product, dont_filter=True)
                return
            else:
                product_identifier = product_identifier[0]
        product_name = hxs.select('//h2[@itemprop="name"]/text()').extract()[0]
        category = hxs.select('//ul[@itemprop="breadcrumb"]/li/a/text()').extract()[1:]
        sku = hxs.select('//div[@class="quickfind"]/text()').extract()
        sku = sku[0].replace('Quick find', '').strip() if sku else ''
        price = hxs.select('//*[@id="product-price-{}"]/div/span[@class="price"]/text()'.format(product_identifier)).extract()[0]
        price_pennies = hxs.select('//*[@id="product-price-{}"]/div/span[@class="price"]/span[@class="price-pennies"]/text()'.format(product_identifier)).extract()
        if price_pennies:
            price += price_pennies[0]
        price = extract_price(price)
        cashback = hxs.select('//div[@class="cashback"]/text()').extract()
        if cashback:
            price += extract_price(cashback[0])
        stock = hxs.select('//*[@id="product_addtocart_form"]//input[@name="addtocart"]')

        options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)
        if options_config:
            product_data = json.loads(options_config.groups()[0])
            products = {}
            prices = {}
            for attr_id, attr in product_data['attributes'].iteritems():
                for option in attr['options']:
                    option_price = extract_price(option['price'])
                    for product in option['products']:
                        products[product] = ' '.join((products.get(product, ''), option['label']))
                        prices[product] = option_price

            for identifier, option_name in products.iteritems():
                product_loader = ProductLoader(item=Product(), selector=hxs)
                product_loader.add_value('identifier', product_identifier + '_' + identifier)
                product_loader.add_value('name', product_name + ' ' + option_name)
                if image_url:
                    product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                product_loader.add_value('url', response.url)
                product_loader.add_value('category', category)
                product_loader.add_value('sku', sku)
                product_loader.add_value('price', price + prices[identifier])
                if price < 150:
                    product_loader.add_value('shipping_cost', 5)
                if not stock:
                    product_loader.add_value('stock', 0)
                product = product_loader.load_item()
                yield product
        else:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('identifier', product_identifier)
            product_loader.add_value('name', product_name)
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            product_loader.add_value('url', response.url)
            product_loader.add_value('category', category)
            product_loader.add_value('sku', sku)
            product_loader.add_value('price', price)
            if price < 150:
                product_loader.add_value('shipping_cost', 5)
            if not stock:
                product_loader.add_value('stock', 0)
            product = product_loader.load_item()
            yield product

# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price
import json, re, ast

from scrapy import log


class CassartSpider(BaseSpider):

    name = u'cassart.co.uk'
    allowed_domains = ['cassart.co.uk']
    json_url = 'https://www.cassart.co.uk/search?searchterm=&format=json&task=view_items&page=%d'
    start_urls = (json_url %1,)


    def parse(self, response):

        base_url = get_base_url(response)
        page = int(response.meta.get('page', 1))
        num_products = int(response.meta.get('num_products', 0))
        data = json.loads(response.body)
        hxs = HtmlXPathSelector(text=data['items'])
        urls = hxs.select('//li[@class="prod"]//h5/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        num_products += len(urls)
        page += 1
        products_total = data['numProducts']
        if num_products < products_total and len(urls):
            yield Request(
                self.json_url %page,
                meta={'num_products': num_products, 'page': page}
            )


    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        url = urljoin_rfc(base_url, response.url)
        image_url = hxs.select('//img[@id="product-image-main"]/@src').extract()
        product_name = hxs.select('//*[@id="product-header"]//h1/text()').extract()
        if product_name:
            product_name = product_name[0].strip()
        else:
            log.msg('Skips product without name: ' + response.url)
            return

        category = hxs.select('//div[@class="crumbs"]/span/a/span/text()').extract()[-1]
        brand = hxs.select('//*[@id="product-header"]/a/img/@alt').extract()
        brand = brand[0] if brand else ''
        options = hxs.select('//table[@class="child-list with-hover"][1]/tbody/tr')
        if options:
            for option in options:
                columns = option.select('./td')
                name = ''
                sku = ''
                get_name = 1
                in_stock = 1
                identifier = ''
                for column in columns:
                    ctype = column.select('./@class').extract()[0]
                    if ctype == 'code':
                        get_name = 0
                        name = product_name + name
                        sku = column.select('./text()').extract()[0]
                    if get_name:
                        name += ' - ' + column.select('./text()').extract()[0]
                    if ctype == 'price':
                        price = column.select('.//input/@value').extract()[-1]
                        price = extract_price(price)
                    if ctype == 'status out-of-stock':
                        in_stock = 0

                
                identifier = sku
                loader = ProductLoader(item=Product(), selector=option)
                loader.add_value('identifier', identifier)
                loader.add_value('url', url)
                colour = hxs.select('//li[.//td[text()="'+sku+'"]]/div[contains(@class, "colour")]/p/text()').extract()
                if colour:
                    name = name + ' ' + colour[0]
                loader.add_value('name', name)
                if image_url:
                    loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                loader.add_value('price', price)
                loader.add_value('sku', sku)
                loader.add_value('brand', brand)
                loader.add_value('category', category)
                if not in_stock:
                    loader.add_value('stock', 0)
                if price <= 49.99:
                    loader.add_value('shipping_cost', 3.95)
                else:
                    loader.add_value('shipping_cost', 0)
                yield loader.load_item()

        else:
            options = hxs.select('//div[@class="product-options"]//option[not(@title="Not Selected")]')

            if options:

                try:
                    options_mappings = json.loads(re.findall(re.compile("childMap\': (\{.+?}),\n"), response.body)[0])
                    options_prices = json.loads(re.findall(re.compile("prices\': (\{.+?}),\n"), response.body)[0])
                    options_skus = json.loads(re.findall(re.compile("skus\': (\{.+?}),\n"), response.body)[0])
                    options_stocks = json.loads(re.findall(re.compile("stockStatuses\': (\{.+?}),\n"), response.body)[0])
                except:
                    return

                for option in options:

                    loader = ProductLoader(item=Product(), selector=hxs)

                    option_name = product_name + ' ' + option.select("./@title").extract()[0]
                    option_id = option.select("./@value").extract()[0]
                    option_mapping = str(options_mappings[option_id])

                    option_price = extract_price(str(options_prices[option_mapping][0]['purchase']))
                    option_sku = options_skus[option_mapping]
                    option_stock = 1 if not 'Out' in options_stocks[option_mapping] else 0

                    loader.add_value('identifier', option_sku)
                    loader.add_value('sku', option_sku)
                    loader.add_value('url', url)
                    loader.add_value('name', option_name)
                    loader.add_value('price', option_price)
                    loader.add_value('brand', brand)
                    loader.add_value('category', category)
                    loader.add_value('stock', option_stock)

                    if image_url:
                        loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                    if option_price < 49.99:
                        loader.add_value('shipping_cost', 3.95)
                    else:
                        loader.add_value('shipping_cost', 0)

                    yield loader.load_item()


            else:
                loader = ProductLoader(item=Product(), selector=hxs)
                sku = hxs.select('//div[@class="title"]//p/text()').extract()[0]
                sku = sku.replace('Product Code: P', '')
                identifier = sku
                loader.add_value('identifier', identifier)
                loader.add_value('sku', sku)
                loader.add_value('url', url)
                loader.add_value('name', product_name)
                if image_url:
                    loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                price = hxs.select('//*[@id="product-price"]//input/@value').extract()[0]
                price = extract_price(price)
                loader.add_value('price', price)
                loader.add_value('brand', brand)
                loader.add_value('category', category)
                in_stock = hxs.select('//*[@id="product-stock"]/text()').extract()[0]
                if in_stock != 'In stock':
                    loader.add_value('stock', 0)
                if price < 49.99:
                    loader.add_value('shipping_cost', 3.95)
                else:
                    loader.add_value('shipping_cost', 0)
                yield loader.load_item()

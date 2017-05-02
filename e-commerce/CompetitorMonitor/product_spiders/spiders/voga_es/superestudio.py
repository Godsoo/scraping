# -*- coding: utf-8 -*-

import re
import sys
from decimal import Decimal


from scrapy.contrib.spiders import SitemapSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, XmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.contrib.loader.processor import TakeFirst, Compose
from scrapy.exceptions import CloseSpider

from product_spiders.items import Product, ProductLoader


def spanishDecimal(a):
    return re.sub(r'[^0-9,]+', '', a).replace(',', '.')


def stripSessionId(url):
    return re.sub('osCsid=\w+', '', url).rstrip('?')


class SupereStudio(SitemapSpider):
    name = 'voga_es-superestudio.com'
    allowed_domains = ['www.superestudio.com']
    sitemap_urls = ('http://www.superestudio.com/sitemap',)
    # download_delay = 1

    '''
    def parse(self, response):
        if not isinstance(response, XmlResponse):
            self.log("%s is not XmlResponse" % response)
            return

        hxs = HtmlXPathSelector(response)

        # categories
        products = hxs.select('//url/loc/text()').extract()
        for url in products:
            yield Request(url, callback=self.parse_page)
    '''

    def parse(self, response):
        for item in self.parse_category(response):
            yield item

        for item in self.parse_product(response):
            yield item

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)

        # products
        products = hxs.select(u'//div[@class="productdetls"]/h4/a/@href').extract()
        for url in products:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product)


        # pages
        next_page = hxs.select(u'//div[@class="paginador_box"]/ul/li/a[contains(text(), "siguiente")]/@href').extract()
        if next_page:
            url = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(url, callback=self.parse_category)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            self.log("%s is not HtmlResponse" % response)
            return

        try:
            hxs = HtmlXPathSelector(response)

            option_specs = []

            product_options = hxs.select(u'//a[@href="#" and contains(@class, "select")]/@title').extract()
            if product_options:
                # Extract product options and price
                for option_text in product_options:
                    parts = re.split(r'[()]', option_text, 2)
                    option_name = parts[0]
                    part_len = len(parts)
                    if part_len == 1:
                        price_diff = 0
                    else:
                        price_spec = parts[1]
                        modifier = -1 if price_spec.startswith('-') else 1
                        price_diff = price_spec.replace('+', '').replace('-', '')
                        price_diff = Decimal(spanishDecimal(price_diff)) * modifier

                    option_specs.append({'extra_name': option_name,
                                         'price_diff': price_diff})

            else:
                option_specs.append({'extra_name': '', 'price_diff': 0})

            for option_spec in option_specs:
                extra_name = option_spec['extra_name']
                price_diff = option_spec['price_diff']
                category = hxs.select(u'//div[@class="breadcump"]/a[not(@class="first")]/text()').extract()
                category = category if category else None
                image_url = hxs.select(u'//div[@id="fotografias"]/div[@class="grande"]/a[contains(@class, "fotopopup")]/img/@src').extract()
                if image_url:
                    image_url = urljoin_rfc(get_base_url(response), image_url[0])

                name = hxs.select(u'//div[@class="colRight"]/h1/strong/text()').extract()
                if not name:
                    return

                product_loader = ProductLoader(item=Product(), response=response)
                if extra_name:
                    product_loader.add_value('name', "%s - %s" %
                                             (name[0].strip(), extra_name.strip()))
                else:
                    product_loader.add_value('name', name[0].strip())
                product_loader.add_value('url', response.url,
                                         Compose(stripSessionId))
                product_loader.add_value('category', category)
                if image_url:
                    product_loader.add_value('image_url', image_url,
                                             Compose(stripSessionId))

                if extra_name:
                    identifier = product_loader.get_xpath('//input[@id="id_producto"]/@value',
                                                          TakeFirst())
                    id_n_ext_name = "%s-%s" % (identifier, extra_name)
                    product_loader.add_value('identifier', id_n_ext_name)

                else:
                    product_loader.add_xpath('identifier',
                                             '//input[@id="id_producto"]/@value',
                                             TakeFirst())

                product_loader.add_xpath('sku',
                                         '//div[@class="colRight"]/div/span[@class="id_ref"]/text()',
                                         TakeFirst())

                price_xpath_root = '//div[@id="detalle-info"]/div/div/div[@class="price"]'
                price_xpath_normal = '%s/span[@class="normalprice" or @class="tachaprice"]/text()' % price_xpath_root
                price_xpath_discount = '%s/span[@class="moreprice"]/text()' % price_xpath_root
                price_xpath = "%s|%s" % (price_xpath_normal, price_xpath_discount)
                extraced_prices = hxs.select(price_xpath).extract()
                self.log("Extraced Prices: %s" % extraced_prices)
                price = filter(unicode.strip, extraced_prices)[-1]
                price = Decimal(spanishDecimal(price))

                if price_diff:
                    price = price + price_diff
                product_loader.add_value('price', price)

                product_loader.add_value('stock', 1 if price else 0)
                yield product_loader.load_item()

                # parse product options
                more_products = hxs.select(u'//div[@class="product_section_sub"][1]/a[@title]/@href').extract()
                _, _, urlpath = response.url.partition('/product-pol')
                url_to_remove = "/product-pol%s" % urlpath
                final_more_products = list(set(more_products)
                                           - set([url_to_remove]))

                # parse product
                for product_url in final_more_products:
                    product_url = urljoin_rfc(get_base_url(response), product_url)
                    yield Request(product_url, callback=self.parse_product)
        except Exception as exc:
            raise CloseSpider("%s on %s" % (exc, response.url)), None, sys.exc_info()[2]

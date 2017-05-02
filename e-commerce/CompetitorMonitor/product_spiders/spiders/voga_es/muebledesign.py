# -*- coding: utf-8 -*-

import re
from decimal import Decimal


from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.contrib.loader.processor import TakeFirst, Compose

from product_spiders.items import Product, ProductLoader


def spanishDecimal(a):
    return re.sub(r'[^0-9,]+', '', a).replace(',', '.')


def stripSessionId(url):
    return re.sub('osCsid=\w+', '', url).rstrip('?')


class MuebleDesign(BaseSpider):
    name = 'voga_es-muebledesign.com'
    allowed_domains = ['www.muebledesign.com']
    start_urls = ('http://www.muebledesign.com/sitemap.html',)
    # download_delay = 1

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            self.log("%s is not HtmlResponse" % response)
            return

        hxs = HtmlXPathSelector(response)

        # categories
        categories = hxs.select('//td[./a[@class="muebles-de-diseno-grey"]][2]/a/@href').extract()
        for url in categories:
            yield Request(url, callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)

        # products
        products = hxs.select(u'//table[@class="tableBox_output"]//a[@href and @class="pdte"]/@href').extract()
        for url in products:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product)

        if not products:
            meta = response.meta.copy()
            meta['retry'] = meta.get('retry', 0)
            if meta['retry'] < 3:
                meta['retry'] += 1
                self.log('>>> RETRY %d => %s'
                         % (meta['retry'], response.request.url))
                yield Request(response.request.url, meta=meta)

        # pages
        next_page = hxs.select(u'//table[@class="result"]//a[contains(@title, "Siguiente")]/@href').extract()
        if next_page:
            url = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(url, callback=self.parse_category)

    def parse_product(self, response):

        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)

        brand = hxs.select("//*[contains(text(),'Dise') and contains(text(),'ador:')]/text()").extract()
        brand = brand[0].split(':')[1].strip() if brand else ''

        option_specs = []

        product_options = hxs.select(u'//select[@class="form" and contains(@onchange, "actualiza_atributos")]/option/text()').extract()
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
            category = hxs.select(u'//td[@class="cont_heading_td"]/span[@class="sub_cont_heading_td"]/text()').extract()
            category = category[0] if category else ''
            image_url = hxs.select(u'(//a[@rel="fotografias"])[1]/@href').extract()
            if image_url:
                image_url = urljoin_rfc(get_base_url(response), image_url[0])

            name = hxs.select(u'//td[@class="cont_heading_td"]/h1[last()]/text()').extract()[0]

            product_loader = ProductLoader(item=Product(), response=response)
            if extra_name:
                product_loader.add_value('name', "%s - %s" %
                                         (name.strip(), extra_name.strip()))
            else:
                product_loader.add_value('name', name.strip())

            product_loader.add_value('url', response.url,
                                     Compose(stripSessionId))
            product_loader.add_value('category', category)
            product_loader.add_value('brand', brand)
            product_loader.add_value('image_url', image_url,
                                     Compose(stripSessionId))

            if extra_name:
                identifier = product_loader.get_value(response.url,
                                                      TakeFirst(),
                                                      re='p-([0-9]+)\.html')
                id_n_ext_name = "%s-%s" % (identifier, extra_name)
                product_loader.add_value('identifier', id_n_ext_name)

            else:
                product_loader.add_value('identifier',
                                         response.url,
                                         TakeFirst(),
                                         re='p-([0-9]+)\.html')

            product_loader.add_xpath('sku',
                                     '//td[contains(text(), "Ref:")]/text()',
                                     TakeFirst(),
                                     re='Ref: (.+)')

            price = hxs.select('//td[@class="preu"]/text()[1]').extract()[0]
            price = Decimal(spanishDecimal(price))
            if price_diff:
                price = price + price_diff
            product_loader.add_value('price', price)

            product_loader.add_value('stock', 1)
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

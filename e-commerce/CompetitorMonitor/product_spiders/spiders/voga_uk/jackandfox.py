# -*- coding: utf-8 -*-

import re
import os
import ast
import itertools
import operator
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.contrib.loader.processor import TakeFirst

from product_spiders.items import Product, ProductLoader


from product_spiders.base_spiders.primary_spider import PrimarySpider


class CodeBlockString:
    """CodeBlockString finds blocks of code in a codes. If you have code string

        if(len(x)>len(y)){
            return new GreaterResultType(new GreaterParameter(x), new LesserParameter(y));
        }

    You can extract following strings from it

    1. `new GreaterParameter(x), new LesserParameter(y)`
    2. `return new GreaterResultType(new GreaterParameter(x), new LesserParameter(y));`
    3. `len(x)>len(y)`

    This is specially helpfull when you parse scripts in website (javascript) or custom
    file format that uses specific starting and ending characters.

    This will not work if the starting and ending tokens are longer than one character.

    Usage:
        # Instanciate
        cbs = CodeBlockString("if(len(x)>len(y)){ ...")
        cbs.set_start(['('])
        cbs.set_end([')'])
        block = cbs.findfrom(2)
        # block contains 'len(x)>len(y)' now

    """

    input = ''
    start = ['[', '{', '(']
    end = [']', '}', ')']
    length = 1

    def __init__(self, value):
        self.set(value)

    def set_start(self, start):
        self.start = start

    def set_end(self, end):
        self.end = end

    def set(self, value):
        self.input = list(value)
        self.length = len(value)

    def findfrom(self, index, level=1):
        """Finds string from an index

        Args:
            index: character index where the search should be started from
            level: nested level of next character in the string. Default 1

        Returns:
            The extracted code block string.

        """

        output = ''
        for i in range(index + 1, self.length):
            if self.input[i] in self.start:
                level += 1
                output += self.input[i]
            elif self.input[i] in self.end:
                level -= 1
                if level < 1:
                    break
                output += self.input[i]
            else:
                output += self.input[i]

        return output


def category_from_url(url):
    basename = os.path.basename(url)
    return re.sub(r'\.html.*', '', basename)


def product_option_dict(script_fragment):
    cbs = CodeBlockString(script_fragment)
    ptr_str = 'Product.Config'
    idx = script_fragment.index(ptr_str) + len(ptr_str)
    codeblock = cbs.findfrom(idx)
    codeblock = re.sub(r'true|false',
                       lambda a: a.group(0).title(),
                       codeblock)
    return ast.literal_eval(codeblock)


def name_fragment_and_price_diffs(option_dict):
    normalized_attribs = [v['options'] for v in
                          option_dict['attributes'].values()]
    combinations = itertools.product(*normalized_attribs)

    # Filter invalid combinations
    combinations = filter(lambda a: reduce(operator.and_,
                                           [set(p['products']) for p in a]),
                          combinations)
    options = []

    for combination in combinations:
        name_fragment = ' '.join(map(lambda a: a['label'], combination))
        price_diff = sum(map(lambda a: a['price'], combination))
        image_option = filter(lambda a: 'image' in a, combination)
        if image_option:
            image_url = image_option[0]['image']
        else:
            image_url = None
        options.append({'extra_name': name_fragment,
                        'price_diff': price_diff})

    return options


class JackAndFox(PrimarySpider):
    name = 'voga_uk-jackandfox.com'
    allowed_domains = ['www.jackandfox.com']
    start_urls = ('http://www.jackandfox.com/catalog/seo_sitemap/category/',)
    # download_delay = 1

    csv_file = 'jackandfox_products_primary.csv'

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            self.log("%s is not HtmlResponse" % response)
            return

        hxs = HtmlXPathSelector(response)

        # categories
        categories = hxs.select('//ul[@class="sitemap"]/li/a/@href').extract()
        for url in categories:
            yield Request("%s?limit=all" % url, callback=self.parse_category)

        # Next page
        next_page = hxs.select(u'//div[@class="pages"]/ol/li/a[@title="Next"]/@href')
        if next_page:
            next_page_url = next_page.extract()[0]
            yield Request(next_page_url, callback=self.parse)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)

        # products
        products = hxs.select(u'//div[@class="item-title"]/a/@href').extract()
        for url in products:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product,
                          meta={"category": category_from_url(response.url)})

        if not products:
            meta = response.meta.copy()
            meta['retry'] = meta.get('retry', 0)
            if meta['retry'] < 3:
                meta['retry'] += 1
                self.log('>>> RETRY %d => %s'
                         % (meta['retry'], response.request.url))
                yield Request(response.request.url, meta=meta)

        # pages
        next_page = hxs.select(u'//div[@class="pages"]/ol/li/a[@title="Next"]/@href').extract()
        if next_page:
            url = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(url, callback=self.parse_category)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)

        option_specs = []
        category = response.meta['category']
        product_options = hxs.select(u'//dl/following-sibling::script[1]/text()').extract()
        if product_options:
            # Extract product options and price
            pod = product_option_dict(product_options[0])
            option_specs = name_fragment_and_price_diffs(pod)
        else:
            option_specs.append({'extra_name': '', 'price_diff': 0})

        for option_spec in option_specs:
            extra_name = option_spec['extra_name']
            price_diff = option_spec['price_diff']

            name = hxs.select(u'//h1[@itemprop="name"]/text()').extract()[0]

            product_loader = ProductLoader(item=Product(), response=response)
            if extra_name:
                product_loader.add_value('name', "%s - %s" %
                                         (name.strip(), extra_name.strip()))
            else:
                product_loader.add_value('name', name.strip())

            product_loader.add_value('url', response.url)
            product_loader.add_value('category', category)
            product_loader.add_xpath('image_url',
                                     u'//img[@id="amasty_zoom"]/@src',
                                     TakeFirst())

            identifier_xpath = '//form[@id="product_addtocart_form"]/div/input[@name="product"]/@value'
            if extra_name:
                identifier = product_loader.get_xpath(identifier_xpath,
                                                      TakeFirst())
                id_n_ext_name = "%s-%s" % (identifier, extra_name)
                product_loader.add_value('identifier', id_n_ext_name)

            else:
                product_loader.add_xpath('identifier',
                                         identifier_xpath,
                                         TakeFirst())

            product_loader.add_xpath('sku',
                                     '//div[@class="section-content"]/ul[li/text()="SKU"]/li[last()]/text()',
                                     TakeFirst())

            price = product_loader.get_xpath(u'//div[@itemid="#product_base"]/script[1]/text()',
                                             TakeFirst(),
                                             re=r'"productPrice":([.0-9]+)')
            price = Decimal(price)
            if price_diff:
                price = price + Decimal("%.2f" % price_diff)
            product_loader.add_value('price', price)

            product_loader.add_value('stock', 1)
            yield product_loader.load_item()

__author__ = 'bayuadji'

import logging
import re
from datetime import datetime

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

import json


class TescoComSpider(BaseSpider):
    name = 'legouk-tesco.com'
    allowed_domains = ['tesco.com']
    start_urls = (
        'http://www.tesco.com/direct/',
    )

    def start_requests(self):
        params = {
            'catId': '4294967294',
            'lazyload': 'true',
            'offset': '0',
            'searchquery': 'Lego',
            'sortBy': '6',
            'view': 'grid',
        }
        get_params = "&".join(map(lambda x: "=".join(x), params.items()))
        ajax_url = 'http://www.tesco.com/direct/blocks/catalog/productlisting/infiniteBrowse.jsp?' + get_params

        yield FormRequest(ajax_url, formdata=params, meta={'offset': 0}, callback=self.parse_search)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        url = response.url
        brand = 'Lego'
        l = ProductLoader(item=Product(), response=response)

        name = hxs.select('//h1[@class="page-title"]/text()').extract()
        if not name:
            logging.error("ERROR! NO NAME! %s" % url)
            return
        name = name[0].strip()
        l.add_value('name', name)

        price = hxs.select('//*[@itemprop="price"]/text()').extract()
        if not price:
            logging.error("ERROR! NO PRICE! %s %s" % (url, name))
            price = ''
        l.add_value('price', price)
        identifier = url.lower().split('skuid=')[-1] if len(url.lower().split('skuid=')) > 0 else None
        if not identifier:
            logging.error("ERROR! IDENTIFIER! %s %s" % (url, name))
            return

        l.add_value('identifier', identifier)
        l.add_value('url', url)

        category = [x.strip() for x in hxs.select('//div[@id="breadcrumb"]//li[not (@class="last")]//a/span/text()').extract()]
        category = u' > '.join(category)
        l.add_value('category', category)
        l.add_value('brand', brand.strip())

        sku = re.search('([\d]{3,})$', l.get_output_value('name'))
        if sku:
            l.add_value('sku', sku.group(1))

        image_url = hxs.select('//div[contains(@class, "static-product-image")]/img/@src').extract()
        if image_url:
            l.add_value('image_url', image_url[0])

        yield l.load_item()

    def parse_search(self, response):
        data = json.loads(response.body)

        if not data['products']:
            return

        hxs = HtmlXPathSelector(text=data['products'])
        base_url = get_base_url(response)

        # parse products
        items = hxs.select("//div[contains(@class, 'product')]")
        for item in items:
            name = item.select(".//div[contains(@class, 'title-author-format')]/h3//a/text()").extract()
            if not name:
                continue

            url = item.select(".//div[contains(@class, 'title-author-format')]/h3/a/@href").extract()
            if not url:
                logging.error("ERROR! NO URL! URL: %s. NAME: %s" % (response.url, name))
                continue
            url = url[0]
            url = urljoin_rfc(base_url, url)

            yield Request(url, callback=self.parse_product)

        offset = response.meta['offset'] + 20

        params = {
            'catId': '4294967294',
            'lazyload': 'true',
            'offset': str(offset),
            'searchquery': 'Lego',
            'sortBy': '6',
            'view': 'grid',
        }
        get_params = "&".join(map(lambda x: "=".join(x), params.items()))
        ajax_url = 'http://www.tesco.com/direct/blocks/catalog/productlisting/infiniteBrowse.jsp?' + get_params

        yield FormRequest(ajax_url, formdata=params, meta={'offset': offset}, callback=self.parse_search, dont_filter=True)

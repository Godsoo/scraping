__author__ = 'bayuadji'

import logging
import re
import urlparse
from datetime import datetime

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from johnlewisitems import JohnLewisMeta

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

import json


class TescoComSpider(BaseSpider):
    name = 'johnlewis-trial-tesco.com'
    allowed_domains = ['tesco.com']
    start_urls = [
        'http://www.tesco.com/direct/home-garden/gadgets-utensils-food-preparation/cat3375673.cat?catId=4294961487', 
        'http://www.tesco.com/direct/technology-gaming/cameras-camcorders/cat3376584.cat?icid=technologygaming_flyoutlink_slot32',
        'http://www.tesco.com/direct/home-electrical/built-in-appliances/cat3376592.cat?icid=homeelectrical_flyoutlink_slot1', 
        'http://www.tesco.com/direct/home-electrical/hobs/cat3376598.cat?catId=4294875598',
        'http://www.tesco.com/direct/home-electrical/dishwashers/cat3376676.cat?icid=homeelectrical_flyoutlink_slot3',
        'http://www.tesco.com/direct/home-electrical/fridges-freezers/cat3376659.cat?icid=homeelectrical_flyoutlink_slot4',
        'http://www.tesco.com/direct/technology-gaming/televisions/cat3376652.cat?icid=technologygaming_flyoutlink_slot20',
        'http://www.tesco.com/direct/technology-gaming/television-accessories/cat3375660.cat?catId=4294959846&icid=technologygaming_flyoutlink_slot21',
        'http://www.tesco.com/direct/technology-gaming/desktops/cat3375862.cat?catId=4294960209&icid=technologygaming_flyoutlink_slot2',
        'http://www.tesco.com/direct/technology-gaming/all-laptops/cat3376345.cat?catId=4294960185&icid=technologygaming_flyoutlink_slot3',
        'http://www.tesco.com/direct/technology-gaming/netbooks/cat3376230.cat?catId=4294960187&icid=technologygaming_flyoutlink_slot7'
        'http://www.tesco.com/direct/toys/arts-music-creative-play/cat3376603.cat?icid=toys_flyoutlink_slot3',
        'http://www.tesco.com/direct/toys/education-science/cat3376577.cat?catId=4294959614&icid=toys_flyoutlink_slot5',
        'http://www.tesco.com/direct/toys/electronic-toys/cat3376541.cat?icid=toys_flyoutlink_slot6',
        'http://www.tesco.com/direct/toys/games-puzzles/cat3376550.cat?icid=toys_flyoutlink_slot16'
        ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        ajax_url = 'http://www.tesco.com/direct/blocks/catalog/productlisting/infiniteBrowse.jsp'

        categories = hxs.select('//div[@class="menu"]/ul/li/a/@href').extract()
        categories += hxs.select('//li[@id="category-filter"]/div/ul/li/a/@href').extract()
        for category in categories:
            parsed = urlparse.urlparse(category)
            params = urlparse.parse_qs(parsed.query)
            cat_id = params['catId'][0]
            params = {
                'catId': cat_id,
                'lazyload': 'true',
                'offset': '0',
                'searchquery': 'undefined',
                'sortBy': '6',
                'view': 'grid',
            }

            yield FormRequest(ajax_url, formdata=params, meta={'offset': 0, 'cat_id': cat_id}, callback=self.parse_search)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        url = response.url
        brand = ''
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

        image_url = hxs.select('//div[@class="product"]/a[@class="thumbnail"]/img/@src').extract()
        if not image_url:
            image_url = hxs.select('//div[@class="product"]//div[@class="static-product-image"]/img/@src').extract()
        if image_url:
            l.add_value('image_url', image_url[0])

        out_of_stock = 'CURRENTLY UNAVAILABLE' in ''.join(hxs.select('//span[@itemprop="availability"]/text()').extract()).upper()
        if out_of_stock:
            l.add_value('stock', 0)

        item = l.load_item()

        price_was = hxs.select('//p[@class="old-price"]/del/text()').extract()
        price_was = price_was[0].strip().replace(u'\xa0', ' ') if price_was else ''

        metadata = JohnLewisMeta()
        metadata['promotion'] = price_was
        item['metadata'] = metadata

        yield item


    def parse_search(self, response):
        data = json.loads(response.body)

        if not data['products']:
            return

        hxs = HtmlXPathSelector(text=data['products'])
        base_url = get_base_url(response)

        # parse products
        items = hxs.select("//div[contains(@class, 'product')]")
        for item in items:
            name = item.select("div[contains(@class, 'title-author-format')]/h3/a/text()").extract()
            if not name:
                continue

            url = item.select("div[contains(@class, 'title-author-format')]/h3/a/@href").extract()
            if not url:
                logging.error("ERROR! NO URL! URL: %s. NAME: %s" % (response.url, name))
                continue
            url = url[0]
            url = urljoin_rfc(base_url, url)

            yield Request(url, callback=self.parse_product)

        offset = response.meta['offset'] + 20
        cat_id = response.meta['cat_id']

        ajax_url = 'http://www.tesco.com/direct/blocks/catalog/productlisting/infiniteBrowse.jsp'
        params = {
            'catId': cat_id,
            'lazyload': 'true',
            'offset': str(offset),
            'searchquery': 'undefined',
            'sortBy': '6',
            'view': 'grid',
        }

        yield FormRequest(ajax_url, formdata=params, meta={'offset': offset, 'cat_id': cat_id}, callback=self.parse_search, dont_filter=True)

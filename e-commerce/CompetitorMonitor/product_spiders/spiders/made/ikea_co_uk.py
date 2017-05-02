# -*- coding: utf-8 -*-

import os
import re
import json
from decimal import Decimal
from copy import deepcopy

from urlparse import urljoin

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))
FILE_WITH_ITEMS = "ikea_mpns_toextract.csv"


class IkeaCoUK(BaseSpider):
    name = "made-ikea.co.uk"
    allowed_domains = ["ikea.co.uk", "ikea.com"]
    start_urls = ["http://www.ikea.com/gb/en/"]

    rotate_agent = True

    def parse(self, response):
        base_url = get_base_url(response)

        categories = response.xpath('//a[contains(@href, "categories/")]/@href').extract()
        for category in categories:
            yield Request(urljoin(base_url, category))

        products = response.xpath('//a[contains(@href, "/products/")]/@href').extract()
        for product in products:
            yield Request(urljoin(base_url, product), callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)

        try:
            name = response.xpath('//div[@id="name"]/text()').extract()[0].strip()
        except:
            name = ''

        try:
            desc = response.xpath('//div[@id="type"]/text()').extract()[0].strip()
        except:
            desc = ''

        if desc:
            name = name + ' ' + desc

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', name)
        loader.add_value('shipping_cost', 7.50)
        loader.add_value('url', response.url)

        price = response.xpath('//span[@id="price1"]/text()').extract()
        if price:
            price = extract_price(price[0])
            loader.add_value('price', price)

        image_url = response.xpath('//img[@id="productImg"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin(base_url, image_url[0]))

        category = map(unicode.strip, response.xpath('//ul[@id="breadCrumbs"]//li/a/text()').extract())[1:]
        category = self._get_unified_category(category, name, price)
        if category and ('Side tables' in category[-1]):
            category = ['Tables', 'Side Tables']
        loader.add_value('category', category)

        stock = response.xpath('//*[@id="dispNotShopableOnlineText"]/@style').extract()
        if not stock or 'display:none' in stock[0]:
            stock = 1
        else:
            stock = 0
        loader.add_value('stock', stock)

        loader.add_xpath('sku', '//div[@id="itemNumber"]/text()')
        loader.add_xpath('identifier', '//div[@id="itemNumber"]/text()')

        item = loader.load_item()

        options_data = re.search(r'var jProductData = (.*);', response.body)
        if options_data:
            product_data = json.loads(options_data.groups()[0])

            for option in product_data['product']['items']:
                option_item = deepcopy(item)
                option_item['name'] = option['name']
                description = []
                description.append(option['type'])
                description.extend(option['validDesign'])
                description = ' '.join(description).strip()
                if description:
                    option_item['name'] += ' ' + description

                option_text = response.xpath('//option[@value="'+option['catEntryId']+'"]/text()').extract()
                option_text = option_text[0].strip() if option_text else ''
                if option_text and option_text.upper() not in option_item['name'].upper():
                    option_item['name'] += ' ' + option_text

                url = option['url']
                option_item['url'] = urljoin(base_url, url)

                option_item['price'] = Decimal(option['prices']['normal']['priceNormal']['rawPrice'])
                identifier = option['partNumber'].replace('S', '')
                identifier = '.'.join(identifier[i:i+3] for i in range(0, len(identifier), 3))
                option_item['identifier'] = identifier
                option_item['sku'] = identifier
                if option_item['identifier']:
                    yield option_item

        else:
            if item['identifier']:
                yield item

    def _get_unified_category(self, categories, name, price):
        categories_lower = map(unicode.lower, categories)
        name_lower = name.lower().replace(',', '').replace('/', ' ').replace('-', ' ')
        set_miscellaneous = False

        if (('extendable' in name_lower) or ('extending' in name_lower)) and ('table' in name_lower.split()):
            return ['Tables', 'Extending Tables']
        if ('dining table' in name_lower) or ('dining tables' in categories_lower):
            if ('top' in name_lower.split()) or ('frame' in name_lower.split()) or ('underframe' in name_lower.split()) or \
               ('base' in name_lower.split()) or ('picnic' in name_lower.split()):
                set_miscellaneous = True
            elif 'outdoor' in name_lower.split():
                return ['Outdoor', 'Outdoor Dining']
            else:
                return ['Tables', 'Dining Tables']
        if ('coffee & side tables' in categories_lower) and ('coffee' in name_lower):
            return ['Tables', 'Coffee Tables']
        if ('coffee & side tables' in categories_lower) and ('side' in name_lower):
            if ('nest' in name_lower.split()) or ('window' in name_lower.split()) or \
               ('tray' in name_lower.split()) or ('storage' in name_lower.split()):
                set_miscellaneous = True
            else:
                return ['Tables', 'Side Tables']
        if 'desks & computer desks' in categories_lower:
            if ('desk' in name_lower.split()) and ('table' not in name_lower.split()):
                return ['Tables', 'Desks']
            set_miscellaneous = True
        if ('tv bench' in name_lower) or ('tv storage' in name_lower):
            return ['Storage', 'Media Units']
        if 'tv benches' in categories_lower:
            set_miscellaneous = True
        if 'dressing tables' in categories_lower:
            if 'stool' not in name_lower.split():
                return ['Tables', 'Dressing Tables']
            set_miscellaneous = True
        if 'bookcases' in categories_lower:
            if ('panel' in name_lower.split()) or ('door' in name_lower.split()) or \
               ('extension' in name_lower.split()) or ('fitting' in name_lower):
                set_miscellaneous = True
            else:
                return ['Storage', 'Bookcases & Shelves']
        if 'wardrobes' in categories_lower:
            if ('wardrobe' in name_lower.split()) and ('frame' not in name_lower):
                return ['Storage', 'Wardrobes']
            set_miscellaneous = True
        if ('sideboards' in categories_lower) and ('sideboard' in name_lower):
            return ['Storage', 'Sideboards']
        if ('chests of drawers' in categories_lower) or \
           (('chest of' in name_lower) and ('drawers' in name_lower.split())):
            if (price > Decimal('19.99')) and ('bench' not in name_lower)\
               and ('top' not in name_lower) and ('plinth' not in name_lower):
                return ['Storage', 'Chests of Drawers']
            set_miscellaneous = True
        if 'floor lamps' in categories_lower:
            return ['Lighting', 'Floor Lamps']
        if 'wall lights' in categories_lower:
            return ['Lighting', 'Wall Lights']
        if 'table lamps' in categories_lower:
            return ['Lighting', 'Table Lamps']
        if ('wooden-base spring mattresses' in categories_lower) or \
           ('foam & latex mattresses' in categories_lower) or \
           ('spring mattresses' in categories_lower) or \
           ('slatted bed bases' in categories_lower) or \
           ('mattress bases' in categories_lower) or \
           ('mattress pads' in categories_lower) or \
           ('bed legs' in categories_lower) or \
           ('mattress & pillow protectors' in categories_lower):
            return ['Bedroom', 'Mattresses']
        if 'cushions & cushion covers' in categories_lower:
            if 'cover' in name_lower.split():
                set_miscellaneous = True
            else:
                return ['Accessories', 'Cushions']
        if 'clocks' in categories_lower:
            if ('alarm' in name_lower) or ('floor' in name_lower):
                set_miscellaneous = True
            else:
                return ['Accessories', 'Clocks']
        if 'living room rugs' in categories_lower:
            return ['Accessories', 'Rugs']
        if 'mirrors' in categories_lower:
            return ['Accessories', 'Mirrors']
        if 'towels' in categories_lower:
            return ['Bed & Bath', 'Bath Towels']
        if 'sheets' in categories_lower:
            return ['Bed & Bath', 'Bed Sheets']
        if 'bath mats' in categories_lower:
            return ['Bed & Bath', 'Bath Mats']
        if 'blankets & throws' in categories_lower:
            return ['Accessories', 'Throws & Blankets']
        if ('children\'s chairs, tables & play tents' in categories_lower) and ('desk' in name_lower.split()):
            if ('table' in name_lower) or ('tent' in name_lower) or ('chair' in name_lower):
                set_miscellaneous = True
            else:
                return ['Kids', 'Desks']
        if ('children\'s ikea' in categories_lower) and ('bunk bed' in name_lower):
            return ['Kids', 'Bunk Beds']
        if ('children\'s beds 8-12' in categories_lower) or ('children\'s beds' in categories_lower):
            if 'desk' in name_lower:
                return ['Kids', 'Desks']
            elif ('rail' in name_lower) or ('wood' in name_lower):
                set_miscellaneous = True
            else:
                return ['Kids', 'Beds']
        if ('baby textiles' in categories_lower) or \
           ('children\'s textiles' in categories_lower) or \
           ('children\'s textiles 8-12' in categories_lower):
            return ['Kids', 'Bedding']
        if ('children\'s ikea' in categories_lower) and ('storage furniture' in categories_lower):
            if ('lid' in name_lower.split()) or ('frame' in name_lower.split()) or ('box' in name_lower.split()) or \
               ('wall' in name_lower.split()) or ('shelf' in name_lower.split()):
                set_miscellaneous = True
            else:
                return ['Kids', 'Storage']
        if 'single beds' in categories_lower:
            if 'storage' in name_lower.split():
                return ['Bedroom', 'Storage Beds']
        if 'double beds' in categories_lower:
            if 'storage' in name_lower.split():
                return ['Bedroom', 'Storage Beds']
            return ['Bedroom', 'Double Beds']
        if 'beds with storage' in categories_lower:
            return ['Bedroom', 'Storage Beds']
        if ('outdoor tables & chairs' in categories_lower) and ('table' in name_lower):
            return ['Tables', 'Outdoor Tables']
        if ('photo frames & art' in categories_lower) and ('picture' in name_lower):
            if ('frame' in name_lower.split()) or ('ledge' in name_lower.split()):
                set_miscellaneous = True
            else:
                return ['Accessories', 'Art']
        if 'bin' in name_lower.split():
            if ('bread' in name_lower.split()) or ('lid' in name_lower.split()):
                set_miscellaneous = True
            else:
                return ['Accessories', 'Bins']
        if ('racks & stands' in categories_lower) and ('stand' in name_lower.split()):
            return ['Accessories', 'Coat Stands & Hooks']
        if ('hooks & hangers' in categories_lower) and ('hook' in name_lower.split()):
            return ['Accessories', 'Coat Stands & Hooks']
        if ('bedside tables' in categories_lower) or ('bedside table' in name_lower):
            if 'chest' in name_lower:
                return ['Storage', 'Chests of Drawers']
            return ['Tables', 'Bedside Tables']
        if 'kingsize bed' in name_lower:
            if 'storage' in name_lower:
                return ['Bedroom', 'Storage Beds']
            return ['Bedroom', 'Kingsize Beds']
        if ('sofa-beds' in categories_lower) or ('sofa bed' in name_lower):
            return ['Bedroom', 'Sofa Beds']
        if ('armchair' in name_lower) or ('wing chair' in name_lower):
            return ['Chairs', 'Armchairs']
        if ('dining room' in categories_lower) and ('bench' in name_lower.split()):
            return ['Chairs', 'Benches']
        if 'dining chairs' in categories_lower:
            if 'bench' in name_lower.split():
                return ['Chairs', 'Benches']
            if 'stool' in name_lower.split():
                return ['Chairs', 'Stools and Bar Stools']
            if 'cover' not in name_lower.split():
                return ['Chairs', 'Dining Chairs']
            set_miscellaneous = True
        if ('office chairs' in categories_lower) and ('chair' in name_lower.split()):
            return ['Chairs', 'Office Chairs']
        if 'footstool' in name_lower.split() and price < Decimal('250'):
            if 'legs' not in name_lower.split():
                return ['Chairs', 'Ottomans and Footstools']
            set_miscellaneous = True
        if 'stool' in name_lower.split():
            if ('cover' in name_lower.split()) or ('frame' in name_lower.split()) or ('sofa' in name_lower.split()):
                set_miscellaneous = True
            else:
                return ['Chairs', 'Stools and Bar Stools']
        if ('children\'s ikea' in categories_lower) and ('bed' in name_lower.split()):
            if ('pocket' in name_lower.split()) or ('box' in name_lower.split()) or ('mattress' in name_lower.split())\
               or ('rail' in name_lower) or ('wood' in name_lower):
                set_miscellaneous = True
            elif 'combo' in name_lower.split():
                return ['Kids', 'Bunk Beds']
            else:
                return ['Kids', 'Beds']
        if 'children\'s' in name_lower and ('chairs' in name_lower.split() or 'stools' in name_lower.split()):
            return ['Kids', 'Tables & Chairs']
        if ('children\'s chairs, tables & play tents' in categories_lower) and \
           (('table' in name_lower) or ('chair' in name_lower)):
            return ['Kids', 'Tables & Chairs']
        if 'ceiling lights' in categories_lower:
            return ['Lighting', 'Ceiling Lights']
        if ('pendant lamp' in name_lower) or ('lamp shade' in name_lower):
            if 'decoration' not in name_lower.split():
                return ['Lighting', 'Pendant Caps and Shades']
            set_miscellaneous = True
        if 'wall lamp' in name_lower:
            return ['Lighting', 'Wall Lamps']
        if 'table' in name_lower and 'outdoor' in name_lower:
            return ['Outdoor', 'Outdoor Dining']
        if 'chair' in name_lower and 'outdoor' in name_lower:
            if ('pad' in name_lower.split()) or ('cushion' in name_lower.split()):
                set_miscellaneous = True
            else:
                return ['Outdoor', 'Outdoor Chairs']
        if 'lounger' in name_lower and 'outdoor' in name_lower:
            if 'cover' in name_lower:
                set_miscellaneous = True
            else:
                return ['Outdoor', 'Outdoor Loungers']
        if ('lounging & relaxing furniture' in categories_lower) and ('lounger' in name_lower):
            return ['Outdoor', 'Outdoor Loungers']
        if ('leather & faux leather sofas' in categories_lower) and ('corner sofa' in name_lower):
            return ['Sofas', 'Corner Leather Sofas']
        if ('leather & faux leather sofas' in categories_lower) and ('two seat' in name_lower):
            return ['Sofas', '2 Seater Leather Sofas']
        if ('leather & faux leather sofas' in categories_lower) and ('three seat' in name_lower):
            return ['Sofas', '3 Seater Leather Sofas']
        if ('leather & faux leather sofas' in categories_lower) and ('chaise' in name_lower):
            return ['Sofas', 'Leather Chaises']
        if ('fabric sofas' in categories_lower) and ('corner sofa' in name_lower):
            return ['Sofas', 'Corner Fabric Sofas']
        if ('fabric sofas' in categories_lower) and ('two seat' in name_lower):
            return ['Sofas', '2 Seater Fabric Sofas']
        if ('fabric sofas' in categories_lower) and ('three seat' in name_lower):
            return ['Sofas', '3 Seater Fabric Sofas']
        if ('fabric sofas' in categories_lower) and ('chaise' in name_lower):
            return ['Sofas', 'Fabric Chaises']
        if ('display cabinets' in categories_lower) or ('cabinets' in categories_lower):
            return ['Storage', 'Cabinets']
        if 'sideboard' in name_lower:
            return ['Storage', 'Sideboards']
        if 'storage bench' in name_lower:
            return ['Storage', 'Storage Benches']
        if 'storage table' in name_lower:
            return ['Storage', 'Storage Tables']
        if 'console table' in name_lower:
            return ['Tables', 'Console Tables']

        if set_miscellaneous:
            categories = ['Miscellaneous']

        return categories

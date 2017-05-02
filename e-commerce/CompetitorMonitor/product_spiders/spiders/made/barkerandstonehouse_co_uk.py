# -*- coding: utf-8 -*-

"""
Name: made-barkerandstonehouse.co.uk
Account: Made UK

IMPORTANT!!

- It uses category priority feature: https://www.assembla.com/spaces/competitormonitor/tickets/4466
- Changes to the category priority feature: https://www.assembla.com/spaces/competitormonitor/tickets/4713
- It uses cleaned names hashed as md5 as identifiers. That's because using the product ID provided by website it's not safe.

Developer of Category Priority Feature: Emiliano M. Rudenick <emr.frei@gmail.com>

"""


import re
from hashlib import md5
from scrapy import Spider, Request, FormRequest
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher


class BarkerandstonehouseSpider(Spider):
    name = 'made-barkerandstonehouse.co.uk'
    allowed_domains = ['barkerandstonehouse.co.uk']
    start_urls = ('https://www.barkerandstonehouse.co.uk/searchresults.php?search=',)
    download_timeout = 300

    '''
    PRIORITY_CATEGORIES format
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    List of tuples.

    Format:

    (<category1>&&<category2>&&..&&<categoryN>,
     <URL>,
     <keywords1>&&<keywords2>&&..&&<keywordsN>)

    Example:

    ('Living > Chairs&&Living > Footstools',
     'http://somecategoryurl.com/category',
     'chair!footstool&&footstool')

    In this example all products with "chair" in their name but without "footstool" into it
    will be included in Living > Chairs category.
    And then all products with "footstool" in their name will be included in Living > Footstools.
    This is only an example, the rules could be more simple:
    For example with keywords "footstool&&chair" and categories "Living > Footstools&&Living > Chairs"

    Keywords format:

    Use "*" to include all products
    Use "," to include all of: <kword1>,<kword2>,..,<kwordN>
    Use "|" to include any of: <kword1>|<kword2>|..|<kwrodN>
    Use "!" to exclude words: !<kwrod1>!<kword2>!..!<kwrodN>

    Example:

    sofa,2 seaters (Include sofa AND 2 seaters)
    sofa,2 seaters|two seaters (Include sofa and either "2 seaters" or "two seaters")
    sofa,bed!chair!footstool (Include sofa and bed, excluding any product with "chair" or "footstool" in its name)

    '''
    PRIORITY_CATEGORIES = [
        ('Sofas > Corner Leather Sofas',
         'http://www.barkerandstonehouse.co.uk/living-room/Corner-Sofas/view/Leather/',
         '*'),
        # temporary cat for leather sofas - should be transformed to proper category
        ('Sofas > Leather',
         'http://www.barkerandstonehouse.co.uk/living-room/Sofas/view/Leather/',
         '*'),
        ('Sofas > Corner Fabric Sofas',
         'http://www.barkerandstonehouse.co.uk/living-room/Corner-Sofas/view/Fabric/',
         '*'),
        # temporary cat for fabric sofas - should be transformed to proper category
        ('Sofas > Fabric',
         'http://www.barkerandstonehouse.co.uk/living-room/Sofas/view/Fabric/',
         '*'),
        ('Sofas > 2 Seater Sofas',
         'http://www.barkerandstonehouse.co.uk/living-room/Sofas/type/2/',
         '*'),
        ('Sofas > 3 Seater Sofas',
         'http://www.barkerandstonehouse.co.uk/living-room/Sofas/type/3/',
         '*'),
        ('Sofas > 4 Seater Sofas',
         'http://www.barkerandstonehouse.co.uk/living-room/Sofas/type/4/',
         '*'),
        ('Sofas > Corner Sofas',
         'http://www.barkerandstonehouse.co.uk/living-room/Corner-Sofas/',
         '*'),
        ('Chairs > Accent Chairs&&Chairs > Armchairs',
         'http://www.barkerandstonehouse.co.uk/living-room/Chairs/',
         'accent&&*'),
        ('Chairs > Dining Chairs',
         'http://www.barkerandstonehouse.co.uk/dining-room/Dining-Chairs/view/Leather/',
         '*'),
        ('Chairs > Dining Chairs',
         'http://www.barkerandstonehouse.co.uk/dining-room/Dining-Chairs/view/Fabric/',
         '*'),
        ('Chairs > Dining Chairs',
         'http://www.barkerandstonehouse.co.uk/dining-room/Dining-Chairs/view/Wood/',
         '*'),
        ('Chairs > Stools and Bar Stools',
         'http://www.barkerandstonehouse.co.uk/dining-room/Barstools/',
         '*'),
        ('Chairs > Office Chairs',
         'http://www.barkerandstonehouse.co.uk/home-office/Office-Chairs/',
         '*'),
        ('Chairs > Benches&&Chairs > Stools and Bar Stools&&Chairs > Love Seats',
         'http://www.barkerandstonehouse.co.uk/dining-room/Benches/',
         'bench!stool&&stool&&*'),
        ('Chairs > Kid\'s Chairs',
         'http://www.barkerandstonehouse.co.uk/childrens/Bedroom-Furniture/view/Childrens-Chairs/',
         '*'),
        ('Chairs > Ottomans and Footstools',
         'http://www.barkerandstonehouse.co.uk/living-room/Footstools/',
         'footstool|ottoman'),
        ('Tables > Extending Tables',
         'http://www.barkerandstonehouse.co.uk/extending-tables.php',
         '*'),
        ('Tables > Extending Tables&&Tables > Dining Tables',
         'http://www.barkerandstonehouse.co.uk/dining-room/Tables/',
         'extending&&*'),
        ('Tables > Coffee Tables',
         'http://www.barkerandstonehouse.co.uk/living-room/Occasional-Tables/view/Coffee/',
         '*'),
        ('Tables > Desks',
         'http://www.barkerandstonehouse.co.uk/home-office/Desks/',
         '*'),
        ('Tables > Dressing Tables',
         'http://www.barkerandstonehouse.co.uk/bedroom/Dressing-Tables/',
         '*'),
        ('Tables > Console Tables',
         'http://www.barkerandstonehouse.co.uk/living-room/Occasional-Tables/view/Console/',
         '*'),
        ('Storage > Bedside Tables',
         'http://www.barkerandstonehouse.co.uk/bedroom/Bedsides/',
         '*'),
        ('Storage > Bookcases & Shelves',
         'http://www.barkerandstonehouse.co.uk/living-room/Bookcases/',
         '*'),
        ('Storage > Chests of Drawers',
         'http://www.barkerandstonehouse.co.uk/bedroom/Chest-of-Drawers/',
         '*'),
        ('Storage > Wardrobes',
         'http://www.barkerandstonehouse.co.uk/bedroom/Wardrobes/',
         '*'),
        ('Storage > Sideboards',
         'http://www.barkerandstonehouse.co.uk/dining-room/Sideboards/',
         '*'),
        ('Storage > Cabinets',
         'http://www.barkerandstonehouse.co.uk/living-room/Display-Cabinets/',
         '*'),
        ('Storage > Kid\'s Storage',
         'http://www.barkerandstonehouse.co.uk/childrens/Bedroom-Furniture/view/Childrens-Storage/',
         '*'),
        ('Storage > Media Units',
         'http://www.barkerandstonehouse.co.uk/living-room/TV-and-Hi-fi-Units/',
         '*'),
        ('Lighting > Pendant Caps and Shades&&Lighting > Floor Lamps',
         'http://www.barkerandstonehouse.co.uk/accessories/Lighting/view/Floor-lamp/',
         'pendant&&*'),
        ('Lighting > Pendant Caps and Shades&&Lighting > Ceiling Lights',
         'http://www.barkerandstonehouse.co.uk/accessories/Lighting/view/Ceiling-light/',
         'pendant&&*'),
        ('Lighting > Pendant Caps and Shades&&Lighting > Table Lamps',
         'http://www.barkerandstonehouse.co.uk/accessories/Lighting/view/Table-lamp/',
         'pendant&&*'),
        ('Lighting > Pendant Caps and Shades&&Lighting > Wall Lamps',
         'http://www.barkerandstonehouse.co.uk/accessories/Lighting/view/Wall-light/',
         'pendant&&*'),
        ('Lighting > Pendant Caps and Shades',
         'http://www.barkerandstonehouse.co.uk/accessories/Lighting/',
         'pendant'),
        ('Bedroom > Kid\'s Beds',
         'http://www.barkerandstonehouse.co.uk/childrens/Childrens-Beds/view/Highsleeper/',
         '*'),
        ('Bedroom > Kid\'s Beds',
         'http://www.barkerandstonehouse.co.uk/childrens/Childrens-Beds/view/Midsleeper/',
         '*'),
        ('Bedroom > Sofa Beds',
         'http://www.barkerandstonehouse.co.uk/bedroom/Guest-Beds-and-Sofabeds/',
         '*'),
        ('Bedroom > Mattresses',
         'http://www.barkerandstonehouse.co.uk/bedroom/Mattress/',
         '*'),
        ('Accessories > Bed Sets and Towels',
         'http://www.barkerandstonehouse.co.uk/accessories/Bedding/view/Duvets/',
         '*'),
        ('Bedroom > Double Beds&&Bedroom > Super Kingsize Beds&&Bedroom > Kingsize Beds',
         'https://www.barkerandstonehouse.co.uk/bedroom/Bedframes/',
         'double&&super king&&king'),
        ('Kids > Bunk Beds',
         'http://www.barkerandstonehouse.co.uk/childrens/Childrens-Beds/view/Bunk/',
         '*'),
        ('Kids > Beds',
         'http://www.barkerandstonehouse.co.uk/childrens/Childrens-Beds/',
         '*'),
        ('Kids > Desks',
         'http://www.barkerandstonehouse.co.uk/childrens/Bedroom-Furniture/view/Childrens-Desks/',
         '*'),
        ('Kids > Storage',
         'http://www.barkerandstonehouse.co.uk/childrens/Bedroom-Furniture/view/Childrens-Storage',
         '*'),
        ('Kids > Tables & Chairs',
         'http://www.barkerandstonehouse.co.uk/childrens/Bedroom-Furniture/view/Childrens-Chairs/',
         '*'),
        ('Accessories > Art',
         'http://www.barkerandstonehouse.co.uk/accessories/Gallery/',
         '*'),
        ('Accessories > Cushions',
         'http://www.barkerandstonehouse.co.uk/accessories/Cushions/',
         '*'),
        ('Accessories > Clocks',
         'http://www.barkerandstonehouse.co.uk/accessories/Clocks/',
         '*'),
        ('Accessories > Throws & Blankets',
         'http://www.barkerandstonehouse.co.uk/accessories/Bedding/view/Throws/',
         '*'),
        ('Accessories > Coat Stands & Hooks',
         'http://www.barkerandstonehouse.co.uk/accessories/Coatstands-Hooks/',
         '*'),
        ('Accessories > Rugs',
         'http://www.barkerandstonehouse.co.uk/rugs/Rugs/',
         '*'),
        ('Accessories > Mirrors',
         'http://www.barkerandstonehouse.co.uk/bedroom/Mirrors/view/Wall-mirror/',
         '*'),
        ('Miscellaneous',
         'http://www.barkerandstonehouse.co.uk/bedroom/Mirrors/',
         '*'),
        ('Bed & Bath > Bedspreads & Blankets',
         'http://www.barkerandstonehouse.co.uk/accessories/Bedding/view/Bedspreads/',
         '*'),
        ('Outdoor > Outdoor Chairs',
         'http://www.barkerandstonehouse.co.uk/garden-furniture/Garden-Chairs/',
         '*'),
        ('Outdoor > Outdoor Dining',
         'http://www.barkerandstonehouse.co.uk/garden-furniture/Garden-Dining-Sets/',
         '*!side table!coffee table'),
        ('Outdoor > Outdoor Loungers',
         'http://www.barkerandstonehouse.co.uk/garden-furniture/Garden-Lounge-Sets/',
         '*'),
    ]

    def __init__(self, *args, **kwargs):
        super(BarkerandstonehouseSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

        self.try_next = True
        self.current_category = 0

    def start_requests(self):
        yield self.next_category_request()

    def spider_idle(self, *args, **kwargs):
        if self.try_next:
            req = self.next_category_request()
            if not req:
                self.try_next = False
                req = Request(self.start_urls[0])
            self.crawler.engine.crawl(req, self)

    def next_category_request(self):
        req = None
        total_categories = len(self.PRIORITY_CATEGORIES)
        if self.current_category < total_categories:
            category, url, kwrds = self.PRIORITY_CATEGORIES[self.current_category]
            self.current_category += 1
            req = Request(url, callback=self.parse,
                          meta={'category': category,
                                'kwrds': kwrds},
                          dont_filter=True)
        return req

    def parse(self, response):
        meta = {'download_timeout': 300}
        if 'category' in response.meta:
            meta['category'] = response.meta['category']
            meta['kwrds'] = response.meta['kwrds']
        urls = response.xpath('//div[@class="col-xs-6 col-md-4 push-center search-item"]/a/@href').extract()
        for url in urls:
            if '/carpets/' not in url and '/hard-flooring/' not in url and '/gift-vouchers/' not in url:
                yield Request(response.urljoin(url + '/'),
                              callback=self.parse_product,
                              meta=meta,
                              dont_filter=True)

    def parse_product(self, response):
        meta = {'download_timeout': 300}
        if 'category' not in response.meta:
            urls = response.xpath('//div[@class="row center-links product-range"]//a/@href').extract()
            for url in urls:
                if '/carpets/' not in url and '/hard-flooring/' not in url and '/gift-vouchers/' not in url:
                    yield Request(response.urljoin(url + '/'), callback=self.parse_product, meta=meta)

        name1 = response.xpath('//div[@class="tab-content"]//span[@class="push-left"]/text()').extract()
        if not name1:
            self.log('WARNING: No name in => %s' % response.url)
            retry_no = int(response.meta.get('retry_no', 0))
            if retry_no < 10:
                retry_no += 1
                self.log('Retry No. %s for page => %s' % (retry_no, response.url))
                req = response.request.copy()
                req.meta['retry_no'] = retry_no
                req.meta['recache'] = True
                req.dont_filter = True
                yield req
            else:
                self.log('Gave up retrying %(request)s (failed %(retries)d times)' %
                         {'request': response.request, 'retries': retry_no})
            return

        options = response.xpath('//div[@class="tab-content"]//table[@class="table table-hover"]/tbody/tr')
        if not options:
            options = response.xpath('//div[@class="tab-content"]//table[@class="table table-hover"]/tr')[1:]
        if options:
            for option in options:
                product_id = option.xpath('.//input[@name="stonehouse_4_ID_Add"]/@value').extract()
                if not product_id:
                    product_id = option.xpath('.//input[@name="size"]/@value').extract()

                if product_id:
                    product_id = product_id[0].strip()
                else:
                    self.log('Not product ID in => %s' % response.url)
                    continue

                name2 = option.xpath('.//input[@name="stonehouse_4_Colour_Add"]/@value').extract()
                name2 = filter(lambda s: bool(s.strip()), name2)
                if name2:
                    name2 = name2[0].strip()
                else:
                    name2 = ' - '.join(filter(lambda s: bool(s) and 'Made for you in ' not in s,
                                              map(unicode.strip, option.xpath('.//b/text()|.//b/following-sibling::text()').extract())))

                product_name = name1[0] + ' - ' + name2

                product_loader = ProductLoader(item=Product(), response=response)
                product_loader.add_value('name', product_name)
                sku = option.xpath('./td//small/text()').extract()
                if not sku:
                    sku = response.xpath('//div[@class="tab-content"]//div[contains(text(), "SKU:")]/text()').extract()

                sku = sku[0] if sku else ''
                sku = sku.replace('SKU: ', '')
                product_loader.add_value('sku', sku)
                image_url = option.xpath('./td[1]//a/@data-image').extract()
                if not image_url:
                    image_url = response.xpath('//*[@id="main"]/@src').extract()
                if image_url:
                    product_loader.add_value('image_url', response.urljoin(image_url[0]))

                price = option.xpath('./td//strong//text()').re(r'[\d,.]+')
                if price:
                    price = price[-1]
                if not price:
                    price = ''.join(response.xpath('//div[@class="price push-left"]//font[@size="5"]/text()').extract())
                price = extract_price(price)
                product_loader.add_value('price', price)
                category = response.xpath('//ol[@class="breadcrumb"]//a/text()').extract()[1:]
                if category[0] in ('Accessories', 'Rugs'):
                    product_loader.add_value('shipping_cost', 2.5)
                else:
                    product_loader.add_value('shipping_cost', 39)

                product_name = product_loader.get_output_value('name')
                if 'category' in response.meta:
                    new_category = self.get_category(
                        product_name,
                        response.meta['category'],
                        response.meta.get('kwrds', '*'))
                    if new_category is not None:
                        category = new_category

                category = transform_category(product_name, category)
                product_loader.add_value('category', category)
                product_loader.add_value('url', response.url)
                stock = ''.join(option.xpath('./td//text()').extract()).strip()
                if 'we have no stock' in stock:
                    product_loader.add_value('stock', 0)

                product = product_loader.load_item()
                if not product['price']:
                    # Try to get price from query
                    option_params = {
                        'stonehouse_6_Quantity_Add': '1',
                        'stonehouse_6_Stock_Add': '',
                        'stonehouse_6_NextPODate_Add': '',
                        'stonehouse_6_Lead_Add': '',
                        'stonehouse_6_ID_Add2': 'NONE',
                        'stonehouse_6_ID_Add3': 'NONE',
                        'stonehouse_6_ID_Add4': 'NONE',
                    }
                    option_params['stonehouse_6_ID_Add'] = str(product_id)
                    option_params['size'] = str(product_id)
                    yield FormRequest(response.url,
                                      formdata=option_params,
                                      dont_filter=True,
                                      meta={'product': product},
                                      callback=self.parse_size)
                else:
                    product['identifier'] = self._get_identifier(product)
                    yield product
        else:
            price = response.xpath('//div[@class="price push-left"]//font[@size="5"]/text()').extract()
            if not price:
                return

            product_loader = ProductLoader(item=Product(), response=response)
            name2 = response.xpath('//div[@class="tab-content"]//table//td[text()="Colour:"]/following-sibling::td/text()').extract()

            if name2:
                product_loader.add_value('name', name1[0] + ' ' + name2[0])
            else:
                product_loader.add_value('name', name1[0])
            sku = response.xpath('//div[@class="tab-content"]//table//td[text()="SKU:"]/following-sibling::td/text()').extract()
            if sku:
                product_loader.add_value('sku', sku)
            image_url = response.xpath('//*[@id="main"]/@src').extract()
            if image_url:
                product_loader.add_value('image_url', response.urljoin(image_url[0]))
            price = extract_price(price[0])
            product_loader.add_value('price', price)
            category = response.xpath('//ol[@class="breadcrumb"]//a/text()').extract()[1:]
            if category[0] in ('Accessories', 'Rugs'):
                product_loader.add_value('shipping_cost', 2.5)
            else:
                product_loader.add_value('shipping_cost', 39)

            product_name = product_loader.get_output_value('name')
            if 'category' in response.meta:
                new_category = self.get_category(
                    product_name,
                    response.meta['category'],
                    response.meta.get('kwrds', '*'))
                if new_category is not None:
                    category = new_category

            category = transform_category(product_name, category)
            product_loader.add_value('category', category)
            product_loader.add_value('url', response.url)
            stock = response.xpath('//div[@class="tab-content"]//table//td[text()="Availability:"]/following-sibling::td//text()').extract()[0]
            if 'we have no stock' in stock:
                product_loader.add_value('stock', 0)
            product = product_loader.load_item()

            product['identifier'] = self._get_identifier(product)
            yield product


    def parse_size(self, response):
        main_product = response.meta['product']
        size_options = response.xpath(u'//td[contains(strong/text(), "£")]')
        for size_xs in size_options:
            option_name = size_xs.xpath('text()').extract()[0].strip()
            new_product = Product(main_product)
            new_product['name'] = main_product['name'] + ' - ' + option_name
            new_product['price'] = extract_price(size_xs.xpath('strong/text()').re(r'[\d,.]+')[0])
            new_product['identifier'] = self._get_identifier(new_product)
            yield new_product

    def _get_identifier(self, product):
        identifier = md5(''.join(re.findall(r'\w+', product['name'])).lower()).hexdigest()
        return identifier

    def get_category(self, product_name, category, kwrds):
        category_options = category.split('&&')
        kwrds_options = kwrds.split('&&')
        for cat_opt, kwrds_opt in zip(category_options, kwrds_options):
            if self.valid_category(product_name, kwrds_opt):
                return cat_opt.split(' > ')
        return None

    def valid_category(self, product_name, kwrds):
        if kwrds != '*':
            inc_kwrds = kwrds.split('!')[0].split(',')
            exc_kwrds = kwrds.split('!')[1:]
            # Exclude words
            for w in exc_kwrds:
                if w.lower() in product_name.lower():
                    return False
            if inc_kwrds and inc_kwrds[0] != '*':
                # Include words
                for w in inc_kwrds:
                    # "|" means OR
                    if not any([wo.lower() in product_name.lower() for wo in w.split('|')]):
                        return False
        return True


category_mapping = {
    'storage > kid\'s storage': ['Kids', 'Storage'],
}


special_category_mapping = {
    'dining room > bedframes': {
        'double': ['Bedroom', 'Double Beds'],
        'king': ['Bedroom', 'Kingsize Beds']
    },
    'bedroom > bedframes': {
        'double': ['Bedroom', 'Double Beds'],
        'king': ['Bedroom', 'Kingsize Beds']
    },
    'lighting > floor lamps': {
        'pendant': ['Lighting', 'Pendant Caps and Shades'],
    },
    'lighting > ceiling lamps': {
        'pendant': ['Lighting', 'Pendant Caps and Shades'],
    },
    'lighting > table lamps': {
        'pendant': ['Lighting', 'Pendant Caps and Shades'],
    },
    'lighting > wall lamps': {
        'pendant': ['Lighting', 'Pendant Caps and Shades'],
    },
    'sofas > leather': {
        'small sofa': ['Sofas', '2 Seater Leather Sofas'],
        '2 seater': ['Sofas', '2 Seater Leather Sofas'],
        '3 seater': ['Sofas', '3 Seater Leather Sofas'],
        '4 seater': ['Sofas', '4 Seater Leather Sofas'],
    },
    'sofas > fabric': {
        'small sofa': ['Sofas', '2 Seater Fabric Sofas'],
        '2 seater': ['Sofas', '2 Seater Fabric Sofas'],
        '3 seater': ['Sofas', '3 Seater Fabric Sofas'],
        '4 seater': ['Sofas', '4 Seater Fabric Sofas'],
    },
}


word_only_category_mapping = {
    'loveseat': ['Chairs', 'Love Seats'],
    'bunk bed': ['Kids', 'Bunk Beds'],
    'storage bench': ['Storage', 'Storage Benches'],
}


def transform_category(product_name, category):
    """
    >>> transform_category('Cavendish - 2 Seater Sofa VINTAGE CIGAR', 'Sofas > Leather')
    ['Sofas', '2 Seater Leather Sofas']

    :param product_name:
    :param category:
    :return:
    """
    for word in word_only_category_mapping:
        if word in product_name.lower():
            return word_only_category_mapping[word]

    if not isinstance(category, basestring):
        key_category = ' > '.join(category)
    else:
        key_category = category
    # check for special categories
    special_cat_data = special_category_mapping.get(key_category.lower())
    if special_cat_data:
        for word in sorted(special_cat_data):
            if word in product_name.lower():
                return special_cat_data[word]

    new_cat = category_mapping.get(key_category.lower())
    if new_cat:
        return new_cat

    return category

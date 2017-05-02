"""
Name: made-habitat
Account: Made UK

IMPORTANT!!

- It uses category priority feature: https://www.assembla.com/spaces/competitormonitor/tickets/4479
- Changes to the category priority feature: https://www.assembla.com/spaces/competitormonitor/tickets/4641
- Changes to the category priority feature: https://www.assembla.com/spaces/competitormonitor/tickets/4715

Developer of Category Priority Feature: Emiliano M. Rudenick <emr.frei@gmail.com>

"""


import os
import csv
from decimal import Decimal
from scrapy import Spider, Request
from scrapy.utils.url import add_or_replace_parameter
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.config import DATA_DIR


class HabitatSpider(Spider):
    name = 'made-habitat'
    allowed_domains = ['habitat.co.uk']
    start_urls = ['http://www.habitat.co.uk/',]

    rotate_agent = True

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
        ('Tables > Extending&&Tables > Dining Tables',
         'http://www.habitat.co.uk/furniture/dining-room/dining-tables',
         'Extending&&*'),
        ('Tables > Coffee Tables',
         'http://www.habitat.co.uk/furniture/living-room/coffee-tables',
         '*'),
        ('Tables > Side Tables',
         'http://www.habitat.co.uk/furniture/living-room/side-tables',
         '*'),
        ('Tables > Desks',
         'http://www.habitat.co.uk/furniture/office/desks-office-chairs',
         'Desk'),
        ('Tables > Bedside Tables&&Tables > Bedside Tables',
         'http://www.habitat.co.uk/furniture/bedroom/bedside-and-chest-of-drawers',
         'bedside table&&Bedside'),
        ('Storage > Media Units',
         'http://www.habitat.co.uk/furniture/living-room/tv-units',
         '*'),
        ('Tables > Dressing Tables',
         'http://www.habitat.co.uk/furniture/bedroom/dressing-tables',
         '*'),
        ('Tables > Console Tables',
         'http://www.habitat.co.uk/furniture/living-room/console-tables',
         '*'),
        ('Storage > Bookcases & Shelves',
         'http://www.habitat.co.uk/furniture/living-room/bookcases-and-shelving',
         '*'),
        ('Storage > Wardrobes',
         'http://www.habitat.co.uk/furniture/bedroom/wardrobes',
         '*'),
        ('Storage > Sideboards&&Storage > Cabinets',
         'http://www.habitat.co.uk/furniture/dining-room/sideboards-cupboards-cabinets',
         'Sideboard&&Cabinet!bedside'),
        ('Lighting > Floor Lamps',
         'http://www.habitat.co.uk/lighting/shop-by-category/floor-lamps',
         '*'),
        ('Lighting > Ceiling Lights',
         'http://www.habitat.co.uk/lighting/shop-by-category/ceiling-lights?limit=all',
         '*'),
        ('Lighting > Table Lamps',
         'http://www.habitat.co.uk/lighting/shop-by-category/table-lamps',
         '*'),
        ('Bedroom > Double Beds&&Bedroom > Kingsize Beds&&Bedroom > Storage Beds&&Bedroom > Super Kingsize Beds',
         'http://www.habitat.co.uk/furniture/bedroom/beds',
         'Double&&Kingsize&&Bed With Storage&&super king bed'),
        ('Bedroom > Sofa Bed',
         'http://www.habitat.co.uk/sofas-armchairs/sofas-categories/sofa-beds',
         '*'),
        ('Bedroom > Mattresses',
         'http://www.habitat.co.uk/furniture/bedroom/mattresses',
         '*'),
        ('Bedroom > Mattresses',
         'http://www.habitat.co.uk/furniture/bedroom/mattresses/pocket-spring-mattresses',
         '*'),
        ('Bedroom > Mattresses',
         'http://www.habitat.co.uk/furniture/bedroom/mattresses/memory-foam-mattresses',
         '*'),
        ('Bedroom > Mattresses',
         'http://www.habitat.co.uk/furniture/bedroom/mattresses/back-care-mattresses',
         '*'),
        ('Bedroom > Mattresses',
         'http://www.habitat.co.uk/furniture/bedroom/mattresses/natural-mattresses',
         '*'),
        ('Bedroom > Mattresses',
         'http://www.habitat.co.uk/furniture/bedroom/mattresses/kids-mattresses',
         '*'),
        ('Bedroom > Mattresses',
         'http://www.habitat.co.uk/furniture/bedroom/mattresses/open-spring-mattresses',
         '*'),
        ('Accessories > Bed Sets and Towels',
         'http://www.habitat.co.uk/soft-furnishing/shop-by-category/bathroom-towels',
         '*!mat'),
        ('Accessories > Bed Sets and Towels',
         'http://www.habitat.co.uk/soft-furnishing/shop-by-category/bedding?limit=all',
         'set!mat'),
        ('Accessories > Art',
         'http://www.habitat.co.uk/accessories/shop-by-category/wall-art',
         '*'),
        ('Miscellaneous&&Accessories > Cushions',
         'http://www.habitat.co.uk/soft-furnishing/shop-by-category/cushions',
         'bag&&*'),
        ('Accessories > Clocks',
         'http://www.habitat.co.uk/accessories/shop-by-category/clocks',
         'wall!alarm'),
        ('Accessories > Bins',
         'http://www.habitat.co.uk/kitchen/shop-by-category/bins',
         '*'),
        ('Accessories > Rugs',
         'http://www.habitat.co.uk/soft-furnishing/shop-by-category/rugs',
         '*'),
        ('Accessories > Mirrors',
         'http://www.habitat.co.uk/accessories/shop-by-category/mirrors',
         '*'),
        ('Accessories > Kid\'s accessories',
         'http://www.habitat.co.uk/accessories/shop-by-category/kids-toys',
         '*'),
        ('Chairs > Armchairs',
         'http://www.habitat.co.uk/sofas-armchairs/sofas-categories/armchairs',
         '*'),
        ('Chairs > Stools and Bar Stools',
         'http://www.habitat.co.uk/furniture/dining-room/stools',
         '*'),
        ('Kids > Storage&&Kids > Tables & Chairs',
         'http://www.habitat.co.uk/furniture/bedroom/kids-bedroom/kids-furniture',
         'storage|drawer!bed&&table|chair'),
        ('Outdoor > Outdoor Chairs&&Outdoor > Outdoor Dining&&Outdoor > Outdoor Loungers',
         'http://www.habitat.co.uk/outdoor/shop-by-category/outdoor-furniture',
         'chair!set!canvas!table&&table!lounger&&lounger!sling'),
    ]

    PRODUCTS_NAME_CATEGORIES = [
        ('coat stand', 'Accessories > Coat Stands & Hooks'),
        ('coat rack', 'Accessories > Coat Stands & Hooks'),
        ('wall hooks', 'Accessories > Coat Stands & Hooks'),
        ('garden chair,set', 'Outdoor > Outdoor Dining'),
        ('garden chair', 'Outdoor > Outdoor Chairs'),
        ('garden dining chair', 'Outdoor > Outdoor Chairs'),
        ('garden table', 'Outdoor > Outdoor Dining'),
        ('dining chair!pad', 'Chairs > Dining Chairs'),
        ('office chair', 'Chairs > Office Chairs'),
        ('cabinet!bedside', 'Storage > Cabinets'),
        ('drawer chest', 'Storage > Chests of Drawers'),
        ('drawer wide chest', 'Storage > Chests of Drawers'),
        ('sideboards', 'Storage > Sideboards'),
        ('storage bench', 'Storage > Storage Benches'),
        ('wardrobes', 'Storage > Wardrobes'),
        ('throw', 'Accessories > Throws & Blankets'),
        ('bedset', 'Accessories > Throws & Blankets'),
        ('bedside table', 'Tables > Bedside Tables'),
        ('sofa bed', 'Bedroom > Sofa Beds'),
        ('bed with storage', 'Bedroom > Storage Beds'),
        ('super king bed', 'Bedroom > Super Kingsize Beds'),
        ('beanbag', 'Chairs > Bean Bags'),
        ('bench', 'Chairs > Benches'),
        ('chair pad', 'Miscellaneous'),
        ('office chair', 'Chairs > Office Chairs'),
        ('ottoman!set', 'Chairs > Ottomans and Footstools'),
        ('footstool', 'Chairs > Ottomans and Footstools'),
        ('kid\'s,bed,bunk', 'Kids > Bunk Beds'),
        ('kid\'s,bed', 'Kids > Beds'),
        ('kids,table,chair', 'Kids > Tables & Chairs'),
        ('ceiling lights', 'Lighting > Ceiling Lights'),
        ('wall light', 'Lighting > Wall Lamps'),
        ('leather 2 seater sofa', 'Sofas > 2 Seater Leather Sofas'),
        ('leather 3 seater sofa', 'Sofas > 3 Seater Leather Sofas'),
        ('leather 4 seater sofa', 'Sofas > 4 Seater Leather Sofas'),
        ('leather,chaises', 'Sofas > Leather Chaises'),
        ('fabric,chaises', 'Sofas > Fabric Chaises'),
        ('leather,corner sofa', 'Sofas > Corner Leather Sofas'),
        ('fabric,corner sofa', 'Sofas > Corner Fabric Sofas'),
        ('fabric 2 seater sofa', 'Sofas > 2 Fabric Leather Sofas'),
        ('fabric 3 seater sofa', 'Sofas > 3 Fabric Leather Sofas'),
        ('fabric 4 seater sofa', 'Sofas > 4 Fabric Leather Sofas'),
        ('extending dining table', 'Tables > Extending Tables'),
      ]

    def __init__(self, *args, **kwargs):
        super(HabitatSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

        self.try_next = True
        self.current_category = 0

    def start_requests(self):
        if hasattr(self, 'prev_crawl_id'):
            with open(os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    yield Request(row['url'],
                                  callback=self.parse_product,
                                  meta={'product': dict(row)})
        else:
            yield self.next_category_request()

    def spider_idle(self, *args, **kwargs):
        if self.try_next:
            req = self.next_category_request()
            if not req:
                self.try_next = False
                req = Request(self.start_urls[0], dont_filter=True)
            self.crawler.engine.crawl(req, self)

    def next_category_request(self):
        req = None
        total_categories = len(self.PRIORITY_CATEGORIES)
        if self.current_category < total_categories:
            category, url, kwrds = self.PRIORITY_CATEGORIES[self.current_category]
            self.current_category += 1
            url = add_or_replace_parameter(url, 'limit', 'all')
            req = Request(url,
                          callback=self.parse_cat,
                          meta={'category': category,
                                'dont_merge_cookies':True,
                                'kwrds': kwrds},
                          dont_filter=True)
        return req

    def parse(self, response):
        for url in response.xpath('//nav[@id="nav"]//a/@href').extract():
            url = response.urljoin(url)
            url = add_or_replace_parameter(url, 'limit', 'all')
            yield Request(url,
                          callback=self.parse_cat,
                          meta={'dont_merge_cookies':True})

    def parse_cat(self, response):
        # Next page
        for url in response.xpath('//a[@title="Next"]/@href').extract():
            yield Request(response.urljoin(url),
                          callback=self.parse_cat,
                          meta=response.meta)

        website_categories = response.xpath('//div[@class="grid-full breadcrumbs"]//span[@itemprop="name"]/text()').extract()[-2:]
        website_categories = ' > '.join(website_categories)
        if 'category' not in response.meta:
            category_urls = response.xpath('//div[@class="widget-category-list"]//a/@href').extract()
            category_urls += response.xpath('//div[@id="shop-by-range"]//li/a/@href').extract()
            for url in category_urls:
                url = response.urljoin(url)
                url = add_or_replace_parameter(url, 'limit', 'all')
                yield Request(url,
                              callback=self.parse_cat,
                              meta=response.meta)

        categories = response.meta.get('category', '')
        for url in response.xpath('//h2[@class="product-name"]//a/@href').extract():
            yield Request(url, callback=self.parse_product,
                          meta={'category': categories,
                                'website_categories': website_categories,
                                'kwrds': response.meta.get('kwrds', '')})

    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)

        identifier = response.xpath('//div[@id="habtat-sku"]/text()').re('Product Code: (\d+)')
        if not identifier:
            return
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//div[@class="product-name"]/h1//text()')
        loader.add_xpath('name', '//div/text()', re='Colour.*:(.+)')

        product_name = loader.get_output_value('name')
        if 'product' in response.meta:
            category = response.meta['product']['category'].split(' > ')
        else:
            website_category = response.meta['website_categories']
            categories = response.meta['category']
            kwrds = response.meta.get('kwrds', '')
            category = self.get_category(product_name, categories, kwrds)
            if not category:
                category = website_category.split(' > ')

        loader.add_value('category', category)
        loader.add_xpath('price', '//div[@class="price-info"]//span[contains(@id, "product-price")]//span/text()')
        if not loader.get_output_value('price'):
            loader.add_xpath('price', '//p[@class="special-price"]/span[@class="price"]/text()')
        price = loader.get_output_value('price')
        if price and Decimal(price) < 50.0:
            loader.add_value('shipping_cost', '4.95')
        img = response.xpath('//div[@class="product-img-box"]/div/a/@href').extract()
        if img:
            loader.add_value('image_url', response.urljoin(img[0]))
        if loader.get_output_value('price'):
            loader.add_value('stock', '1')
        else:
            loader.add_value('stock', '0')

        yield loader.load_item()

    def get_category_by_name(self, product_name):
        category = ''
        for kword, pcat in self.PRODUCTS_NAME_CATEGORIES:
            exclude = kword.split('!')[1:]
            kwords = kword.split('!')[0].split(',')
            valid_cat = True
            for kw in kwords:
                if kw.lower() not in product_name.lower():
                    valid_cat = False
                    break
            for exc in exclude:
                if exc in product_name.lower():
                    valid_cat = False
                    break
            if valid_cat:
                category = pcat
                break
        return category

    def get_category(self, product_name, category, kwrds):
        category_by_name = self.get_category_by_name(product_name)
        if category_by_name:
            return category_by_name
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

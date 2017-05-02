import re
import os
import csv
from urlparse import urljoin

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy import log

from product_spiders.base_spiders.matcher import Matcher
from product_spiders.items import Product, ProductLoader

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, get_speed_rating, get_alt_speed, \
    find_brand_segment, find_man_mark, unify_brand


HERE = os.path.abspath(os.path.dirname(__file__))

class LoveTyresSpider(BaseSpider):
    name = 'lovetyres.com_test'
    allowed_domains = ['lovetyres.com']
    start_urls = ('http://www.lovetyres.com',)
    tyre_sizes = []
    all_man_marks = {}

    def __init__(self, *args, **kwargs):
        super(LoveTyresSpider, self).__init__(*args, **kwargs)
        self.matcher = Matcher(self.log)

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.tyre_sizes.append(row)

        with open(os.path.join(HERE, 'manmarks.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.all_man_marks[row['code']] = row['manufacturer_mark']

        self.errors = []

    def start_requests(self):
        for row in self.tyre_sizes:
            search = str(row['Width']) + '/' + str(row['Aspect Ratio']) + \
                     str(row['Speed rating']) + str(row['Rim'])
            yield Request('http://www.lovetyres.com/search/tyres/{Width}-{Aspect Ratio}-{Rim}'.format(**row),
                          meta={'search': search}, callback=self.parse)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
  
        products = hxs.select('//tr[contains(@class,"tyre-search-row")]')

        next_page = []
        if next_page:
            yield Request(urljoin(base_url, next_page[0]), meta=response.meta)

        for product in products:
            url = product.select('.//td/b/a/@href')[0].extract()
            winter_tyre = product.select('.//td/b/a/text()')[0].extract()
            winter_tyre = 'winter' in winter_tyre.lower()
            if not winter_tyre:
                brand = product.select('.//a/img/@src')[0].extract()
                brand = re.search('/public/brands/(.*?)(-tyres)?\.', brand).group(1).replace('-', ' ').title()
                meta = response.meta
                meta['brand'] = brand
                price = product.select("td[3]/b/text()").extract()
                if price:
                    meta['price'] = price[0]
                yield Request(urljoin(base_url, url), callback=self.parse_product, meta=meta)
            
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_loader = ProductLoader(item=Product(), selector=hxs)
        # the full name of the tyre (name variable) is used to extract metadata (i.e. run flat, xl),
        # the pattern should be set as the product's name
        brand = response.meta.get('brand') or ''
        product_name = hxs.select('//h2[@class="heading black"]/text()')[0].extract().strip()
        product_name = re.sub(brand, '', product_name).strip()
        fitting_method = 'Delivered'
    
        base_loader.add_value('url', response.url)
    
        image_url = hxs.select('//div[@class="item"]/a/img/@src').extract()
        options = hxs.select('//div[@style="background: #fff; padding: 6px; "]')
        for option in options:
            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('name', product_name)
            loader.add_value('brand', unify_brand(brand))
            loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
            loader.add_value('url', response.url)
            if image_url:
                loader.add_value('image_url', urljoin(get_base_url(response), image_url[0]))
            identifier = option.select('../input[@type="hidden" and @name="item_id"]/@value').extract()
            if not identifier:
                identifier = option.select('./a/@href').re('email_me_stock/(.*)')
            if not identifier:
                continue
            loader.add_value('identifier', identifier[0])
            price = option.select('./strong[@class="price" and not(contains(text(),"On Backorder"))]/text()').extract()
            if price:
                loader.add_value('price', price[0]) 
            else:
                if response.meta.get('price'):
                    loader.add_value('price', response.meta['price'])
                else:
                    loader.add_value('price', '0.00')
                loader.add_value('stock', 0)
        
            pattern_name = option.select('./p/strong/text()').extract()
            if not pattern_name:
                pattern_name = option.select('./strong/text()').extract()
            pattern_name = pattern_name[0]
            data = re.search('(?P<Width>\d+)/(?P<Aspect_Ratio>\d+) R(?P<Rim>\d+) (?P<Speed_Rating>[A-Za-z]{1,2}) \((?P<Load_Rating>\d+).*?\)',
                              pattern_name)
            if data:
                data = data.groupdict()
            else:
                msg = 'ERROR parsing "{}" [{}]'.format(pattern_name, response.url)
                log.msg(msg)
                self.errors.append(msg)
                continue
            metadata = MicheldeverMeta()
            metadata['aspect_ratio'] = data['Aspect_Ratio']
            metadata['rim'] = data['Rim']
            metadata['speed_rating'] = data['Speed_Rating'].upper()
        
            metadata['width'] = data['Width']
            metadata['fitting_method'] = fitting_method
            metadata['load_rating'] = data['Load_Rating'] or ''
            metadata['alternative_speed_rating'] = ''
            xl = 'XL' in pattern_name
            metadata['xl'] = 'Yes' if xl else 'No'
        
            run_flat = 'run flat' in pattern_name.lower() or 'runflat' in pattern_name.lower()
            metadata['run_flat'] = 'Yes' if run_flat else 'No'
            manufacturer_mark = [mark for mark in self.all_man_marks.keys() if mark in pattern_name.split(' ')]
            manufacturer_mark = manufacturer_mark[0].strip() if manufacturer_mark else []
            metadata['manufacturer_mark'] = find_man_mark(manufacturer_mark) if manufacturer_mark else ''

            metadata['full_tyre_size'] = '/'.join((metadata['width'],
                                                   metadata['aspect_ratio'],
                                                   metadata['rim'],
                                                   metadata['load_rating'], 
                                                   metadata['speed_rating']))
                                                    #metadata['alternative_speed_rating']))
        
            product = loader.load_item()
            product['metadata'] = metadata

            if not is_product_correct(product):
                continue

            product['metadata']['mts_stock_code'] = find_mts_stock_code(product, spider_name=self.name, log=self.log)

            new_speed_rating = get_speed_rating(product)
            new_alt_speed = get_alt_speed(product)
            product['metadata']['alternative_speed_rating'] = new_alt_speed if new_alt_speed else \
                product['metadata']['speed_rating'] if product['metadata']['speed_rating'] != new_speed_rating else ''
            product['metadata']['speed_rating'] = new_speed_rating
        
            yield product
        
    def match_name(self, search_name, new_item, match_threshold=80, important_words=None):
        r = self.matcher.match_ratio(search_name, new_item, important_words)
        return r >= match_threshold

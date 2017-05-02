import re
import os
import csv
from urlparse import urljoin

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import FormRequest
from scrapy.utils.response import get_base_url
from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, get_speed_rating, get_alt_speed, \
    find_brand_segment, unify_brand


HERE = os.path.abspath(os.path.dirname(__file__))

class TyresPneusOnlineSpider(BaseSpider):
    name = 'tyres-pneus-online.co.uk_test'
    allowed_domains = ['tyres-pneus-online.co.uk']
    start_urls = ('http://www.tyres-pneus-online.co.uk/',)
    tyre_sizes = []
    all_man_marks = {}

    def __init__(self, *args, **kwargs):
        super(TyresPneusOnlineSpider, self).__init__(*args, **kwargs)

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
            formdata = {'affichage': '200',
             'diametre': str(row['Rim']),
             'hauteur': str(row['Aspect Ratio']),
             'idProduitPanierMetaPart1': '',
             'idTypeProduit': '1',
             'largeur': str(row['Width']),
             'tri': 'prix_desc',
             'recherche': 'Search'}
            yield FormRequest('http://www.tyres-pneus-online.co.uk/search-size/', formdata=formdata,
                          meta={'formdata': formdata, 'row': row, 'search': search}, callback=self.parse)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
  
        products = hxs.select('//ul[@class="c-list-classic c-list-classic-liste m-produit-res"]/li')

        next_page = hxs.select('//li[a[span[text()="Next"]]]/@data-page').extract()  # pagination
        if next_page:
            formdata = response.meta.get('formdata')
            formdata['page'] = next_page[0]
            yield FormRequest(response.url, formdata=formdata, dont_filter=True, meta=response.meta)

        for product_el in products:
            url = product_el.select('.//a[@class="u-semi-link"]/@href')[0].extract()
            winter_tyre = product_el.select('.//div[@class="m-produit-bloc-res-lst__gamme-saison"]/text()').re('Winter')
            if not winter_tyre:    
                loader = ProductLoader(item=Product(), selector=product_el)
                # the full name of the tyre (name variable) is used to extract metadata (i.e. run flat, xl),
                # the pattern should be set as the product's name
                loader.add_xpath('name', './/span[@class="m-produit-bloc-res-lst__dcp"]/text()')
                brand = product_el.select('.//span[@class="m-produit-bloc-res-lst__fab"]/text()').extract()
                if brand:
                    brand = brand[0].strip()
                    loader.add_value('brand', unify_brand(brand))
                loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
                fitting_method = 'Delivered'
            
                loader.add_value('url', urljoin(base_url, url))
            
                image_url = product_el.select('.//div[@class="m-produit-bloc-res-lst__image"]//img/@src').extract()
                if image_url:
                    loader.add_value('image_url', urljoin(get_base_url(response), image_url[0]))
                
                identifier = product_el.select('.//button/@data-id')[0].extract()
                loader.add_value('identifier', identifier)
                price = product_el.select('.//div[@class="c-qte-prix__prix m-produit-bloc-res-lst__prix"]/text()')[0].extract()
                loader.add_value('price', price) 
                if not loader.get_output_value('price'):
                    loader.add_value('stock', 0)
            
                name = product_el.select('.//div[@class="m-produit-bloc-res-lst__dim"]/text()')[0].extract().strip().replace(u'\xa0', u' ')
                data = parse_pattern(name)
                if not data:
                    log.msg('ERROR parsing "{}" [{}]'.format(name, response.url))
                    self.errors.append('ERROR parsing "{}" [{}]'.format(name, response.url))
                    continue
                    
                additional_data = ' '.join(product_el.select('.//ul[@class="m-produit__carac c-list-horizontale"]/li/text()').extract())
                metadata = MicheldeverMeta()
                metadata['aspect_ratio'] = data['Aspect_Ratio']
                metadata['rim'] = data['Rim']
                metadata['speed_rating'] = data['Speed_Rating']
            
                metadata['width'] = data['Width']
                metadata['fitting_method'] = fitting_method
                metadata['load_rating'] = data['Load_Rating'] or ''
                metadata['alternative_speed_rating'] = ''
                xl = 'XL' in additional_data
                metadata['xl'] = 'Yes' if xl else 'No'
            
                run_flat = 'runflat' in additional_data.lower()
                metadata['run_flat'] = 'Yes' if run_flat else 'No'
                manufacturer_mark = [mark for mark in self.all_man_marks.keys() if re.search('\(?{}\)?'.format(mark.replace('*', '\*')), additional_data)]
                manufacturer_mark = manufacturer_mark[0].strip() if manufacturer_mark else []
                metadata['manufacturer_mark'] = self.all_man_marks.get(manufacturer_mark, '') if manufacturer_mark \
                                                                                              else ''
                metadata['mts_stock_code'] = ''
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


def parse_pattern(pattern):
    """
    >>> parse_pattern('215/55 R16 93 V') == {'Width': '215', 'Aspect_Ratio': '55', 'Rim': '16', 'Load_Rating': '93', 'Speed_Rating': 'V'}
    True
    >>> parse_pattern('205/65 R16 107/105 R') == {'Width': '205', 'Aspect_Ratio': '65', 'Rim': '16', 'Load_Rating': '107/105', 'Speed_Rating': 'R'}
    True
    >>> parse_pattern('33/12.5 R15 108 R') == {'Width': '33', 'Aspect_Ratio': '12.5', 'Rim': '15', 'Load_Rating': '108', 'Speed_Rating': 'R'}
    True
    """
    data = re.search('(?P<Width>\d+)/(?P<Aspect_Ratio>\d+\.?\d*) R(?P<Rim>\d+) (?P<Load_Rating>\d+/?\d*)? ?(?P<Speed_Rating>.{1,2})',
                     pattern)
    if data:
        return data.groupdict()
    else:
        return None
import re
import os
import csv
import urlparse

from scrapy import Spider, Request, FormRequest
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.base_spiders.matcher import Matcher

from product_spiders.items import Product, ProductLoader

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, find_brand_segment, \
    find_man_mark, unify_brand, is_run_flat


HERE = os.path.abspath(os.path.dirname(__file__))


class MyTyresSpider(Spider):
    name = 'mytyres.co.uk'
    allowed_domains = ['mytyres.co.uk']
    start_urls = ('http://www.mytyres.co.uk',)
    tyre_sizes = []

    rotate_agent = True

    def __init__(self, *args, **kwargs):
        super(MyTyresSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        self.matcher = Matcher(self.log)

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.tyre_sizes.append(row)

        self.ip_codes = {}
        self.ip_codes_filename = os.path.join(HERE, 'mytyres_ip_codes.csv')
        if os.path.exists(self.ip_codes_filename):
            with open(self.ip_codes_filename) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.ip_codes[row['identifier']] = row['ip_code']


        self.errors = []

        self.search_history = set()

    def spider_closed(self, spider):
        with open(self.ip_codes_filename, 'w') as f:
            writer = csv.DictWriter(f, ['identifier', 'ip_code'])
            writer.writeheader()
            for identifier, ip_code in self.ip_codes.iteritems():
                new_row = {'identifier': identifier, 'ip_code': ip_code}
                writer.writerow(new_row)

    def _get_history_key(self, search_params):
        key = "%(width)s-%(rim)s-%(aspect_ratio)s-%(speed_rating)s" % search_params
        return key

    def check_in_history(self, search_params):
        if self._get_history_key(search_params) in self.search_history:
            return True
        return False

    def add_to_history(self, search_params):
        self.search_history.add(self._get_history_key(search_params))

    def start_requests(self):
        for i, row in enumerate(self.tyre_sizes, 1):
            for speed_rating in [row['Speed rating'], row['Alt Speed']]:
                if not speed_rating:
                    continue

                search_params = {
                    'width': row['Width'],
                    'aspect_ratio': row['Aspect Ratio'],
                    'speed_rating': speed_rating,
                    'rim': row['Rim']
                }

                if self.check_in_history(search_params):
                    continue

                self.add_to_history(search_params)

                formdata = {}
                search = str(search_params['width']) + '/' + str(search_params['aspect_ratio']) + \
                         str(search_params['speed_rating']) + str(search_params['rim'])
                formdata['Breite'] = str(search_params['width'])
                formdata['Quer'] = str(search_params['aspect_ratio'])
                formdata['Felge'] = str(search_params['rim'])
                formdata['sowigan'] = ''
                formdata['Speed'] = search_params['speed_rating']
                formdata['dsco'] = '110'
                formdata['kategorie'] = ''
                formdata['Marke'] = ''
                formdata['ranzahl'] = '4'
                formdata['search_tool'] = 'standard'
                formdata['rsmFahrzeugart'] = ''
                formdata['suchen'] = 'Show tyres'
                formdata['F_F'] = '1'
                yield FormRequest('http://www.mytyres.co.uk/cgi-bin/rshop.pl', dont_filter=True, formdata=formdata,
                                  meta={'search': search, 'search_params': search_params}, callback=self.parse)


    def parse(self, response):
        products = response.xpath('//div[@class="results"]')

        pages = response.xpath('//p[contains(text(),"Page")]//a/@href').extract()
        for page in pages:
            yield Request(response.urljoin(page), meta=response.meta)

        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            # the full name of the tyre (name variable) is used to extract metadata (i.e. run flat, xl),
            # the pattern should be set as the product's name
            name = ' '.join(map(unicode.strip, product.select('.//div[@class="resultsLeft"]/div'
                                                              '//text()[normalize-space()]').extract()))
            name += name + ' %s' % ' '.join(map(unicode.strip, product.select('.//div[@class="t_size"]//text()[normalize-space()]').extract()))
            loader.add_xpath('name', './/div[@class="resultsLeft"]/div//a/i/b/text()[normalize-space()]')
            brand = product.select('.//div[@class="resultsLeft"]/div/b//text()[normalize-space()]').extract()[0].strip()

            # skip winter tyres
            if product.select('.//img[contains(@alt,"Winter / cold weather tyres")]'):
                continue
            if product.select('.//img[contains(@alt,"Wi") or contains(@src,"/simg/hiver.png")]'):
                continue
            loader.add_value('brand', unify_brand(brand))
            loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
            fitting_method = 'Fitted'

            url = product.select('.//a[i[b]]/@href')[0].extract()
            url = response.urljoin(url)
            url = re.sub('cart_id=[^&]*', '', url)
            loader.add_value('url', url)

            image_url = product.select('.//a/img[@align="left"]/@src').extract()
            if image_url:
                loader.add_value('image_url', response.urljoin(image_url[0]))

            identifier = urlparse.parse_qs(urlparse.urlparse(url).query)['typ'][0]
            loader.add_value('identifier', identifier)
            price = ''.join(product.select('.//div[@class="price"]/font/b//text()[normalize-space()]').extract())
            price = re.findall(r"\d+.\d+", price) if price else '0.0'
            loader.add_value('price', price)

            data = parse_pattern(name)
            if not data:
                # log.msg("ERROR %s [%s]" % (name, response.url))
                # self.errors.append("Error parsing: %s. URL: %s" % (name, response.url))
                continue

            metadata = MicheldeverMeta()
            metadata['aspect_ratio'] = data['Aspect_Ratio']
            metadata['rim'] = data['Rim']
            metadata['speed_rating'] = data['Speed_Rating']

            metadata['width'] = data['Width']
            metadata['fitting_method'] = fitting_method
            metadata['load_rating'] = data['Load_Rating']
            metadata['alternative_speed_rating'] = ''
            xl = 'XL' in name
            metadata['xl'] = 'Yes' if xl else 'No'

            run_flat_found = is_run_flat(name)
            run_flat = 'run flat' in name.lower() or 'runflat' in name.lower() or run_flat_found
            metadata['run_flat'] = 'Yes' if run_flat else 'No'
            manufacturer_mark = product.select('.//div[@class="t_size"]/b/a[contains(@onmouseover,"Original") or '
                                               'contains(@onmouseover,"BMW") or contains(@onmouseover,"Porsche")]'
                                               '/@name[normalize-space()]').extract()
            manufacturer_mark = manufacturer_mark[0].strip() if manufacturer_mark else []
            metadata['manufacturer_mark'] = find_man_mark(manufacturer_mark) if manufacturer_mark else ''
            metadata['full_tyre_size'] = '/'.join((metadata['width'],
                                                   metadata['aspect_ratio'],
                                                   metadata['rim'],
                                                   metadata['load_rating'],
                                                   metadata['speed_rating']))

            try:
                fuel, grip, noise = map(unicode.strip, product.select('.//div[@class="tyre_label_short"]//text()').extract())
                metadata['fuel'] = fuel
                metadata['grip'] = grip
                metadata['noise'] = noise.replace('dB', '').strip()
            except:
                metadata['fuel'] = ''
                metadata['grip'] = ''
                metadata['noise'] = ''

            product = loader.load_item()
            product['metadata'] = metadata

            if not is_product_correct(product):
                continue

            if product['identifier'] in self.ip_codes:
                ip_code = self.ip_codes[product['identifier']]
                product['sku'] = ip_code
                product['metadata']['mts_stock_code'] = find_mts_stock_code(
                    product, spider_name=self.name, log=self.log,
                    ip_code=ip_code)
                yield product
            else:
                # We can't found IP code on products list, unfortunatelly we must extract it from product page
                yield Request(product['url'], meta={'product': product}, callback=self.parse_ipcode)

    def parse_ipcode(self, response):
        product = response.meta['product']
        ip_code = response.xpath('//div[@id="pdp_tb_info_sku"]/div[2]/text()').extract_first()
        self.ip_codes[product['identifier']] = ip_code or ''
        product['sku'] = ip_code
        product['metadata']['mts_stock_code'] = find_mts_stock_code(
            product, spider_name=self.name, log=self.log,
            ip_code=ip_code)
        yield product

    def match_name(self, search_name, new_item, match_threshold=80, important_words=None):
        r = self.matcher.match_ratio(search_name, new_item, important_words)
        return r >= match_threshold

    # Only if Proxy Service enabled
    def proxy_service_check_response(self, response):
        return response.status == 502

def parse_pattern(pattern):
    """
    Michelin Collection SX MXX 3 N2Michelin Collection SX MXX 3 N2 205/55 R16 ZR WW 20mm *.
    >>> parse_pattern('Michelin Agilis 51Michelin Agilis 51 175/65 R14C 90T') == {'Width': '175', 'Aspect_Ratio': '65', 'Rim': '14', 'Load_Rating': '90', 'Speed_Rating': 'T'}
    True
    """
    data = re.search('(?P<Width>\d+)/(?P<Aspect_Ratio>\d+\.?\d*) .?R(?P<Rim>\d+)[a-z]? (?P<Load_Rating>\d+/?\d*)(?P<Speed_Rating>.)', pattern, re.I)
    if not data:
        return None

    return data.groupdict()

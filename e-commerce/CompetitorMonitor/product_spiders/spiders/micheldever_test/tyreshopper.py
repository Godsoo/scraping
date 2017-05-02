import re
import os
import csv
from urlparse import urljoin

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoader

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, get_speed_rating, get_alt_speed, \
    find_brand_segment, unify_brand


HERE = os.path.abspath(os.path.dirname(__file__))


class TyreShopperSpider(BaseSpider):
    name = 'tyre-shopper.co.uk_test'
    allowed_domains = ('tyre-shopper.co.uk',)

    tyre_sizes = []
    all_man_marks = {}

    def __init__(self, *args, **kwargs):
        super(TyreShopperSpider, self).__init__(*args, **kwargs)

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.tyre_sizes.append(row)

        with open(os.path.join(HERE, 'manmarks.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.all_man_marks[row['code']] = row['manufacturer_mark']

        self.errors = []

    def _get_manufacturer_code(self, name):
        name = name.upper()
        for code, manufacturer_mark in self.all_man_marks.items():
            if code not in name:
                continue

            if code in name.split(' ') or code == '*':
                return manufacturer_mark

        return ''

    def start_requests(self):
        for row in self.tyre_sizes:
            width = row['Width']
            aspect_ratio = row['Aspect Ratio']
            rim = row['Rim']
            load_rating = row['Load rating']
            speed_rating = row['Speed rating']

            yield Request('http://www.tyre-shopper.co.uk/search/%s-%s-r%s/%s/%s' % (width, aspect_ratio, rim,
                                                                                    speed_rating, load_rating),
                          meta={'product_data': row})

            if row['Alt Speed']:
                width = row['Width']
                aspect_ratio = row['Aspect Ratio']
                rim = row['Rim']
                load_rating = row['Load rating']
                speed_rating = row['Alt Speed']

                yield Request('http://www.tyre-shopper.co.uk/search/%s-%s-r%s/%s/%s' % (width, aspect_ratio, rim,
                                                                                        speed_rating, load_rating),
                              meta={'product_data': row})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        products = hxs.select('//div[contains(@class, "searchResult")]//div[contains(@class, "itemCol")]/a/@href').extract()
        for p in products:
            yield Request(urljoin(base_url, p), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        title = hxs.select('//h1/text()')[0].extract()
        if 'winter' in title.lower():
            return

        title = re.search('(.*)-[^-]+', title).groups()[0]
        brand = title.split(' ')[0]
        price = hxs.select('//td[@class="price"]/text()')[0].extract()
        # fix wrong product
        if brand.strip() == 'R27':
            loader.add_value('name', title.replace('XL', '').replace('RF', ''))
            brand = 'Toyo'
        else:
            loader.add_value('name', title.replace(brand, '').replace('XL', '').replace('RF', ''))
        loader.add_value('brand', unify_brand(brand))
        loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))

        loader.add_value('price', price)
        loader.add_value('url', response.url)
        loader.add_xpath('identifier', '//input[@id="product_reference"]/@value')
        image_url = hxs.select('//img[@class="productImg"]/@src')[0].extract()
        loader.add_value('image_url', urljoin(get_base_url(response), image_url))

        speed_rating = hxs.select("//tr[td/strong[text()='Speed:']]/td[2]/text()").extract()[0]
        load_rating = hxs.select("//tr[td/strong[text()='Load:']]/td[2]/text()").extract()[0].replace(speed_rating, "")

        size = hxs.select("//tr[td/strong[text()='Size:']]/td[2]/text()").extract()[0]

        width, aspect_ratio, _, rim = parse_tyre_size(size)
        if not width:
            msg = "Error parsing '%s' on page %s" % (size, response.url)
            self.log(msg)
            self.errors.append(msg)
            return

        m = MicheldeverMeta()
        m['aspect_ratio'] = aspect_ratio
        m['rim'] = rim
        m['width'] = width
        m['speed_rating'] = speed_rating.upper()
        m['load_rating'] = load_rating
        if 'RF' in title.upper():
            m['run_flat'] = 'Yes'
        else:
            m['run_flat'] = 'No'

        if 'XL' in title.upper():
            m['xl'] = 'Yes'
        else:
            m['xl'] = 'No'

        m['full_tyre_size'] = '/'.join((m['width'],
                                        m['aspect_ratio'],
                                        m['rim'],
                                        m['load_rating'],
                                        m['speed_rating']))

        m['fitting_method'] = 'Fitted'
        m['manufacturer_mark'] = self._get_manufacturer_code(title)

        product = loader.load_item()
        product['metadata'] = m

        if not is_product_correct(product):
            return

        product['metadata']['mts_stock_code'] = find_mts_stock_code(product, spider_name=self.name, log=self.log)

        new_speed_rating = get_speed_rating(product)
        new_alt_speed = get_alt_speed(product)
        product['metadata']['alternative_speed_rating'] = new_alt_speed if new_alt_speed else \
            product['metadata']['speed_rating'] if product['metadata']['speed_rating'] != new_speed_rating else ''
        product['metadata']['speed_rating'] = new_speed_rating

        yield product


regex = re.compile("(\d*)/([\d]*)(.[a-zA-Z]?)R(\d*)")
regex2 = re.compile("(\d{1,3})([\d]*)(.[a-zA-Z]?)R(\d*)")

def parse_tyre_size(size):
    """
    >>> parse_tyre_size("225/40WR18")
    ('225', '40', 'W', '18')
    >>> parse_tyre_size("25540WR19")
    ('255', '40', 'W', '19')
    """
    m = regex.search(size)
    if not m:
        m = regex2.search(size)
    if m:
        return m.groups()
    else:
        return None, None, None, None
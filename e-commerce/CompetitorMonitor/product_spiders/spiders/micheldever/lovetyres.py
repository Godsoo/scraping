import re
import os
import csv

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.base_spiders.matcher import Matcher
from product_spiders.items import Product, ProductLoader

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, get_speed_rating, get_alt_speed, \
    find_brand_segment, find_man_mark, unify_brand, is_run_flat

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

HERE = os.path.abspath(os.path.dirname(__file__))


class LoveTyresSpider(BaseSpider):
    name = 'lovetyres.com'
    allowed_domains = ['lovetyres.com']
    start_urls = ['http://www.lovetyres.com']

    images_filename = os.path.join(HERE, 'lovetyres_images.csv')

    def __init__(self, *args, **kwargs):
        super(LoveTyresSpider, self).__init__(*args, **kwargs)

        self.matcher = Matcher(self.log)
        self.images = {}
        self.all_man_marks = {}

        with open(os.path.join(HERE, 'manmarks.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.all_man_marks[row['code']] = row['manufacturer_mark']

        if os.path.exists(self.images_filename):
            with open(self.images_filename) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.images[row['product_url']] = row['image_url']

        self.errors = []

        dispatcher.connect(self.spider_closed, signals.spider_closed)

    def spider_closed(self, spider):
        with open(self.images_filename, 'w') as f:
            writer = csv.DictWriter(f, ['product_url', 'image_url'])
            writer.writeheader()
            for product_url, image_url in self.images.items():
                writer.writerow({'product_url': product_url,
                                 'image_url': image_url})

    def start_requests(self):
        requests = []
        urls = set()
        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                search = str(row['Width']) + '/' + str(row['Aspect Ratio']) + \
                         str(row['Speed rating']) + str(row['Rim'])

                search_url = 'http://www.lovetyres.com/search/tyres/%(Width)s-%(Aspect Ratio)s-%(Rim)s' % row

                if search_url not in urls:
                    self.log(search_url)
                    urls.add(search_url)
                    requests.append(Request(search_url, meta={'search': search}, callback=self.parse))

        self.log('TOTAL SEARCH REQUESTS: %s' % len(requests))

        return requests

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//tr[contains(@class,"tyre-search-row")]')

        next_page = []
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]), meta=response.meta)

        not_found_count = 0

        for product in products:
            url = product.select('.//td/b/a/@href')[0].extract()
            winter_tyre = product.select('.//td/b/a/text()')[0].extract()
            winter_tyre = 'winter' in winter_tyre.lower()
            if not winter_tyre:
                brand = product.select('.//a/img/@src')[0].extract()
                brand = re.search('/public/brands/(.*?)(-tyres)?\.', brand).group(1).replace('-', ' ').title()
                product_name = product.select('.//td/b/a/text()')[0].extract()
                product_name = re.sub(brand, '', product_name).strip()
                fitting_method = 'Delivered'
                identifier = product.select('.//input[@name="item_id"]/@value').extract()
                if not identifier:
                    identifier = product.select('.//a/@href').re('email_me_stock/(.*)')
                if not identifier:
                    continue
                try:
                    fuel, grip, noise = map(unicode.strip,
                        product.select('.//img[contains(@alt, "Tyre Label")]/following-sibling::text()').extract())
                except:
                    fuel = ''
                    grip = ''
                    noise = ''

                price = product.select("td[3]/b/text()").extract()
                loader = ProductLoader(item=Product(), selector=hxs)
                loader.add_value('identifier', identifier[0])
                loader.add_value('name', product_name)
                loader.add_value('brand', unify_brand(brand))
                loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
                loader.add_value('url', url)
                if price:
                    loader.add_value('price', price[0])
                else:
                    loader.add_value('price', '0.00')
                    loader.add_value('stock', 0)

                pattern_name = product.select('.//i/text()').extract()
                if not pattern_name:
                    continue
                pattern_name = pattern_name[0]

                data = re.search('(?P<Width>\d+)/(?P<Aspect_Ratio>\d+) R(?P<Rim>\d+) (?P<Speed_Rating>[A-Za-z]{1,2}) \((?P<Load_Rating>\d+).*?\)',
                              pattern_name)
                if data:
                    data = data.groupdict()
                else:
                    msg = 'ERROR parsing "{}" [{}]'.format(pattern_name, response.url)
                    self.log(msg)
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

                run_flat_found = is_run_flat(pattern_name)
                run_flat = 'run flat' in pattern_name.lower() or 'runflat' in pattern_name.lower() or run_flat_found
                metadata['run_flat'] = 'Yes' if run_flat else 'No'
                manufacturer_mark = [mark for mark in self.all_man_marks.keys() if mark in pattern_name.split(' ')]
                manufacturer_mark = manufacturer_mark[0].strip() if manufacturer_mark else []
                metadata['manufacturer_mark'] = find_man_mark(manufacturer_mark) if manufacturer_mark else ''

                metadata['full_tyre_size'] = '/'.join((metadata['width'],
                                                       metadata['aspect_ratio'],
                                                       metadata['rim'],
                                                       metadata['load_rating'],
                                                       metadata['speed_rating']))

                metadata['fuel'] = fuel
                metadata['grip'] = grip
                metadata['noise'] = noise

                product = loader.load_item()
                product['metadata'] = metadata

                if not is_product_correct(product):
                    not_found_count += 1
                    self.log('%s - PRODUCT IS NOT CORRECT: %r' % (not_found_count, product))
                    continue

                product['metadata']['mts_stock_code'] = find_mts_stock_code(product, spider_name=self.name, log=self.log)

                if product['url'] in self.images:
                    product['image_url'] = self.images[product['url']]
                    yield product
                else:
                    yield Request(product['url'], callback=self.parse_image, meta={'product': product}, dont_filter=True)

    def parse_image(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=response.meta['product'], selector=response)
        image_url = hxs.select('//div[@class="item"]/a/img/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

        product = loader.load_item()
        if 'image_url' in product and product['image_url'].strip():
            self.images[product['url']] = product['image_url']

        yield product

    def match_name(self, search_name, new_item, match_threshold=80, important_words=None):
        r = self.matcher.match_ratio(search_name, new_item, important_words)
        return r >= match_threshold

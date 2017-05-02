import re
import os
import csv
from urlparse import urljoin

try:
    from scrapy.spiders import Spider as BaseSpider
except ImportError:
    from scrapy.spider import BaseSpider

from scrapy.http import Request
from scrapy.utils.response import get_base_url

from product_spiders.base_spiders.matcher import Matcher
from product_spiders.items import Product, ProductLoader

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, get_speed_rating, get_alt_speed, \
    find_brand_segment, find_man_mark, unify_brand, is_run_flat


HERE = os.path.abspath(os.path.dirname(__file__))


class KwikFitSpider(BaseSpider):
    name = 'kwik-fit.com'
    allowed_domains = ['kwik-fit.com']
    start_urls = ('http://www.kwik-fit.com',)
    tyre_sizes = []

    download_delay = 0.1

    def __init__(self, *args, **kwargs):
        super(KwikFitSpider, self).__init__(*args, **kwargs)
        self.matcher = Matcher(self.log)

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.tyre_sizes.append(row)

    def start_requests(self):
        for row in self.tyre_sizes:
            search = row['Width'] + '/' + row['Aspect Ratio'] + row['Speed rating'] + row['Rim']
            yield Request('https://www.kwik-fit.com/tyres/search/results/%(Width)s/%(Aspect Ratio)s/%(Rim)s/%(Speed rating)s' % row,
                          dont_filter=True,
                          meta={'row':row, 'search':search},
                          callback=self.parse)

            if row['Alt Speed']:
                search = row['Width'] + '/' + row['Aspect Ratio'] + row['Alt Speed'] + row['Rim']
                yield Request('https://www.kwik-fit.com/tyres/search/results/%(Width)s/%(Aspect Ratio)s/%(Rim)s/%(Alt Speed)s' % row,
                                  dont_filter=True,
                                  meta={'row':row, 'search':search},
                                  callback=self.parse)

    def parse(self, response):
        products = response.xpath('//div[contains(@class, "tyres_search_results_tyre") and @data-viewtype="grid"]')

        for product in products:
            winter_tyre = product.xpath('@data-filter-season').extract()[0] == 'Winter'
            if not winter_tyre:
                name = product.xpath('.//div[contains(@class, "tyre-model text-center")]/text()').extract()[0]
                brand = product.xpath('@data-filter-brand').extract()[0]

                loader = ProductLoader(item=Product(), selector=product)
                loader.add_value('name', brand + ' ' + name)
                loader.add_value('brand', unify_brand(brand))
                loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
                identifier = product.xpath('@data-tyreid').extract()[0]
                loader.add_value('identifier', identifier)
                loader.add_value('url', response.url)
                image_url = product.xpath('.//div[contains(@class, "tyre-image")]//img/@src').extract()
                if image_url:
                    loader.add_value('image_url', urljoin(get_base_url(response), image_url[0]))
                price = product.xpath('.//div[contains(@class, "tyre-pricing-information")]/div/text()').re(r'[\d,.]+')
                price = price[0] if price else '0.00'
                loader.add_value('price', price)
                tyresize_text = product.xpath('.//div[contains(@class, "tyre-size")]/text()').extract()[0].strip()
                try:
                    width, aspect, speed_rating, rim, load_rating = re.search(r'(\d+)\/(\d+)(\w{1})(\d+)\s\((\d+)\)', tyresize_text, re.I).groups()
                except:
                    width, aspect, speed_rating, rim = re.search(r'(\d+)\/(\d+)(\w{1})(\d+)', tyresize_text, re.I).groups()
                    load_rating = ''

                fitting_method = 'Fitted'

                metadata = MicheldeverMeta()
                metadata['aspect_ratio'] = aspect
                metadata['rim'] = rim

                metadata['speed_rating'] = speed_rating

                metadata['width'] = width
                metadata['fitting_method'] = fitting_method
                metadata['load_rating'] = load_rating
                metadata['alternative_speed_rating'] = ''
                xl = product.xpath('@data-filter-reinforced').extract()[0] == 'Y'
                metadata['xl'] = 'Yes' if xl else 'No'

                run_flat_found = is_run_flat(loader.get_output_value('name'))
                run_flat = product.xpath('@data-filter-runflat').extract()[0] == 'Y'
                metadata['run_flat'] = 'Yes' if run_flat or run_flat_found else 'No'
                manufacturer_mark = product.xpath('.//span[contains(@title, "Homologated for fitment to certai")]/@title')\
                                           .re(r'Homologated for fitment to certain (.*) cars\.')

                metadata['manufacturer_mark'] = find_man_mark(manufacturer_mark[0]) if manufacturer_mark else ''

                metadata['full_tyre_size'] = '/'.join((metadata['width'],
                                                       metadata['aspect_ratio'],
                                                       metadata['rim'],
                                                       metadata['load_rating'],
                                                       metadata['speed_rating']))

                fuel, grip, noise = product.xpath('@data-filter-tyreefficiencyr'
                                                  '|@data-filter-tyreefficiencyg'
                                                  '|@data-filter-tyreefficiencyd')\
                                           .extract()
                metadata['fuel'] = fuel
                metadata['grip'] = grip
                metadata['noise'] = noise

                product = loader.load_item()
                product['metadata'] = metadata

                if not is_product_correct(product):
                    continue

                product['metadata']['mts_stock_code'] = find_mts_stock_code(product, spider_name=self.name, log=self.log)

                yield product

    def match_name(self, search_name, new_item, match_threshold=80, important_words=None):
        r = self.matcher.match_ratio(search_name, new_item, important_words)
        return r >= match_threshold

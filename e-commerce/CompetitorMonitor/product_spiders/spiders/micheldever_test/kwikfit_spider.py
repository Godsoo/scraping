import re
import os
import csv
from urlparse import urljoin

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import FormRequest
from scrapy.utils.response import get_base_url

from product_spiders.base_spiders.matcher import Matcher
from product_spiders.items import Product, ProductLoader

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, get_speed_rating, get_alt_speed, \
    find_brand_segment, find_man_mark, unify_brand


HERE = os.path.abspath(os.path.dirname(__file__))


class KwikFitSpider(BaseSpider):
    name = 'kwik-fit.com_test'
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
            formdata = {}
            search = row['Width']+'/'+row['Aspect Ratio']+row['Speed rating']+row['Rim']
            formdata['dts'] = search
            formdata['sop'] = 'TyreSize'
            formdata['ssq'] = '3'
            formdata['tsf'] = search
            formdata['tsr'] = search
            formdata['MobileQuote'] = 'false'
            formdata['ShowSummerTyres'] = 'true'
            formdata['ShowTyresForBookOnline'] = 'true'
            formdata['ShowTyresForQuotation'] = 'true'
            formdata['ShowWinterTyres'] = 'true'
            formdata['Stage'] = '2'
            yield FormRequest('http://www.kwik-fit.com/tyre-search.asp', dont_filter=True, formdata=formdata, meta={'row':row, 'search':search}, callback=self.parse)

            if row['Alt Speed']:
                formdata = {}
                search = row['Width']+'/'+row['Aspect Ratio']+row['Alt Speed']+row['Rim']
                formdata['dts'] = search
                formdata['sop'] = 'TyreSize'
                formdata['ssq'] = '3'
                formdata['tsf'] = search
                formdata['tsr'] = search
                formdata['MobileQuote'] = 'false'
                formdata['ShowSummerTyres'] = 'true'
                formdata['ShowTyresForBookOnline'] = 'true'
                formdata['ShowTyresForQuotation'] = 'true'
                formdata['ShowWinterTyres'] = 'true'
                formdata['Stage'] = '2'
                yield FormRequest('http://www.kwik-fit.com/tyre-search.asp', dont_filter=True, formdata=formdata, meta={'row':row, 'search':search}, callback=self.parse)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
  
        products = hxs.select('//div[contains(@id,"Tyre") and contains(@class, "tyre-list-tyre")]')

        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_xpath('name', 'div//div[@class="manufacturerText"]/p/strong/text()')
            brand = ''.join(product.select('div//div[@class="manufacturerImage"]/img/@alt').extract()).split(' - ')[0]
            winter_tyre = product.select('div//img[@alt="Winter Tyre"]')
            if not winter_tyre:
                loader.add_value('brand', unify_brand(brand))
                loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
                identifier = product.select('div//div[@class="pricingAddToOrder clearfix"]/input/@value').extract()[0]
 
                loader.add_value('url', '')

                image_url = product.select('div[@class="image"]/img/@src').extract()
                if image_url:
                    loader.add_value('image_url', urljoin(get_base_url(response), image_url[0]))

                loader.add_value('identifier', identifier)
                price = product.select('div//div[contains(@class, "pricingSelection")]//a/strong/text()').extract()
                price = re.findall(r"\d+.\d+", price[0]) if price else '0.0'
                loader.add_value('price', price)

                tyresize_text = product.select('.//div[contains(@class, "manufacturerText")]/p/span/text()').extract()[0].strip()
                width, aspect, speed_rating, rim = re.search(r'tyre size (\d+)\/(\d+)(\w{1})(\d+)', tyresize_text, re.I).groups()

                fitting_method = 'Fitted'

                metadata = MicheldeverMeta()
                metadata['aspect_ratio'] = aspect
                metadata['rim'] = rim

                metadata['speed_rating'] = speed_rating

                metadata['width'] = width
                metadata['fitting_method'] = fitting_method
                load_rating = product.select('div//li/a[@rel="load-index-description"]/text()').extract()
                metadata['load_rating'] = load_rating[0].split(': ')[-1] if load_rating else ''
                metadata['alternative_speed_rating'] = ''
                xl = product.select('div//img[@title="Reinforced"]/@title').extract()
                metadata['xl'] = 'Yes' if xl else 'No'

                run_flat = product.select('div//img[@title="Run Flat"]').extract()
                metadata['run_flat'] = 'Yes' if run_flat else 'No'
                manufacturer_mark = product.select('div//img[contains(@title, "Homologated for fitment to certai")]/@title').extract()
                manufacturer_mark = manufacturer_mark[0].replace('Homologated for fitment to certain ' ,'').replace(' cars.' ,'') if manufacturer_mark else ''
 
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

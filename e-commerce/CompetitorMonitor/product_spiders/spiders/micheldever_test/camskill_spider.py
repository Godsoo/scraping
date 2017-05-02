import os
from urlparse import urljoin
import csv
import shutil
import json
from time import sleep
from subprocess import call
import random

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy import log
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.utils.url import urljoin_rfc


from product_spiders.items import Product, ProductLoader
from product_spiders.phantomjs import get_page

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, get_speed_rating, get_alt_speed, \
    find_brand_segment, find_man_mark, unify_brand


HERE = os.path.abspath(os.path.dirname(__file__))

PROXIES = ['38.130.175.110:65432', '38.130.175.140:65432', '38.130.174.175:65432', '38.130.173.190:65432',
           '38.130.172.205:65432', '149.71.195.115:65432', '149.71.194.120:65432',
           '154.51.143.85:65432', '154.51.141.65:65432', '149.71.195.84:65432', '38.130.171.197:65432',
           '149.71.192.155:65432']

class CamSkillSpider(BaseSpider):
    name = 'micheldever-camskill.co.uk_test'
    allowed_domains = ['camskill.co.uk', 'translate.google.com', 'google.com']
    start_urls = ('http://google.com',)
    tyre_sizes = []
    all_man_marks = {}
    manually_matched = []
    rotate_agent = True
    download_delay = 10
    translate_url = 'https://translate.google.com/translate?sl=es&tl=en&js=y&prev=_t&hl=es-419&ie=UTF-8&u=%s&edit-text=&act=url'
    '''
    def restart_tor(self):
        self.log('Restarting tor')
        call(['/home/innodev/product-spiders/product_spiders/scripts/torinstances/torinstances.sh',
              'restart', 'camskill'])
        sleep(30)
    '''


    def __init__(self, *argv, **kwgs):
        super(CamSkillSpider, self).__init__(*argv, **kwgs)
        self.products_data = {}
        self.products_metadata = {}
        self.incorrect_identifiers = []
        self.req_count = 0
        fname = os.path.join(HERE, 'camskill.csv')
        if os.path.exists(fname):
            with open(fname) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.products_data[row['identifier']] = row

        fname_meta = os.path.join(HERE, 'camskill_meta.json')
        if os.path.exists(fname_meta):
            with open(fname_meta) as f:
                data = json.load(f)
                for row in data:
                    self.products_metadata[row['identifier']] = row['metadata']

        fname_ids = os.path.join(HERE, 'camskill_incorrect.csv')
        if os.path.exists(fname_ids):
            with open(fname_ids) as f:
                reader = csv.reader(f)
                for row in reader:
                    self.incorrect_identifiers.append(row[0])

    def parse(self, response):
        for ident in self.products_data:
            row = self.products_data[ident]
            url = self.translate_url % row['url']
            self.log('Product url: %s' % url)
            try:
                html = get_page(url, proxy=random.choice(PROXIES))

                hxs = HtmlXPathSelector(text=html)
                out_of_stock = 'NO STOCK' in ''.join(hxs.select('//p[@class="prodmain"]//text()').extract()).upper()

                price = ''.join(hxs.select('//td[span/span/span/text()="PRICE:"]/span/text()').extract()).strip()
                if not price:
                    price = ''.join(hxs.select('//td//p[span/text()="PRICE:"]/span/text()').extract()).strip()
            except Exception:
                self.log('URL raised exception: %s' % url)
                price = row['price']
                out_of_stock = False
                hxs = HtmlXPathSelector()

            if price:
                yield self.parse_product_cache(ident, price, out_of_stock, hxs)

            sleep(10)

    '''
    def spider_closed(self, spider):
        if spider.name == self.name:
            shutil.copy('data/%s_products.csv' % spider.crawl_id, os.path.join(HERE, 'camskill.csv'))
            #shutil.copy('data/meta/%s_meta.json' % spider.crawl_id, os.path.join(HERE, 'camskill_meta.json'))
            with open(os.path.join(HERE, 'camskill_incorrect.csv'), 'w') as f:
                writer = csv.writer(f)
                for i in self.incorrect_identifiers:
                    writer.writerow([str(i)])

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//div[@class="categoryGroupWrapper" and h5/strong/a/text()!="Car Winter Tyres" and h5/strong/a[contains(text(), "Tyre")]]/div/div/div[@class="categoryGroupContent"]/a/@href').extract()

        for category in categories:
            url = urljoin(get_base_url(response), category)
            yield Request(url, meta={'cookiejar': str(self.req_count / 50)})
            self.req_count += 1

        sub_categories = hxs.select('//div[@class="subCategoryEntry"]/a/@href').extract()
        for sub_cateogry in sub_categories:
            url = urljoin(get_base_url(response), sub_cateogry)
            yield Request(url, meta={'cookiejar': str(self.req_count / 50)})
            self.req_count += 1

        products = hxs.select('//div/table/tr[td[form/input[@name="productID"]]]')
        for product in products:
            url = product.select('./td/p/a[not(contains(@href, "order"))]/@href').extract()[0]
            url = urljoin_rfc(get_base_url(response), url)
            winter_tyre = 'WINTER' in url.upper()
            if winter_tyre:
                continue

            identifier = product.select('./td/form/input[@name="productID"]/@value').extract()[0]
            if identifier in self.incorrect_identifiers:
                continue

            price = product.select('./td/form/input[@name="productPrice"]/@value').extract()[0]
            if identifier in self.products_data and identifier in self.products_metadata:
                yield self.parse_product_cache(identifier, price, product)
            else:
                yield Request(url, callback=self.parse_product, meta={'cookiejar': str(self.req_count / 50)})
                self.req_count += 1


    def parse_product(self, hxs, url, image_url):

        loader = ProductLoader(item=Product(), selector=hxs)
        name = ''.join(hxs.select('//tr[td/span/span/text()="Model"]/td[@class="pcv"]/span/text()').extract())
        if not name:
            log.msg('NO NAME FOUND')
            return
        loader.add_xpath('name', '//tr[td/span/span/text()="Model"]/td[@class="pcv"]/span/text()')
        brand = hxs.select('//tr[td/span/span/text()="Brand"]/td[@class="pcv"]/span/text()').extract()
        brand = brand[0] if brand else ''

        loader.add_value('brand', unify_brand(brand))
        loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
        loader.add_value('url', url)
        fitting_method = 'Delivered'

        #image_url = hxs.select('//a[@rel="lightbox"]/img/@src').extract()
        #image_url = image_url[0] if image_url else ''

        if image_url:
            loader.add_value('image_url', image_url)

        out_of_stock = 'NO STOCK' in ''.join(hxs.select('//p[@class="prodmain"]/span/text()').extract()).upper()
        if out_of_stock:
            loader.add_value('stock', 0)

        loader.add_xpath('identifier', '//input[@name="productID"]/@value')
        price = ''.join(hxs.select('//td[span/text()="PRICE:"]/text()').extract()).strip()
        if not price:
            price = ''.join(hxs.select('//td/p[span/text()="PRICE:"]/text()').extract()).strip()
        loader.add_value('price', price)

        metadata = MicheldeverMeta()
        aspect_ratio = hxs.select('//tr[td/text()="Profile"]/td[@class="pcv"]/text()').extract()
        metadata['aspect_ratio'] = aspect_ratio[0] if aspect_ratio else ''
        rim = hxs.select('//tr[td/text()="Rim"]/td[@class="pcv"]/text()').extract()
        metadata['rim'] = rim[0] if rim else ''
        speed_rating = hxs.select('//tr[td/text()="Speed"]/td[@class="pcv"]/text()').extract()
        metadata['speed_rating'] = speed_rating[0] if speed_rating else ''
        width = hxs.select('//tr[td/text()="Width"]/td[@class="pcv"]/text()').extract()
        metadata['width'] = width[0] if width else ''
             
        metadata['fitting_method'] = fitting_method
        load_rating = hxs.select('//tr[td/text()="Load"]/td[@class="pcv"]/text()').extract()
        metadata['load_rating'] = load_rating[0] if load_rating else ''
        metadata['alternative_speed_rating'] = ''
        xl = hxs.select('//tr[td/text()="Ply"]/td[@class="pcv"]/text()').extract()
        metadata['xl'] = 'Yes' if xl else 'No'
        run_flat = hxs.select('//tr[td/text()="Runflat"]/td[@class="pcv"]/text()').extract()
        metadata['run_flat'] = 'Yes' if run_flat else 'No'

        man_code = hxs.select('//tr[td/text()="OE Code"]/td[@class="pcv"]/text()').extract()

        if man_code:
            self.log("Manufacturer mark for %s: %s" % (loader.get_output_value('identifier'), man_code[0]))
        metadata['manufacturer_mark'] = find_man_mark(man_code[0]) if man_code and man_code[0] else ''
        metadata['full_tyre_size'] = '/'.join((metadata['width'],
                                               metadata['aspect_ratio'], 
                                               metadata['rim'], 
                                               metadata['load_rating'], 
                                               metadata['speed_rating']))
        product = loader.load_item()
        product['metadata'] = metadata

        if not is_product_correct(product):
            self.incorrect_identifiers.append(product['identifier'])
            return

        product['metadata']['mts_stock_code'] = find_mts_stock_code(product, spider_name=self.name, log=self.log)

        new_speed_rating = get_speed_rating(product)
        new_alt_speed = get_alt_speed(product)
        product['metadata']['alternative_speed_rating'] = new_alt_speed if new_alt_speed else \
            product['metadata']['speed_rating'] if product['metadata']['speed_rating'] != new_speed_rating else ''
        product['metadata']['speed_rating'] = new_speed_rating

        return product

    '''

    def parse_product_cache(self, identifier, price, out_of_stock, product):
        """
        >>> spider = CamSkillSpider()
        >>> product = {\
                "brand": "Pirelli", \
                "category": 'R16" -  205/55/16, 205/55R16', \
                "identifier": "113764", \
                "image_url": "http://www.camskill.co.uk/smsimg/1943/113764--main--1943.jpg", \
                "metadata": {\
                    "alternative_speed_rating": "", \
                    "aspect_ratio": "55", \
                    "fitting_method": "Delivered", \
                    "full_tyre_size": "205/55/16/91/V", \
                    "load_rating": "91", \
                    "manufacturer_mark": "", \
                    "mts_stock_code": "2055516VPIP7", \
                    "rim": "16", \
                    "run_flat": "No", \
                    "speed_rating": "V", \
                    "width": "205", \
                    "xl": "No"\
                }, \
                "name": "Cinturato P7", \
                "price": "64.40", \
                "sku": None, \
                "stock": "0", \
                "url": "http://www.camskill.co.uk/m62b0s291p113764/Pirelli_Tyres_Car_Pirelli_P7_Cinturato_Pirelli_P_7_-_205_55_R16_91V_TL_Fuel_Eff_%3A_E_Wet_Grip%3A_A_NoiseClass%3A_2_Noise%3A_70dB"\
            }
        >>> spider.products_data['113764'] = product
        >>> product_ = spider.parse_product_cache("113764", 123, product)
        >>> product_['metadata']['mts_stock_code']
        '2055516VPIP7CINT'
        """
        loader = ProductLoader(item=Product(), selector=product)
        for col in ['name', 'identifier', 'sku', 'url', 'image_url', 'brand']:
            loader.add_value(col, self.products_data[identifier][col])

        loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))

        loader.add_value('price', price)
        if out_of_stock:
            loader.add_value('stock', 0)

        product_ = loader.load_item()
        if identifier in self.products_metadata:
            product_['metadata'] = self.products_metadata[identifier]

            if not is_product_correct(product_):
                self.incorrect_identifiers.append(product['identifier'])
                return

            product_['metadata']['mts_stock_code'] = find_mts_stock_code(product_, spider_name=self.name, log=self.log)

            new_speed_rating = get_speed_rating(product_)
            new_alt_speed = get_alt_speed(product_)
            product_['metadata']['alternative_speed_rating'] = new_alt_speed if new_alt_speed else \
                product_['metadata']['speed_rating'] if product_['metadata']['speed_rating'] != new_speed_rating else ''
            product_['metadata']['speed_rating'] = new_speed_rating

        return product_


if __name__ == "__main__":
    import doctest
    doctest.testmod()

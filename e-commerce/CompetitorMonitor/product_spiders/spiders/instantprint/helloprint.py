import csv
import os
import itertools
from scrapy import Spider, Request
from product_spiders.items import Product, ProductLoader
from hashlib import md5
from decimal import Decimal

from product_spiders.config import DATA_DIR


QTY_VALUES = [
    1, 2, 3, 4, 5, 10, 15, 25, 50, 100, 150,
    200, 250, 300, 400, 500, 600, 700, 750, 800,
    900, 1000, 1250, 1500, 1750, 2000, 2250, 2500,
    2750, 3000, 3500, 4000, 4500, 5000, 10000, 15000,
    20000, 25000, 30000, 40000, 50000]



class HelloPrintSpider(Spider):
    name = 'instantprint-helloprint.co.uk'
    allowed_domains = ['helloprint.co.uk']
    start_urls = ['https://www.helloprint.co.uk/']
    product_names = []
    single_sided = ['Full colour on 1 side', 'Single sided printing', 'On 1 side', 'On 1 side full colour', 'On one side']
    double_sided = ['Full colour on 2 sides', 'Double sided printing', 'On 2 sides', 'On 2 sides full colour', 'Double-sided']

    def __init__(self, *k, **kw):
        super(HelloPrintSpider, self).__init__(*k, **kw)
        self.single_sided_rep = itertools.product(*([self.single_sided] * 2))
        self.single_sided_rep = [rep for rep in self.single_sided_rep if rep[0] != rep[1]]
        self.double_sided_rep = itertools.product(*([self.double_sided] * 2))
        self.double_sided_rep = [rep for rep in self.double_sided_rep if rep[0] != rep[1]]

    def start_requests(self):
        if hasattr(self, 'prev_crawl_id'):
            with open(os.path.join(DATA_DIR, '{}_products.csv'.format(self.prev_crawl_id))) as f:
                self.product_names = {' - '.join(row['name'].split(' - ')[:-1]) for row in csv.DictReader(f)}
        for url in self.start_urls:
            yield Request(url)

    def get_standard_name(self, product_name):
        if any([s in product_name for s in self.single_sided]):
            for tr in self.single_sided_rep:
                if product_name.replace(tr[0], tr[1]) in self.product_names:
                    self.log('Replaced {}=>{}'.format(tr[0], tr[1]))
                    return product_name.replace(tr[0], tr[1])
        else:
            for tr in self.double_sided_rep:
                rep = product_name.replace(tr[0], tr[1])
                if rep in self.product_names:
                    self.log('Replaced {}=>{}'.format(tr[0], tr[1]))
                    return rep
        rep = product_name.replace('Wide Roller Banners', 'Roll-up Banners')
        if rep in self.product_names:
            return rep
        rep = product_name.replace('Roll-up Banners', 'Wide Roller Banners')
        if rep in self.product_names:
            return rep
        return product_name


    def get_standard_size(self, response):
        if 'helloprint.co.uk/xbanners' in response.url:
            return '60x160cm'
        elif 'helloprint.co.uk/businesscards' in response.url:
            return '85x55mm'
        return None

    def get_lamination(self, options):
        options_str = ' '.join(options).lower()
        if 'matt laminated' in options_str:
            return 'Matt Lamination'
        elif 'velvet laminated' in options_str:
            return 'Velvet Lamination'
        elif 'high gloss' in options_str:
            return 'Gloss Lamination'
        elif 'unlaminated' in options_str:
            return 'No Lamination'
        return None

    def parse(self, response):
        products = [
            ('Fence banners', 'https://www.helloprint.co.uk/fencebanners'),
            ('L-Banners', 'https://www.helloprint.co.uk/lbanners'),
            ('Roll-up Banners', 'https://www.helloprint.co.uk/rollupbanners'),
            ('Wide Roller Banners', 'https://www.helloprint.co.uk/rollupbanners-150x205-210mu-footdeluxe-1'),
            ('X-Banners', 'https://www.helloprint.co.uk/xbanners'),
            ('Flyers', 'https://www.helloprint.co.uk/flyers'),
            ('Business Cards', 'https://www.helloprint.co.uk/businesscards'),
            ('Appointment Cards', 'https://www.helloprint.co.uk/appointmentcards'),
            ('Birth Announcement Cards', 'https://www.helloprint.co.uk/birthannouncementcards'),
            ('Change of Address Cards', 'https://www.helloprint.co.uk/changeofaddresscards'),
            ('Compliment Cards', 'https://www.helloprint.co.uk/complimentcards'),
            ('Greeting Cards', 'https://www.helloprint.co.uk/greetingcards'),
            ('Invitations', 'https://www.helloprint.co.uk/invitations'),
            ('Postcards', 'https://www.helloprint.co.uk/postcards'),
            ('Wedding Invitations', 'https://www.helloprint.co.uk/weddinginvitations'),
            ('Leaflets', 'https://www.helloprint.co.uk/leaflets'),
            ('Folded Leaflets', 'https://www.helloprint.co.uk/foldedleaflets'),
            ('Advertising Poster', 'https://www.helloprint.co.uk/advertisingposter'),
            ('Posters', 'https://www.helloprint.co.uk/posters'),
            ('Booklets', 'https://www.helloprint.co.uk/booklets'),
            ('Letterheads', 'https://www.helloprint.co.uk/letterheads'),
            ('Compliment Slips', 'https://www.helloprint.co.uk/complimentslips'),
            ('Stickers Digital', 'https://www.helloprint.co.uk/stickersdigital'),
            ('Stickers', 'https://www.helloprint.co.uk/stickers'),
            ('Labels', 'https://www.helloprint.co.uk/labels'),
            ('Labels on Roll', 'https://www.helloprint.co.uk/labelsonroll'),
        ]
        for prod_name, prod_url in products:
            yield Request(prod_url,
                          meta={'product_name': prod_name},
                          callback=self.parse_product)

    def parse_product(self, response):
        option_urls = filter(lambda l: l != '#',
            response.xpath('//div[contains(@class, "funnel-wrapper")]/div[@id and @id!="printrun"]'
                           '//a[@id]/@href').extract())
        for url in option_urls:
            yield Request(response.urljoin(url),
                          meta=response.meta,
                          callback=self.parse_product)

        prices_found = response.xpath('//div[contains(@class, "funnel-wrapper")]'
            '/div[@id]//a[@id]/span[@class="price"]/text()').re(r'[\d\.,]+')
        if prices_found:
            main_name = response.meta['product_name']
            options_selected_label = response.xpath('//h3[contains(text(), "Product Summary")]'
                '/following-sibling::div/span[@class="active"]/preceding-sibling::h4/text()').extract()
            options_selected = response.xpath('//h3[contains(text(), "Product Summary")]'
                '/following-sibling::div/span[@class="active"]/text()').extract()
            product_name = main_name + ' - ' + ' - '.join(options_selected)
            if product_name not in self.product_names:
                product_name = self.get_standard_name(product_name)
            image_url = response.xpath('//div[@class="main-image left"]/img/@src').extract()
            quantity = response.xpath('//div[contains(@class, "funnel-wrapper")]'
                '/div[@id]//a[@id and span[@class="price"]]/text()').re(r'[\d\.,]+')
            for i, qty in enumerate(quantity):
                qty = qty.replace('.', '').replace(',', '')
                if int(qty) not in QTY_VALUES:
                    continue
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('name', product_name + ' - ' + qty)
                loader.add_value('identifier', md5(product_name + ' - ' + qty).hexdigest())
                loader.add_value('price', prices_found[i])
                loader.add_value('url', response.url)
                loader.add_value('category', main_name)
                if image_url:
                    loader.add_value('image_url', response.urljoin(image_url[0]))
                item = loader.load_item()
                if item['price'] and 'laminat' in item['name'].lower():
                    item['price'] = (item['price'] * Decimal('1.2')).quantize(Decimal('0.01'))
                metadata = {'ProdQty': qty}
                standard_size = self.get_standard_size(response)
                if standard_size:
                    metadata['PaperSize'] = standard_size

                paper_type_label = 'paper type'
                if paper_type_label not in map(unicode.lower, options_selected_label):
                    paper_type_label = 'material'
                lamination = self.get_lamination(options_selected)
                if lamination:
                    metadata['LaminationType'] = lamination
                for label, value in zip(options_selected_label, options_selected):
                    if label.lower() == 'size':
                        metadata['PaperSize'] = value
                    elif label.lower() == paper_type_label:
                        metadata['PaperType'] = value
                    elif label.lower() == 'pages':
                        metadata['PrintPageNumber'] = value

                item['metadata'] = metadata
                yield item

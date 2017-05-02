import csv
import os
import json

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from product_spiders.base_spiders.primary_spider import PrimarySpider

from harveysmeta import set_product_type


HERE = os.path.dirname(os.path.abspath(__file__))


class HarveysFurnitureSpider(PrimarySpider):
    name = 'harveysfurniture.co.uk'
    allowed_domains = ['ist-apps.com', 'harveysfurniture.co.uk']
    start_urls = ['http://www.harveysfurniture.co.uk/']

    csv_file = 'harveysfurniture.co.uk_products.csv'

    def __init__(self, *args, **kwargs):
        super(HarveysFurnitureSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

        self.old_data = {}
        self.products_collected = []
        self.images_collected = {}
        self.finished = False

        with open(os.path.join(HERE, 'harveysfurniture_data.csv')) as f:
            reader = csv.DictReader(f)

            for row in reader:
                self.old_data[row['url']] = {'category': row['category'].split(' > '),
                                             'brand': row['brand'],
                                             'sku': row['sku']}

    def start_requests(self):
        fabric = 'http://www.harveysfurniture.co.uk/sofas/shop-by/sortby/-relevance/view_size/all/view_mode/3_wide/normalised_fabric/eagle-jennifer_floral-caymen-cord_nevada-jennifer-fifth_ave_plain-bear-beijing-jumbo_snake_wave-jumbo_snake-jumbo_snake_geo_wave-hong_kong-aosta-polla-belize-hellas-highland-livorno/type/%s/'
        leather = 'http://www.harveysfurniture.co.uk/sofas/shop-by/sortby/-relevance/view_size/all/view_mode/3_wide/normalised_fabric/cat_15_llm-lls-cat_20_llm-cat_10_llm-punch_leather-cat_30_lls-cat_35_california-cat_55_new_club-new_club_llm-cat_10_lls-cat_55_seattle-bv_llm/type/%s/'
        dining = 'http://www.harveysfurniture.co.uk/dining/shop-by/type/%s/view_size/all'
        living = 'http://www.harveysfurniture.co.uk/living-room/shop-by/type/%s/view_size/all'
        self.cats = [
            (fabric %'corner_sofas', 'Sofa,Fabric,Corner sofas'),
            (leather %'corner_sofas', 'Sofa,Leather,Corner sofas'),
            (leather %'2_seaters', 'Sofa,Leather,2 seater'),
            (fabric %'2_seaters', 'Sofa,Fabric,2 seater'),
            (leather %'3_seaters', 'Sofa,Leather,3 seater'),
            (fabric %'3_seaters', 'Sofa,Fabric,3 seater'),
            (leather %'4_seaters', 'Sofa,Leather,4 seater'),
            (fabric %'4_seaters', 'Sofa,Fabric,4 seater'),
            (leather %'armchairs', 'Sofa,Leather,armchair'),
            (fabric %'armchairs', 'Sofa,Fabric,armchair'),
            (leather %'footstools', 'Sofa,Leather,Footstools'),
            (fabric %'footstools', 'Sofa,Fabric,Footstools'),
            (leather %'sofabeds', 'Sofa,Leather,Sofa Beds'),
            (fabric %'sofabeds', 'Sofa,Fabric,Sofa Beds'),
            (dining %'dining_chairs', 'Dining,Dining Chairs'),
            ('http://www.harveysfurniture.co.uk/dining/shop-by/type/dining_tables/', 'Dining,Dining Tables'),
            (dining %'display_units', 'Cabinets,Display Units'),
            (dining %'sideboards', 'Cabinets,Sideboards'),
            (living %'coffee_tables', 'Living,Coffee Tables'),
            (living %'entertainment_units', 'Cabinets,Entertainment Units'),
            (living %'care_kits', 'Sofa,Care Kits'),
            (living %'console_tables', 'Cabinets,Console Tables'),
            (living %'lamp_tables', 'Living,Lamp Tables'),
            (living %'nest_of_tables', 'Living,Nest of Tables'),
            (living %'mirrors', 'Accessories,Mirrors'),
            (living %'rugs', 'Accessories,Rugs'),
        ]

        self.category_products = {}
        self.parse_all = True

        for url, category in self.cats:
            yield Request(url, callback=self.parse_category_products, meta={'category': category})

    def parse_category_products(self, response):
        hxs = HtmlXPathSelector(response)
        self.category_products[response.meta['category']] = \
            hxs.select('//div[contains(@class, "list-product")]/a[contains(@class, "link")]/@href').extract()

    def spider_idle(self, spider):
        if self.parse_all:
            self.parse_all = False
            req = Request('http://www.harveysfurniture.co.uk/', dont_filter=True)
            self._crawler.engine.crawl(req, self)
        elif not self.finished:
            self._crawler.engine.crawl(Request(self.start_urls[0], dont_filter=True, callback=self.collect_products), self)

    def collect_products(self, response):
        for product in self.products_collected:
            product_item = Product(product)
            main_id = product_item['identifier'].split(':')[0]
            if main_id in self.images_collected:
                product_item['image_url'] = self.images_collected[main_id]
            yield product_item
        self.finished = True

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//ul[@class="primary-nav"]//div[@class="sub-cats"]//li/a/@href').extract()

        for url in categories:
            url += 'view_size/all/'

            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_urls = hxs.select('//div[contains(@class, "list-product")]/a[contains(@class, "link")]/@href').extract()
        self.images_collected.update(
            dict(zip(hxs.select('//*/@data-secondid').re(r'\d+'),
                     hxs.select('//span[@class="product-image-wrap"]/img[contains(@class, "product-image")]/@src').extract())))
        for url in product_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        product_titles = hxs.select('//div[@class="product-header"]/h2/text()').extract()
        product_urls = hxs.select('//div[@data-product-id]/@class').re(r'js-product-([\w-]+)')

        products = []

        for l in response.body.split('\n'):
            if 'Harveys.DATA.CDP.Products' in l:
                products.append(l.strip())

        for i, product in enumerate(products):
            data = json.loads(product.split(' = ')[1][:-1])
            product_id = data['product_id']
            product_url = response.url
            for value in data['variants'].values():
                product_name = product_titles[i] + ' - ' + ' - '.join(value['attributes'].values())
                product_price = value['prices']['price']['value']
                variant_id = value[u'variant_id']

                product_identifier = '%s:%s' % (product_id, variant_id)
                product_url = urljoin_rfc(product_url, '#/%s' % product_urls[i])

                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('url', product_url)
                loader.add_value('name', product_name)
                loader.add_value('identifier', product_identifier)
                loader.add_value('price', product_price)
                loader.add_value('shipping_cost', '59')

                if product_url in self.old_data:
                    loader.add_value('category', self.old_data[product_url]['category'])
                    loader.add_value('brand', self.old_data[product_url]['brand'])
                    loader.add_value('sku', self.old_data[product_url]['sku'])

                category_found = bool(loader.get_output_value('category'))
                if not category_found:
                    for category, urls in self.category_products.items():
                        if product_url in urls or product_url + '/' in urls:
                            loader.add_value('category', category.split(','))
                            category_found = True
                            break

                if not category_found:
                    if 'lily-loveseat' in product_url:
                        loader.add_value('category', ['Sofa', 'Fabric', 'armchair'])
                    elif 'lean-to-shelf' in product_url:
                        loader.add_value('category', ['Cabinets', 'Bookcases'])
                    elif 'bench' in product_url:
                        loader.add_value('category', ['Dining', 'Dining Tables'])
                    elif 'console-table' in product_url:
                        loader.add_value('category', ['Cabinets', 'Console Tables'])
                    elif 'coffee-table' in product_url:
                        loader.add_value('category', ['Living', 'Coffee Tables'])
                    elif 'nest-of-table' in product_url:
                        loader.add_value('category', ['Living', 'Nest of Tables'])
                    elif '-sofa' in product_url or 'sofa' in product_name.lower():
                        if 'leather' in product_url or 'leather' in product_name.lower():
                            category = ['Sofa', 'Leather']
                        else:
                            category = ['Sofa', 'Fabric']

                        if '2-seater' in product_url:
                            category.append('2 seater')
                        elif '2.5 seater' in product_name.lower():
                            category.append('2.5 seater')
                        elif '3-seater' in product_url:
                            category.append('3 seater')
                        elif '4-seater' in product_url:
                            category.append('4 seater')
                        elif 'corner' in product_url:
                            category.append('Corner sofas')
                        elif 'recliner' in product_url:
                            category.append('Recliner sofas')

                        if len(category) == 3:
                            loader.add_value('category', category)
                    elif '-corner' in product_url:
                        if 'leather' in product_url or 'leather' in product_name.lower():
                            category = ['Sofa', 'Leather', 'Corner sofas']
                        else:
                            category = ['Sofa', 'Fabric', 'Corner sofas']
                        loader.add_value('category', category)
                    elif '-recliner-chair' in product_url or (('chair' in product_name.lower() or 'seat' in product_name.lower()) and ('recliner' in product_name.lower() or ' no recline' in product_name.lower())) or 'relaxer-chair' in product_url or 'hand-facing' in product_url:
                        if 'leather' in product_url or 'leather' in product_name.lower() or 'reid-hedgemoor' in product_url:
                            category = ['Sofa', 'Leather', 'armchair']
                        else:
                            category = ['Sofa', 'Fabric', 'armchair']
                        loader.add_value('category', category)
                    elif '-footstool' in product_url and not ('chair' in product_url):
                        if 'millan-' in product_url or 'leather' in product_url or 'leather' in product_name.lower():
                            loader.add_value('category', ['Sofa', 'Leather', 'Footstools'])
                        else:
                            loader.add_value('category', ['Sofa', 'Fabric', 'Footstools'])
                    elif '-table' in product_url and '-chairs' in product_url:
                        loader.add_value('category', ['Dining', 'Dining Sets'])
                    elif '-dining-table' in product_url:
                        loader.add_value('category', ['Dining', 'Dining Tables'])
                    elif '-bookcase' in product_url:
                        loader.add_value('category', ['Cabinets', 'Bookcases'])
                    elif '-lamp-table' in product_url:
                        loader.add_value('category', ['Living', 'Lamp Tables'])
                    elif '-sideboard' in product_url:
                        loader.add_value('category', ['Cabinets', 'Sideboards'])
                    elif '-display-unit' in product_url:
                        loader.add_value('category', ['Cabinets', 'Display Units'])
                    elif 'tv unit' in product_name.lower():
                        loader.add_value('category', ['Cabinets', 'Entertainment units'])
                    elif '-shelving-unit' in product_url:
                        loader.add_value('category', ['Cabinets', 'Display Units'])
                    elif '-wine-storage' in product_url:
                        loader.add_value('category', ['Cabinets', 'Display Units'])

                self.products_collected.append(set_product_type(loader.load_item()))

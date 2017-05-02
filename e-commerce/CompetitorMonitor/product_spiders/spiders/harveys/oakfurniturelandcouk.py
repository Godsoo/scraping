from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import Compose
from urlparse import urljoin
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)

from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

import re

from product_spiders.base_spiders.primary_spider import PrimarySpider


class OakfurniturelandcoSpider(PrimarySpider):
    name = u'oakfurnitureland.co.uk'
    allowed_domains = ['www.oakfurnitureland.co.uk']
    start_urls = [
        u'http://www.oakfurnitureland.co.uk/page/sitemap-product-page-1.html',
    ]
    errors = []

    csv_file = 'oakfurnitureland.co.uk_products.csv'

    def __init__(self, *args, **kwargs):
        super(OakfurniturelandcoSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

        self.parse_all = True

    def spider_idle(self):
        if self.parse_all:
            self.parse_all = False
            request = Request(self.start_urls[0], dont_filter=True, callback=self.parse)
            self._crawler.engine.crawl(request, self)

    def start_requests(self):
        categories = [
            ('leather', 'http://www.oakfurnitureland.co.uk/category/real-leather-sofas/', ''),
            ('fabric', 'http://www.oakfurnitureland.co.uk/category/fabric-sofas/', ''),
            ('corner', 'http://www.oakfurnitureland.co.uk/category/corner-sofas/', ''),
            ('dining_chairs', 'http://www.oakfurnitureland.co.uk/category/chairs/', 'Dining,Dining Chairs'),
            ('dining_sets', 'http://www.oakfurnitureland.co.uk/category/dining-sets/', 'Dining,Dining Sets'),
            ('dining_tables', 'http://www.oakfurnitureland.co.uk/category/dining-tables/', 'Dining,Dining Tables'),
            ('cabinets_bookcases', 'http://www.oakfurnitureland.co.uk/category/bookcases/', 'Cabinets,Bookcases'),
            ('cabinets_display', 'http://www.oakfurnitureland.co.uk/category/display-cabinets/', 'Cabinets,Display Units'),
            ('cabinets_entertainment', 'http://www.oakfurnitureland.co.uk/category/tv-cabinets/', 'Cabinets,Entertainment Units'),
            ('cabinets_console', 'http://www.oakfurnitureland.co.uk/category/hall-tables/', 'Cabinets,Console Tables'),
            ('cabinets_sideboards', 'http://www.oakfurnitureland.co.uk/category/sideboards/', 'Cabinets,Sideboards'),
            ('living_coffee', 'http://www.oakfurnitureland.co.uk/category/coffee-tables/', 'Living,Coffee Tables'),
            ('living_lamp', 'http://www.oakfurnitureland.co.uk/category/lamp-tables/', 'Living,Lamp Tables'),
            ('living_lamp', 'http://www.oakfurnitureland.co.uk/category/side-tables/', 'Living,Lamp Tables'),
            ('living_nest', 'http://www.oakfurnitureland.co.uk/category/nest-of-tables/', 'Living,Nest of Tables'),
            ('accessories_mirrors', 'http://www.oakfurnitureland.co.uk/category/mirrors/', 'Accessories,Mirrors'),
        ]

        for cat_id, url, names in categories:
            yield Request(url, meta={'catid': cat_id, 'catnames': names}, callback=self.parse_category)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        pages = hxs.select('//div[@id="skin_content"]//a[contains(@href, "/page/sitemap-product-page")]/@href').extract()
        for url in pages:
            yield Request(urljoin(base_url, url))

        products = hxs.select('//div[@id="skin_content"]//a[not (contains(@href, "/page/sitemap"))]/@href').extract()
        for url in products:
            yield Request(urljoin(base_url, url), callback=self.parse_product)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        items = hxs.select('//table[@class="khxc_cptbl_prod"]/tr/td/div/h2/a/@href').extract()
        for url in items:
            yield Request(urljoin(base_url, url), callback=self.parse_product, meta=response.meta)

        if not items:
            categories = hxs.select('//table[contains(@class, "khxc_cptbl_cat")]/tr/td/div/h2/a/@href').extract()
            for url in categories:
                yield Request(urljoin(base_url, url), callback=self.parse_category, meta=response.meta)

    def parse_price(self, price):
        try:
            price, count = re.subn(r'[^0-9]*([0-9 .,]+).*', r'\1', price.strip())
        except TypeError:
            return False
        if count:
            price = price.replace(",", "").replace(" ", "")
            try:
                price = float(price)
            except ValueError:
                return False
            else:
                return price
        elif price.isdigit():
            return float(price)
        return False

    def parse_product(self, response):

        if response.url == 'http://www.oakfurnitureland.co.uk/page/404.html':
            return

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = "".join(hxs.select('//h1[@id="ProductNameDisplay"]/text()').extract()).strip()
        if not name:
            name = hxs.select('//h1/text()').extract()

        try:
            pid = hxs.select('//input[@name="id"]/@value').pop().extract()
        except:
            try:
                pid = hxs.select('//input[@name="ecom_return_ref"]/@value').extract()[0]
            except:
                try:
                    pid = re.search(r'/(\d+).html', response.url).group(1)
                except:
                    return

        sku = hxs.select('//span[@class="prod-code"]/text()').extract()
        if not sku:
            try:
                sku = hxs.select('//div[@class="leftcol-inner"]/p[@class="lead-time"]/following-sibling::text()').extract()[0].strip()
            except:
                sku = ''

        price = hxs.select('//script[@type="application/ld+json"]/text()').re('"price":.*"(.+)",')
        if not price:
            price = hxs.select('//p[@class="khxc_inline_red_big"]/text()').extract()
        if not price:
            price = hxs.select('//*[@id="product-price"]//p[contains(@class, "khxc_inline_red_big")]/text()').extract()

        price = self.parse_price(price[0])

        if not price or not name:
            return
        else:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('url', urljoin(base_url, response.url))
            loader.add_value('name', name)

            category = self.get_category(hxs.select('//div[@class="newbreadcrumb"]/div/a/span/text()').extract())

            cat_id = response.meta.get('catid')
            cat_names = response.meta.get('catnames')

            material = ''.join(hxs.select('//div[@class="leftcol"]//td[@class="strong" and contains(text(), '
                                          '"Material")]/following-sibling::td[2]/text()').extract())

            categories = self.get_category_from_cat_id(cat_id, cat_names, loader.get_output_value('name'), material, category)
            for category in categories:
                loader.add_value('category', category)

            try:
                loader.add_xpath('image_url', '//script[@type="application/ld+json"]/text()', re='"image":.*"(.+)",')
            except:
                self.errors.append("No image set for url: '%s'" % urljoin(base_url, response.url))
            loader.add_value('price', price)
            loader.add_value('identifier', pid.upper())
            if sku:
                loader.add_value('sku', sku)

            yield loader.load_item()

    def get_category(self, categories):
        categories = map(lambda c: c.split('(')[0].strip(), categories)
        if categories:
            return categories.pop().strip()
        else:
            return ''

    def get_category_from_cat_id(self, cat_id, cat_names, product_name, material, page_category):
        name_splitted = map(unicode.strip, product_name.lower().split())

        if 'large sofa' in product_name.lower() and material:
            material = 'Fabric' if 'fabric' in material.lower() else 'Leather'
            if 'recliner' in product_name.lower():
                return ['Sofa', material, '3 seater recliner']
            else:
                return ['Sofa', material, '3 seater']
        elif 'small sofa' in product_name.lower() and material:
            material = 'Fabric' if 'fabric' in material.lower() else 'Leather'
            if 'recliner' in product_name.lower():
                return ['Sofa', material, '2 seater recliner']
            else:
                return ['Sofa', material, '2 seater']
        elif 'armchair' in product_name.lower().split() and material:
            material = 'Fabric' if 'fabric' in material.lower() else 'Leather'
            if 'recliner' in product_name.lower():
                return ['Sofa', material, 'Recliner armchairs']
            else:
                return ['Sofa', material, 'armchair seater']

        if cat_id == 'corner' or 'corner' in product_name.lower().split():
            material = 'Fabric' if 'fabric' in material.lower() else 'Leather'
            return ['Sofa', material, 'corner']
        elif cat_id in ('fabric', 'leather'):
            material = 'Fabric' if cat_id == 'fabric' else 'Leather'
            if 'large' in name_splitted and 'sofa' in name_splitted:
                return ['Sofa', material, '3 Seater']
            elif 'small' in name_splitted and 'sofa' in name_splitted:
                return ['Sofa', material, '2 Seater']
            elif 'armchair' in name_splitted:
                return ['Sofa', material, 'armchair']
            elif 'footstool' in name_splitted or 'footstools' in name_splitted:
                return ['Sofa', material, 'footstool']
            elif 'chair' in name_splitted:
                return ['Sofa', material, 'armchair']

        page_category_splitted = map(unicode.strip, page_category.lower().split())
        if 'dining' in page_category_splitted and 'sets' in page_category_splitted:
            return ['Dining', 'Dining Sets']
        elif 'dining' in page_category_splitted and 'chairs' in page_category_splitted:
            return ['Dining', 'Dining Chairs']
        elif 'dining' in page_category_splitted and 'tables' in page_category_splitted:
            return ['Dining', 'Dining Tables']
        elif 'display' in page_category_splitted and 'cabinets' in page_category_splitted:
            return ['Cabinets', 'Display Units']
        elif 'coffee' in page_category_splitted and 'tables' in page_category_splitted:
            return ['Living', 'Coffee Tables']

        # Check if is "Sofas, Armchairs and Footstools" category
        if page_category.strip() == 'Sofas, Armchairs and Footstools' and material:
            material = 'Fabric' if 'fabric' in material.lower() else 'Leather'
            if 'large' in name_splitted and 'sofa' in name_splitted:
                return ['Sofa', material, '3 Seater']
            elif 'small' in name_splitted and 'sofa' in name_splitted:
                return ['Sofa', material, '2 Seater']
            elif 'armchair' in name_splitted:
                return ['Sofa', material, 'armchair']
            elif 'footstool' in name_splitted or 'footstools' in name_splitted:
                return ['Sofa', material, 'footstool']
            elif 'chair' in name_splitted:
                return ['Sofa', material, 'armchair']

        # Check if is "Storage Cabinets" category
        if page_category.strip() == 'Storage Cabinets':
            if 'display' in name_splitted:
                return ['Cabinets', 'Display Units']
            elif 'media' in name_splitted:
                return ['Cabinets', 'Entertainment Units']

        return cat_names.split(',') if cat_names else [page_category]

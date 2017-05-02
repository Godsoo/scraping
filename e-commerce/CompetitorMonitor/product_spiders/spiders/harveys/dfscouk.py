import re
import json
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import url_query_parameter
from scrapy.contrib.loader.processor import Compose
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader

from product_spiders.base_spiders.primary_spider import PrimarySpider


from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from harveysmeta import set_product_type


class DfscoSpider(PrimarySpider):
    name = u'dfs.co.uk'
    allowed_domains = ['www.dfs.co.uk']
    start_urls = [
        u'http://www.dfs.co.uk/',
    ]
    errors = []

    csv_file = 'dfs.co.uk_products.csv'
    use_data_dir = True

    subcategories = []

    identifiers = []

    categorie_priorities = [
        ('Sofa,Fabric,2 Seater', 'http://www.dfs.co.uk/fabric-sofas/all-fabric-sofas/results-filter?2Seater=Y', ['2-seater'], []),
        ('Sofa,Fabric,2 Seater', 'http://www.dfs.co.uk/fabric-sofas/fabric-recliner-sofas/results-filter?2Seater=Y', ['2-seater'], []),
        ('Sofa,Fabric,3 Seater', 'http://www.dfs.co.uk/fabric-sofas/all-fabric-sofas/results-filter?3Seater=Y', ['3-seater'], []),
        ('Sofa,Fabric,3 Seater', 'http://www.dfs.co.uk/fabric-sofas/fabric-recliner-sofas/results-filter?3Seater=Y', ['3-seater'], []),
        ('Sofa,Fabric,4 Seater', 'http://www.dfs.co.uk/fabric-sofas/all-fabric-sofas/results-filter?4PlusSeater=Y', ['4-seater'], []),
        ('Sofa,Fabric,4 Seater', 'http://www.dfs.co.uk/fabric-sofas/fabric-recliner-sofas/results-filter?4Seater=Y', ['4-seater'], []),
        ('Sofa,Fabric,Corner sofas', 'http://www.dfs.co.uk/fabric-sofas/corner-fabric-sofas/results', ['corner'], []),
        ('Sofa,Leather,2 Seater', 'http://www.dfs.co.uk/leather-sofas/all-leather-sofas/results-filter?2Seater=Y', ['2-seater'], []),
        ('Sofa,Leather,2 Seater', 'http://www.dfs.co.uk/leather-sofas/leather-recliner-sofas/results-filter?2Seater=Y', ['2-seater'], []),
        ('Sofa,Leather,3 Seater', 'http://www.dfs.co.uk/leather-sofas/all-leather-sofas/results-filter?3Seater=Y', ['3-seater'], []),
        ('Sofa,Leather,3 Seater', 'http://www.dfs.co.uk/leather-sofas/leather-recliner-sofas/results-filter?3Seater=Y', ['3-seater'], []),
        ('Sofa,Leather,4 Seater', 'http://www.dfs.co.uk/leather-sofas/all-leather-sofas/results-filter?4PlusSeater=Y', ['4-seater'], []),
        ('Sofa,Leather,4 Seater', 'http://www.dfs.co.uk/leather-sofas/leather-recliner-sofas/results-filter?4Seater=Y', ['4-seater'], []),
        ('Sofa,Leather,Corner sofas', 'http://www.dfs.co.uk/leather-sofas/corner-leather-sofas/results', ['corner'], []),
        ('Sofa,Fabric,Sofa Beds', 'http://www.dfs.co.uk/sofa-beds/fabric-sofa-beds/results', ['sofa-bed'], []),
        ('Sofa,Leather,Sofa Beds', 'http://www.dfs.co.uk/sofa-beds/leather-sofa-beds/results', ['sofa-bed'], []),
        ('Dining,Dining Sets', 'http://www.dfs.co.uk/dining/tables-and-chairs/results', ['table', 'chairs'], []),
        ('Dining,Dining Chairs', 'http://www.dfs.co.uk/dining/dining-chairs/results', ['dining-chair'], []),
        ('Dining,Dining Tables', 'http://www.dfs.co.uk/dining/dining-tables/results', ['-table-'], ['chairs', 'lamp-table', 'coffee-table', 'console-table']),
        ('Cabinets,Bookcases', 'http://www.dfs.co.uk/dining/sideboards-and-cabinets/results-filter?bookcase=Y', ['bookcase'], []),
        ('Cabinets,Sideboards', 'http://www.dfs.co.uk/dining/sideboards-and-cabinets/results-filter?sideBoard=Y', ['sideboard'], []),
        ('Cabinets,Display Units', 'http://www.dfs.co.uk/dining/sideboards-and-cabinets/results-filter?cabinet=Y', ['cabinet,display-unit'], []),
        ('Cabinets,Console Tables', 'http://www.dfs.co.uk/dining/coffee-and-occasional-tables/results-filter?consoleTable=Y', ['console-table'], []),
        ('Cabinets,Entertainment Units', 'http://www.dfs.co.uk/dining/sideboards-and-cabinets/results-filter?tvUnit=Y', ['tv-unit'], []),
        ('Cabinets,Entertainment Units', 'http://www.dfs.co.uk/dining/tv-stands/results', ['tv-unit,tv-sideboard,tv-base'], []),
        ('Living,Coffee Table', 'http://www.dfs.co.uk/dining/coffee-and-occasional-tables/results-filter?coffeeTable=Y', ['coffee-table'], []),
        ('Living,Lamp Tables', 'http://www.dfs.co.uk/dining/coffee-and-occasional-tables/results-filter?lampTable=Y', ['lamp-table'], []),
        ('Living,Nest of Tables', 'http://www.dfs.co.uk/dining/coffee-and-occasional-tables/results-filter?nestOfTables=Y', ['nest-of-tables'], []),
        ('Accessories,Mirrors', 'http://www.dfs.co.uk/home-accessories/mirrors/results', ['mirror-'], []),
        ('Accessories,Rugs', 'http://www.dfs.co.uk/home-accessories/rugs/results', ['rug-'], []),
    ]

    parse_all = True

    def __init__(self, *args, **kwargs):
        super(DfscoSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def spider_idle(self):
        if self.categorie_priorities:
            category_name, url, include_vals, exclude_vals = self.categorie_priorities.pop()
            request = Request(url, dont_filter=True, callback=self.parse_category,
                meta={'category': category_name, 'include': include_vals, 'exclude': exclude_vals})
            self._crawler.engine.crawl(request, self)
        elif self.parse_all:
            self.parse_all = False
            for url in self.start_urls:
                request = Request(url, dont_filter=True, callback=self.parse, meta={'full_crawl': True})
                self._crawler.engine.crawl(request, self)

    def start_requests(self):
        category_name, url, include_vals, exclude_vals = self.categorie_priorities.pop()
        yield Request(url, meta={'category': category_name, 'include': include_vals, 'exclude': exclude_vals}, callback=self.parse_category)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        cats = hxs.select('//ul[@class="navigation mainNav  clearfix"]/li[@class=""]/a/@href').extract()
        for url in cats:
            yield Request(urljoin(base_url, url), callback=self.parse_subcategory, meta=response.meta)

    def parse_subcategory(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        items = hxs.select('//ul[contains(@class, "categories")]/li/a/@href').extract()
        for url in items:
            if url not in self.subcategories:
                self.subcategories.append(url)
                yield Request(urljoin(base_url, url),
                              callback=self.parse_category,
                              meta=response.meta)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        category = response.meta.get('category')
        if not category:
            category = hxs.select('//section[@id="coreListerImage"]/img/@title').extract()
            if category:
                category = [category[0]]
        else:
            category = category.split(',')

        items = hxs.select('//ul[@class="productRange"]/li/a/img/../@href').extract()
        next_page = hxs.select('//li[@class="nextPage"]/a/@href').extract()
        for url in items:
            meta = response.meta.copy()
            meta['category'] = category
            yield Request(urljoin(base_url, url), callback=self.parse_product, meta=meta, dont_filter=True)
        if items and next_page:
            yield Request(urljoin(base_url, next_page.pop()), callback=self.parse_category,
                          meta=response.meta)

    def parse_price(self, price):
        try:
            price, count = re.subn(
                r'[^0-9 .,]*([0-9 .,]+).*', r'\1', price.strip())
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
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        if not response.meta.get('subopt'):
            options = hxs.select('//ul[@class="swatchTabs"]/li[@class=""]/a/@href').extract()
            for url in options:
                response.meta['subopt'] = 1
                yield Request(urljoin(base_url, url), callback=self.parse_product, meta=response.meta)


        brand = hxs.select('//span[@itemprop="name"]/h3/strong/text()').extract()
        if brand:
            brand = brand.pop().strip()

        name = hxs.select('//span[@itemprop="name"]/h3/text()').pop().extract().strip()
        if name.startswith(':'):
            name = name[1:].strip()

        option = hxs.select('//ul[@class="swatchTabs"]/li[@class="selected"]/a/text()').extract()
        if option:
            option_value = option.pop()
            if not brand or (brand and brand.strip() != option_value.strip()):
                name = "%s - %s" % (name, option_value)

        if brand:
            name = brand + ' - ' + name

        category = list(response.meta.get('category', []))
        material = hxs.select('//ul[contains(@class, "coverType_Fabric_Large")]').re(r'(leather)')
        if not material:
            material = hxs.select('//div[@id="productInfo"]').re(r'(leather|fabric)')
            if material and material[0] == 'leather':
                if hxs.select('//div[@id="productInfo"]').re(r'(faux leather)'):
                    material = []
        if material and material[0] == 'leather':
            material = 'Leather'
        else:
            material = 'Fabric'

        from_more_items = response.meta.get('from_more_items', False)

        try:
            pid = response.xpath('//input[@name="productId"]/@value').pop().extract()
        except:
            try:
                pid = url_query_parameter(response.xpath('//a[@class="addToFavourites"]/@href').extract()[0], 'productId')
            except:
                data_json = response.xpath('//*[contains(@class, "addToShortlist")]/@data-listurl').extract()[0]
                pid = json.loads(data_json)['id'] or json.loads(data_json)['productId']

        if pid not in self.identifiers:
            self.identifiers.append(pid)

            price = self.parse_price(hxs.select('//div[@class="lowPrice"]/span/text()').pop().extract())

            if price:
                loader = ProductLoader(response=response, item=Product())
                loader.add_value('url', urljoin(base_url, response.url))
                loader.add_value('name', name)
                try:
                    loader.add_xpath('image_url', '//div[@class="colWithImg"]/img/@src', Compose(lambda v: urljoin(base_url, v[0])))
                except IndexError:
                    self.log("No image set for url: '%s'" % urljoin(base_url, response.url))
                loader.add_value('price', price)

                if 'footstool' in name.lower():
                    category = ['Sofa', material, 'footstools']
                elif 'lamp-table' in response.url:
                    category = ['Living', 'Lamp Tables']
                elif 'coffee-table' in response.url:
                    category = ['Living', 'Coffee Table']
                elif 'console-table' in response.url:
                    category = ['Living', 'Console Tables']
                elif 'nest-of-tables' in response.url:
                    category = ['Living', 'Nest of Tables']
                elif 'sofa-bed' in response.url:
                    if category and category[0] == 'Sofa' and not from_more_items:
                        category[-1] = 'Sofa Beds'
                    else:
                        category = ['Sofa', material, 'Sofa Beds']
                elif 'corner-sofa' in response.url:
                    if category and category[0] == 'Sofa' and not from_more_items:
                        category[-1] = 'Corner sofas'
                    else:
                        category = ['Sofa', material, 'Corner sofas']
                elif '2-seater' in response.url:
                    if category and category[0] == 'Sofa' and not from_more_items:
                        category[-1] = '2 Seater'
                    else:
                        category = ['Sofa', material, '2 Seater']
                elif '3-seater' in response.url:
                    if category and category[0] == 'Sofa' and not from_more_items:
                        category[-1] = '3 Seater'
                    else:
                        category = ['Sofa', material, '3 Seater']
                elif '4-seater' in response.url:
                    if category and category[0] == 'Sofa' and not from_more_items:
                        category[-1] = '4 Seater'
                    else:
                        category = ['Sofa', material, '4 Seater']
                elif ('sofa' in ' '.join(category).lower() and 'chair' in name.lower()) or 'armchair' in name.lower():
                    category = ['Sofa', material, 'armchair']

                if category[-1] == 'armchair' and 'recliner' in name.lower():
                    ['Sofa', material, 'Recliner sofas']
                elif category[-1] in ('2 Seater', '3 Seater') and 'recliner' in name.lower():
                    category[-1] = category[-1] + ' recliner'

                # Fix material
                if len(category) == 3 and category[0] == 'Sofa' and category[1] == 'Fabric' and material == 'Leather':
                    category[1] = 'Leather'

                for cat in category:
                    loader.add_value('category', cat)
                loader.add_value('identifier', pid)
                if brand:
                    loader.add_value('brand', brand)
                yield set_product_type(loader.load_item())
            else:
                self.errors.append("No price set for url: '%s'" %
                                   urljoin(base_url, response.url))

        more_items = hxs.select('//table[@id="listViewDataTable"]//div[@class="rangeItem"]'
            '//a[not(contains(@data-dialog, "#quickView"))]/@href').extract()

        # this is to avoid include items into a wrong category
        include_values = response.meta.get('include', [])
        exclude_values = response.meta.get('exclude', [])
        more_items = self._filter_links(more_items, include_values, exclude_values)
        for url in more_items:
            meta = response.meta.copy()
            meta['from_more_items'] = True
            yield Request(urljoin(get_base_url(response), url),
                          meta=meta,
                          callback=self.parse_product)

    def _filter_links(self, links, include_values, exclude_values):
        filtered_links = []
        for link_url in links:
            valid = True
            # Check include values
            # Include all of them, a single value could include any of the comma separated values
            # For example: ['table,chair', 'dining'] should be contain ("table" or "chair") and "dining"
            for value in include_values:
                is_in = False
                for v in value.split(','):
                    if v in link_url:
                        is_in = True
                        break
                if not is_in:
                    valid = False
                    break
            # If still valid then check exclude values
            if valid:
                # Exclude if any of them is contained in the url
                for value in exclude_values:
                    if value in link_url:
                        valid = False
                        break
            # If still valid then link is valid
            if valid:
                filtered_links.append(link_url)

        return filtered_links

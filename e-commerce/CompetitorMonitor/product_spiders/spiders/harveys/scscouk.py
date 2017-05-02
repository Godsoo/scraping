import re
import json
from scrapy import Request
from scrapy.utils.url import add_or_replace_parameter
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from harveysmeta import set_product_type, TWO_SEATER, THREE_SEATER
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.base_spiders.primary_spider import PrimarySpider


class Scsco(PrimarySpider):
    name = u'scs.co.uk'
    allowed_domains = ['www.scs.co.uk']
    start_urls = [
        u'http://www.scs.co.uk/our-sofas/recliner/',
        u'http://www.scs.co.uk/famous-sofa-brands/',
        u'http://www.scs.co.uk/carpets-and-flooring/',
        u'http://www.scs.co.uk/dining-and-occasional/',
    ]

    csv_file = 'scs.co.uk_products.csv'

    category_priorities = [
        ('leather', 'http://www.scs.co.uk/our-sofas/leather-sofas/', ''),
        ('leather', 'http://www.scs.co.uk/exclusive-brands/?prefn1=fabrics&prefv1=Leather', ''),
        ('leather', 'http://www.scs.co.uk/our-sofas/?prefn1=fabrics&prefv1=Leather', ''),
        ('leather_chair', 'http://www.scs.co.uk/our-sofas/chair/?prefn1=fabrics&prefv1=Leather', 'Sofa,Leather,Armchair'),
        ('leather_footstools', 'http://www.scs.co.uk/our-sofas/footstools/?prefn1=fabrics&prefv1=Leather', 'Sofa,Leather,Footstools'),
        ('leather_sofabeds', 'http://www.scs.co.uk/our-sofas/sofa-bed/?prefn1=fabrics&prefv1=Leather', 'Sofa,Leather,Sofa Beds'),
        ('corner_fabric', 'http://www.scs.co.uk/our-sofas/corner-sofa/?prefn1=fabrics&prefv1=Fabric', 'Sofa,Fabric,Corner'),
        ('corner_leather', 'http://www.scs.co.uk/our-sofas/corner-sofa/?prefn1=fabrics&prefv1=Leather', 'Sofa,Leather,Corner'),
        ('fabric', 'http://www.scs.co.uk/our-sofas/fabric-sofas/', ''),
        ('fabric', 'http://www.scs.co.uk/exclusive-brands/?prefn1=fabrics&prefv1=Fabric', ''),
        ('fabric', 'http://www.scs.co.uk/our-sofas/?prefn1=fabrics&prefv1=Fabric', ''),
        ('fabric_chair', 'http://www.scs.co.uk/our-sofas/chair/?prefn1=fabrics&prefv1=Fabric', 'Sofa,Fabric,Armchair'),
        ('fabric_footstools', 'http://www.scs.co.uk/our-sofas/footstools/?prefn1=fabrics&prefv1=Fabric', 'Sofa,Fabric,Footstools'),
        ('fabric_sofabeds', 'http://www.scs.co.uk/our-sofas/sofa-bed/?prefn1=fabrics&prefv1=Fabric', 'Sofa,Fabric,Sofa Beds'),
        ('dining', 'http://www.scs.co.uk/dining-and-occasional/', ''),
        ('dining_chairs', 'http://www.scs.co.uk/dining-and-occasional/dining-chairs/', 'Dining,Dining Chairs'),
        ('dining_tables', 'http://www.scs.co.uk/dining-and-occasional/dining-tables/', 'Dining,Dining Tables'),
        ('cabinets', 'http://www.scs.co.uk/dining-and-occasional/storage-and-media-units/', ''),
        ('console_tables', 'http://www.scs.co.uk/dining-and-occasional/console-tables/', 'Cabinets,Console Tables'),
        ('coffee_tables', 'http://www.scs.co.uk/dining-and-occasional/coffee-tables/', 'Living,Coffee Table'),
        ('lamp_tables', 'http://www.scs.co.uk/dining-and-occasional/lamp-tables/', 'Living,Lamp Tables'),
        ('nest_tables', 'http://www.scs.co.uk/dining-and-occasional/nest-of-tables/', 'Living,Nest Tables'),
        ('mirrors', 'http://www.scs.co.uk/dining-and-occasional/mirrors/', 'Accessories,Mirrors'),
    ]

    parse_all = True

    ADDITIONAL_TERMS = {TWO_SEATER: [], THREE_SEATER: ['large']}

    def __init__(self, *args, **kwargs):
        super(Scsco, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def spider_idle(self):
        if self.category_priorities:
            cat_id, url, cat_name = self.category_priorities.pop()
            request = Request(url,
                              meta={'cat_id': cat_id,
                                    'cat_name': cat_name},
                              callback=self.parse_category,
                              dont_filter=True)
            self._crawler.engine.crawl(request, self)
        elif self.parse_all:
            self.parse_all = False
            for url in self.start_urls:
                request = Request(url, dont_filter=True, callback=self.parse)
                self._crawler.engine.crawl(request, self)

    def start_requests(self):
        cat_id, url, cat_name = self.category_priorities.pop()
        yield Request(url,
                      meta={'cat_id': cat_id,
                            'cat_name': cat_name},
                      callback=self.parse_category,
                      dont_filter=True)

    def parse(self, response):

        " Firstly open all links from Shop by Product, then from oflSofas"

        for item in self.parse_category(response):
            yield item

        categories = response.xpath('//a[@class="shop-flooring__item"]/@href').extract()
        categories.extend(response.xpath('//a[@class="inspiration__item"]/@href').extract())
        categories.extend(response.xpath('//a[@class="filter-nav-list__link"]/@href').extract())

        for url in categories:
            yield Request(response.urljoin(url), callback=self.parse_category)

    def parse_category(self, response):
        try:
            category = response.xpath('//span[@class="breadcrumb__title breadcrumb-last"]/text()').extract()[0]
        except:
            return

        brands = response.xpath('//*[contains(text(), "Brands")]/following-sibling::ul/li/a[@class="filter-list__link"]/text()').extract()
        if not response.meta.get('filter_active', False):
            meta = response.meta.copy()
            meta['filter_active'] = True
            unit_filters = response.xpath('//*[contains(text(), "Type of sofa")]/following-sibling::ul/li/a[@class="filter-list__link"]/@href').extract()
            for filter_url in unit_filters:
                yield Request(response.urljoin(filter_url),
                              callback=self.parse_category,
                              meta=meta)

        next_page = response.xpath('//a[@class="btn lazy-load-placeholder--btn"]/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]),
                          callback=self.parse_category,
                          meta=response.meta.copy())

        meta = response.meta.copy()
        meta['brands'] = brands
        if 'cat_id' not in meta:
            meta['cat_id'] = ''
            meta['cat_name'] = category
        items = response.xpath('//a[@itemtype="http://schema.org/Product" and contains(@class, "product-trigger")]/@href').extract()
        for url in items:
            yield Request(
                response.urljoin(url),
                callback=self.parse_product,
                meta=meta,
            )

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
        name = response.xpath('//div[@id="buy-now"]//*[@itemprop="name"]/text()').extract()

        if not name:
            return

        name = name[0].strip()

        cat_id = response.meta.get('cat_id')
        cat_name = response.meta.get('cat_name')

        pid = response.xpath('//input[@id="pid"]/@value').extract()

        price = response.xpath('//div[@id="buy-now"]').css('em.product__price-now--amount ::text').extract_first()
        was_price = response.xpath('//s[@class="product__price-was--amount"]/text()')
        if was_price:
            was_price = was_price.extract()[0]
            was_price = self.parse_price(was_price)
            if was_price:
                self.log('Was price is {} {}'.format(was_price, response.url))

        brand = ''
        brands = response.meta.get('brands', [])
        for opt_brand in brands:
            if opt_brand.lower() in name.lower():
                brand = opt_brand
                break

        if price:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('url', response.urljoin(response.url))
            if brand:
                loader.add_value('brand', brand)
                loader.add_value('name', brand + ' - ' + name)
            else:
                loader.add_value('name', name)
            loader.add_xpath('image_url', '//div[@class="product-trigger__media"]/img/@src')
            loader.add_value('price', price)
            for cat in self.get_category(cat_id, name, cat_name):
                loader.add_value('category', cat)
            loader.add_value('identifier', pid)

            item = set_product_type(loader.load_item(), additional_terms=self.ADDITIONAL_TERMS, was_price=was_price)

            options = response.xpath('//div[@id="swatches"]//a[contains(@class,"product-swatches")]')

            if options:
                ajax_url = 'https://www.scs.co.uk/on/demandware.store/Sites-SCS-Site/default/Product-GetVariationPricesAsJson'
                for option in options:
                    try:
                        option_pid = option.xpath('@data-pid').extract()[0]
                        option_name = option.xpath('@data-name').extract()[0]
                    except:
                        continue

                    if len(options) == 1:
                        item['identifier'] = option_pid
                        item['name'] += ' - ' + option_name
                        yield set_product_type(self._fix_category(item), additional_terms=self.ADDITIONAL_TERMS)

                    else:
                        url = add_or_replace_parameter(ajax_url, 'pid', option_pid)
                        yield Request(url, callback=self.parse_option_price,
                                      meta={'product': item,
                                            'pid': option_pid,
                                            'name': option_name})
            else:
                yield item

    def parse_option_price(self, response):
        data = json.loads(response.body)

        product = Product(response.meta['product'])
        product['price'] = data['current']['value']
        was_price = data['high']['value']
        if str(was_price) != '0' and data['high']['pricelabel'].lower() == 'was':
            was_price = str(was_price)
            self.log('Was price in option is {} {}'.format(was_price, response.url))
        else:
            was_price = None

        product['identifier'] = response.meta['pid']
        product['name'] += ' - ' + response.meta['name']

        yield set_product_type(self._fix_category(product), additional_terms=self.ADDITIONAL_TERMS, was_price=was_price)

    def get_category(self, cat_id, product_name, cat_name):
        name_splitted = map(unicode.strip, product_name.lower().split())
        if cat_id in ('leather', 'fabric'):
            material = 'Fabric' if cat_id == 'fabric' else 'Leather'
            if '4 seater' in product_name.lower():
                return ['Sofa', material, '4 seater']
            elif '3.5 seater' in product_name.lower():
                return ['Sofa', material, '3.5 seater']
            elif '3 seater' in product_name.lower():
                if 'recliner' in product_name.lower():
                    return ['Sofa', material, '3 seater recliner']
                else:
                    return ['Sofa', material, '3 seater']
            elif '2.5 seater' in product_name.lower():
                return ['Sofa', material, '2.5 seater']
            elif '2 seater' in product_name.lower():
                if 'recliner' in product_name.lower():
                    return ['Sofa', material, '2 seater recliner']
                else:
                    return ['Sofa', material, '2 seater']
            elif 'corner' in name_splitted:
                return ['Sofa', material, 'Corner']
        elif cat_id in ('leather_chair', 'fabric_chair'):
            if 'recliner' in product_name.lower():
                category = cat_name.split(',')
                category[-1] = 'Recliner armchairs'
                return category
        elif cat_id == 'dining':
            if 'table' in name_splitted and 'chairs' in name_splitted:
                return ['Dining', 'Dining Sets']
        elif cat_id == 'cabinets':
            if 'sideboard' in name_splitted:
                return ['Cabinets', 'Sideboards']
            elif 'tv' in name_splitted or 'media' in name_splitted:
                return ['Cabinets', 'Entertainment Units']
            else:
                return ['Cabinets', 'Display Units']

        return cat_name.split(',')

    def _fix_category(self, product):
        if ('Leather' in product['category']) and \
            ('fabric' in [s.lower() for s in product['name'].split()]):
                product['category'] = product['category'].replace('Leather', 'Fabric')
        elif ('Fabric' in product['category']) and \
            ('leather' in [s.lower() for s in product['name'].split()]):
                product['category'] = product['category'].replace('Fabric', 'Leather')

        return product

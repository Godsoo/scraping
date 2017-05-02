from scrapy import Spider, Request
from scrapy.utils.url import (
    url_query_parameter,
    add_or_replace_parameter,
)
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from product_spiders.items import Product, ProductLoader
from product_spiders.lib.schema import SpiderSchema


class Furniturevillageco(Spider):
    name = u'furniturevillage.co.uk'
    allowed_domains = ['www.furniturevillage.co.uk']
    start_urls = ['http://www.furniturevillage.co.uk/']

    csv_file = 'furniturevillage_crawl.csv'
    errors = []
    clearance = dict()
    items = []
    parse_all = True

    category_priorities = [
        ('Sofa,Leather,footstools', 'http://www.furniturevillage.co.uk/sofas-and-armchairs/footstools/leather/'),
        ('Sofa,Fabric,footstools', 'http://www.furniturevillage.co.uk/sofas-and-armchairs/footstools/fabric-1/'),
        ('Sofa,Fabric,Sofa Beds', 'http://www.furniturevillage.co.uk/sofas-and-armchairs/sofas/sofa-beds/fabric-1/'),
        ('Sofa,Leather,Sofa Beds', 'http://www.furniturevillage.co.uk/sofas-and-armchairs/sofas/sofa-beds/leather/'),
        ('Sofa,Leather,2 Seater', 'http://www.furniturevillage.co.uk/sofas-and-armchairs/sofas/leather/?prefn1=itemType&prefv1=2%20Seater%20Sofa'),
        ('Sofa,Leather,2.5 Seater', 'http://www.furniturevillage.co.uk/sofas-and-armchairs/sofas/leather/?prefn1=itemType&prefv1=2.5%20Seater%20Sofa'),
        ('Sofa,Leather,3 Seater', 'http://www.furniturevillage.co.uk/sofas-and-armchairs/sofas/leather/?prefn1=itemType&prefv1=3%20Seater%20Sofa'),
        ('Sofa,Leather,3.5 Seater', 'http://www.furniturevillage.co.uk/sofas-and-armchairs/sofas/leather/?prefn1=itemType&prefv1=3.5%20Seater%20Sofa'),
        ('Sofa,Leather,4 Seater', 'http://www.furniturevillage.co.uk/sofas-and-armchairs/sofas/leather/?prefn1=itemType&prefv1=4%20Seater%20Sofa'),
        ('Sofa,Leather,Medium', 'http://www.furniturevillage.co.uk/sofas-and-armchairs/sofas/leather/?prefn1=itemType&prefv1=Medium%20Sofa'),
        ('Sofa,Leather,armchair', 'http://www.furniturevillage.co.uk/sofas-and-armchairs/armchairs/leather/'),
        ('Sofa,Fabric,2 Seater', 'http://www.furniturevillage.co.uk/sofas-and-armchairs/sofas/fabric-1/?prefn1=itemType&prefv1=2%20Seater%20Sofa'),
        ('Sofa,Fabric,2.5 Seater', 'http://www.furniturevillage.co.uk/sofas-and-armchairs/sofas/fabric-1/?prefn1=itemType&prefv1=2.5%20Seater%20Sofa'),
        ('Sofa,Fabric,3 Seater', 'http://www.furniturevillage.co.uk/sofas-and-armchairs/sofas/fabric-1/?prefn1=itemType&prefv1=3%20Seater%20Sofa'),
        ('Sofa,Fabric,3.5 Seater', 'http://www.furniturevillage.co.uk/sofas-and-armchairs/sofas/fabric-1/?prefn1=itemType&prefv1=3.5%20Seater%20Sofa'),
        ('Sofa,Fabric,4 Seater', 'http://www.furniturevillage.co.uk/sofas-and-armchairs/sofas/fabric-1/?prefn1=itemType&prefv1=4%20Seater%20Sofa'),
        ('Sofa,Fabric,Medium', 'http://www.furniturevillage.co.uk/sofas-and-armchairs/sofas/fabric-1/?prefn1=itemType&prefv1=Medium%20Sofa'),
        ('Sofa,Fabric,armchair', 'http://www.furniturevillage.co.uk/sofas-and-armchairs/armchairs/fabric-1/'),
        ('Sofa,Fabric,Corner sofas', 'http://www.furniturevillage.co.uk/sofas-and-armchairs/sofas/corner-sofas/fabric-1/'),
        ('Sofa,Leather,Corner sofas', 'http://www.furniturevillage.co.uk/sofas-and-armchairs/sofas/corner-sofas/leather/'),
        ('Dining,Dining Chairs', 'http://www.furniturevillage.co.uk/dining-room/dining-chairs/'),
        ('Dining,Dining Sets', 'http://www.furniturevillage.co.uk/dining-room/dining-table-and-chairs/'),
        ('Dining,Dining tables', 'http://www.furniturevillage.co.uk/dining-room/dining-tables/'),
        ('Cabinets,Bookcases', 'http://www.furniturevillage.co.uk/living-room/storage/bookcases/'),
        ('Cabinets,Display Unit', 'http://www.furniturevillage.co.uk/living-room/storage/display-cabinets/'),
        ('Cabinets,Display Unit', 'http://www.furniturevillage.co.uk/living-room/storage/shelves/'),
        ('Cabinets,Entertainment Units', 'http://www.furniturevillage.co.uk/living-room/storage/tv-stands/'),
        ('Cabinets,Sideboards', 'http://www.furniturevillage.co.uk/living-room/storage/sideboards/'),
        ('Cabinets,Console Tables', 'http://www.furniturevillage.co.uk/living-room/tables/console-tables/'),
        ('Living,Coffee Tables', 'http://www.furniturevillage.co.uk/living-room/tables/coffee-tables/'),
        ('Living,Lamp Tables', 'http://www.furniturevillage.co.uk/living-room/tables/side-tables/'),
        ('Living,Nest of Tables', 'http://www.furniturevillage.co.uk/living-room/tables/nest-of-tables/'),
        ('Accessories,Mirrors', 'http://www.furniturevillage.co.uk/accessories/accessories/mirrors/'),
        ('Accessories,Rugs', 'http://www.furniturevillage.co.uk/accessories/accessories/rugs/'),
    ]

    def __init__(self, *args, **kwargs):
        super(Furniturevillageco, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def start_requests(self):
        category_name, url = self.category_priorities.pop()
        yield Request(url, meta={'category': category_name}, callback=self.parse_category)

    def spider_idle(self):
        if self.category_priorities:
            category_name, url = self.category_priorities.pop()
            request = Request(url, meta={'category': category_name}, callback=self.parse_category)
            self._crawler.engine.crawl(request, self)

    def parse(self, response):
        categories = {}
        for c in response.xpath('//*[@id="mainMenu"]//div[contains(@class, "level-3")]//a'):
            url = c.xpath('@href').extract()[0]
            text = c.xpath('text()').extract()[0].strip()
            if ('/brands/' not in url) and (text not in categories):
                categories[text] = url

        for c_desc, c_url in categories.items():
            yield Request(
                response.urljoin(c_url),
                callback=self.parse_category,
                meta={'category': c_desc}
            )

    def parse_category(self, response):
        items = set(response.xpath('//li[@data-productid]//a[contains(@class, "name-link")]/@href').extract())
        for url in items:
            yield Request(
                response.urljoin(url),
                callback=self.parse_product,
                meta={'category': response.meta['category']}
            )

        if items and len(items) >= 12:
            # Try next page
            start_index = int(url_query_parameter(response.url, 'start', '0')) + 12
            url = add_or_replace_parameter(response.url, 'sz', '12')
            url = add_or_replace_parameter(url, 'start', str(start_index))
            yield Request(
                url,
                callback=self.parse_category,
                meta={'category': response.meta['category']}
            )

    def parse_product(self, response):
        # Normal options
        options = response.xpath('//select[@class="variation-select"]/option[not(@selected)]')
        options = zip(map(unicode.strip, options.xpath('text()').extract()), options.xpath('@value').extract())
        for desc, url in options:
            yield Request(url,
                          meta={'category': response.meta.get('category'),
                                'option': desc},
                          callback=self.parse_product)

        # Variations popup
        variations_url = response.xpath('//div[@class="variations"]//a/@data-href').extract()
        if variations_url:
            url = response.urljoin(variations_url[0])
            yield Request(url, callback=self.parse_variations, meta=response.meta)

        schema = SpiderSchema(response)
        product = schema.get_product()

        name = product['name']

        # Normal option selected
        current_option = map(
            unicode.strip,
            response.xpath('//select[@class="variation-select"]/option[@selected]/text()')
            .extract())
        if current_option:
            name += ' - ' + current_option[0]

        # Variation selected
        currently_selected = response.xpath('//div[@class="variations"]'
            '//div[contains(@class, "variation-attribute-selected-value")]/text()')\
            .extract()
        if currently_selected:
            current_option = currently_selected[-1].strip()
            name += ' - ' + current_option[0]

        identifier = product['productID']
        price = product['offers']['properties']['price']
        image_url = product['image']
        category = response.meta.get('category')

        if not category:
            category = [c['properties']['name'] \
                for c in schema.data['items'][0]['properties']\
                        ['breadcrumb']['properties']['itemListElement'][1:-1]]
        else:
            category = category.split(',')
            if '2 seater' in name.lower():
                category[-1] = '2 Seater'
            elif '2.5 seater' in name.lower():
                category[-1] = '2.5 Seater'
            elif '3 seater' in name.lower():
                category[-1] = '3 Seater'
            elif '3.5 seater' in name.lower():
                category[-1] = '3.5 Seater'
            elif '4 seater' in name.lower():
                category[-1] = '4 Seater'
            if 'recliner' in name.lower():
                if '2 Seater' in category:
                    category[-1] = '2 seater recliner'
                elif '3 Seater' in category:
                    category[-1] = '3 seater recliner'
                elif 'armchair' in category:
                    category[-1] = 'Recliner armchairs'

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_value('image_url', image_url)
        loader.add_value('price', price)
        for cat in category:
            loader.add_value('category', cat)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)

        if not identifier in self.items:
            self.items.append(identifier)
            yield loader.load_item()

    def parse_variations(self, response):
        variants_urls = response.xpath('//div[contains(@class, '
            '"product-popup-variations")]//input[not(@checked)]/@value')\
            .extract()
        for url in variants_urls:
            yield Request(response.urljoin(url),
                          callback=self.parse_product,
                          meta=response.meta)

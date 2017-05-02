import re
import json
from datetime import datetime
from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.url import urljoin_rfc, parse_url, add_or_replace_parameter
from scrapy.utils.response import get_base_url
from scrapy.exceptions import CloseSpider

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

class PixmaniaBaseSpider(BaseSpider):

    available_locations = (
        ('be_fr', 'http://www.pixmania.be/fr/index.html'),
        ('be_nl', 'http://www.pixmania.be/nl/index.html'),
        ('cz', 'http://www.pixmania.cz/off/index.html'),
        ('cy', 'http://www.pixmania.com.cy/off/index.html'),
        ('dk', 'http://www.pixmania.dk/index.html'),
        ('de', 'http://www.pixmania.de/index.html'),
        ('gr', 'http://www.pixmania.gr/off/index.html'),
        ('ee', 'http://www.pixmania.ee/et/off/index.html'),
        ('es', 'http://www.pixmania.es/index.html'),
        ('fr', 'http://www.pixmania.fr/index.html'),
        ('ie', 'http://www.pixmania.ie/index.html'),
        ('it', 'http://www.pixmania.it/index.html'),
        ('lv', 'http://www.pixmania.lv/off/index.html'),
        ('lt', 'http://www.pixmania.lt/off/index.html'),
        ('lu_fr', 'http://www.pixmania.lu/fr/off/index.html'),
        ('lu_de', 'http://www.pixmania.lu/de/off/index.html'),
        ('hu', 'http://www.pixmania.hu/off/index.html'),
        ('nl', 'http://www.pixmania.nl/index.html'),
        ('no', 'http://www.pixmania.no/index.html'),
        ('at', 'http://www.pixmania.at/off/index.html'),
        ('pl', 'http://www.pixmania.pl/index.html'),
        ('pt', 'http://www.pixmania.pt/index.html'),
        ('ch_de', 'http://www.pixmania.ch/de/off/index.html'),
        ('ch_fr', 'http://www.pixmania.ch/fr/off/index.html'),
        ('ch_it', 'http://www.pixmania.ch/it/off/index.html'),
        ('sk', 'http://www.pixmania.sk/off/index.html'),
        ('si', 'http://www.pixmania.si/off/index.html'),
        ('fi', 'http://www.pixmania.fi/index.html'),
        ('se', 'http://www.pixmania.se/index.html'),
        ('uk', 'http://www.pixmania.co.uk/index.html'),
    )

    location = 'uk'
    only_buybox = False
    pixmania_direct = False
    collect_reviews = False
    append_brand_to_name = True
    filters_enabled = False  # Try website filters
    use_main_id_as_sku = False
    full_category_path = False

    reviews_url = 'http://api.bazaarvoice.com/data/batch.json?passkey=id8675mbdlc80xrwg1vxdde0t&apiversion=5.5&displaycode=13997-fr_fr&resource.q0=reviews&filter.q0=isratingsonly%3Aeq%3Afalse&filter.q0=productid%3Aeq%3A09698791&filter.q0=contentlocale%3Aeq%3Afr_FR&sort.q0=relevancy%3Aa1&stats.q0=reviews&filteredstats.q0=reviews&include.q0=authors%2Cproducts%2Ccomments&filter_reviews.q0=contentlocale%3Aeq%3Afr_FR&filter_reviewcomments.q0=contentlocale%3Aeq%3Afr_FR&filter_comments.q0=contentlocale%3Aeq%3Afr_FR&limit.q0=30&offset.q0=8&limit_comments.q0=3&callback=bv_1111_40649'

    def __init__(self, *args, **kwargs):

        super(PixmaniaBaseSpider, self).__init__(*args, **kwargs)

        self.init_start_urls()
        self.init_allowed_domains()

    def init_start_urls(self):
        if (not hasattr(self, 'start_urls')) or (hasattr(self, 'start_urls') and (not self.start_urls)):
            dict_locations = dict(self.available_locations)
            self.start_urls = []
            try:
                self.start_urls.append(dict_locations[self.location])
            except KeyError:
                self.log('Not valid location: %s' % self.location, level=self.log.CRITICAL)
                raise CloseSpider


    def init_allowed_domains(self):
        if (not hasattr(self, 'allowed_domains')) or (hasattr(self, 'allowed_domains') and (not self.allowed_domains)):
            self.allowed_domains = []
            dict_locations = dict(self.available_locations)
            for url in self.start_urls:
                domain = parse_url(dict_locations[self.location]).netloc.replace('www.', '')
                if domain not in self.allowed_domains:
                    self.allowed_domains.append(domain)
        elif hasattr(self, 'allowed_domains') and not isinstance(self.allowed_domains, list):
            self.allowed_domains = list(self.allowed_domains)

        if 'bazaarvoice.com' not in self.allowed_domains:
            self.allowed_domains.append('bazaarvoice.com')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        if self.filters_enabled:
            filters = hxs.select('//aside[@id="filters"]//li/a/@href').extract()
            for url in filters:
                yield Request(urljoin_rfc(base_url, url))

        products = hxs.select('//form//div[contains(@class, "resultList")]/article'
                              '//*[contains(@class, "productTitle")]/a/@href').extract()

        for url in products:
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product)

        pages = hxs.select('//ul[@class="pagination"]//a/@href').extract()

        for url in pages:
            yield Request(urljoin_rfc(base_url, url))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        product_name = hxs.select('//span[@itemprop="name"]/text()').extract()[0].strip()
        try:
            product_brand = hxs.select('//span[@itemprop="brand"]/text()').extract()[0].strip()
        except:
            product_brand = ''
        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()[0]
        category = hxs.select('//div[@class="breadcrumb"]//a/span[@itemprop="title"]/text()').extract()[-1]
        categories = hxs.select('//ul[@class="simple"]/li/a/span[@itemprop="title"]/text()').extract()
        categories = categories[1:] if categories else []
        identifier = response.url.split('/')[-1].split('-')[0]
        price = hxs.select('//div[@itemprop="offers"]//ins[@itemprop="price"]/text()').extract()[0]
        product_url = response.url
        stock = hxs.select('//div[contains(@class, "productDetail")]//div[contains(@class, "availability")]//strong[contains(@class, "available")]/i[@class="icon-ok"]').extract()
        sellers_url = hxs.select('//a[contains(@href, "all_seller")]/@href').extract()

        dealer = hxs.select('//p[contains(@class, "sellby")]/a/strong/text()').extract()
        if not dealer:
            dealer = hxs.select('//p[contains(@class, "sellby")]/strong/text()').extract()
        if not dealer:
            dealer = hxs.select('//section[@class="col3"]//p/strong/text()').extract()

        dealer = dealer[0].strip() if dealer else 'Pixmania.com'

        if self.pixmania_direct and dealer != 'Pixmania.com':
            return

        l = ProductLoader(item=Product(), response=response)
        l.add_value('identifier', identifier)
        if self.use_main_id_as_sku:
            l.add_value('sku', identifier)
        if self.append_brand_to_name:
            l.add_value('name', product_brand + ' ' + product_name)
        else:
            l.add_value('name', product_name)
        if not self.full_category_path:
            l.add_value('category', category)
        else:
            l.add_value('category', categories)
        l.add_value('brand', product_brand)
        l.add_value('url', product_url)
        l.add_value('image_url', image_url)

        if not stock:
            l.add_value('stock', 0)

        if not self.only_buybox and not self.pixmania_direct and sellers_url:
            item = l.load_item()
            yield Request(sellers_url[0].strip(), callback=self.parse_sellers, meta={'product': item})
        else:
            l.add_value('price', self._encode_price(price))
            l.add_value('dealer', 'Pix - ' + dealer)
            item = l.load_item()
            item['identifier'] += '-' + dealer
            if self.collect_reviews:
                reviews_url = add_or_replace_parameter(self.reviews_url, 'filter.q0', 'productid:eq:%s' % identifier)
                reviews_url = add_or_replace_parameter(reviews_url, 'offset.q0', '0')
                yield Request(reviews_url, meta={'products': [item]}, callback=self.parse_reviews)
            else:
                yield item

    def parse_sellers(self, response):
        hxs = HtmlXPathSelector(response)
        product = response.meta['product']
        products = []  # Only is reviews enabled
        sellers = hxs.select('//div[contains(@class, "merchant") and contains(@class, "product")]')
        for seller in sellers:
            price = seller.select('.//span[@class="currentPrice"]/ins/text()').extract()[0]
            seller_name = seller.select('.//p[@class="soldby"]/strong//text()').extract()
            try:
                shipping_cost = seller.select('.//div[@class="productPrices"]//span/text()').re(r'\+ ([\d,.]+)')[0]
            except:
                shipping_cost = '0,00'

            stock = seller.select('.//p[@class="availability"]/span[contains(@class, "available")]'
                                  '/i[@class="icon-ok"]').extract()

            l = ProductLoader(item=Product(), response=response)
            l.add_value('identifier', product['identifier'] + '-' + seller_name[0])
            if self.use_main_id_as_sku:
                l.add_value('sku', product['identifier'])
            l.add_value('name', product['brand'] + ' ' + product['name'])
            l.add_value('category', product['category'])
            l.add_value('brand', product['brand'])
            l.add_value('url', product['url'])
            l.add_value('shipping_cost', self._encode_price(shipping_cost))
            l.add_value('price', self._encode_price(price))
            l.add_value('image_url', product['image_url'])
            l.add_value('dealer', 'Pix - ' + seller_name[0] if seller_name else 'Pixmania.com')
            if not stock:
                l.add_value('stock', 0)

            new_item = l.load_item()

            if 'metadata' in product:
                new_item['metadata'] = product['metadata'].copy()

            products.append(new_item)

        if self.collect_reviews:
            reviews_url = add_or_replace_parameter(self.reviews_url, 'filter.q0', 'productid:eq:%s' % product['identifier'])
            reviews_url = add_or_replace_parameter(reviews_url, 'offset.q0', '0')
            yield Request(reviews_url, meta={'products': products}, callback=self.parse_reviews)
        else:
            for item in products:
                yield item

    def parse_reviews(self, response):
        try:
            data = json.loads(response.body.replace('bv_1111_40649(', '')[:-1])
        except ValueError:
            data = json.loads(re.findall('\((.*)\)', response.body)[0])

        products = response.meta['products']
        results = data['BatchedResults']['q0']['Results']

        for result in results:
            review = {}
            review['rating'] = result['Rating']
            review_date = datetime.strptime(result['SubmissionTime'].split('T')[0], '%Y-%m-%d')
            review['date'] = review_date.strftime('%d/%m/%Y')
            review['full_text'] = result['Title'] + ' ' + result['ReviewText']
            review['review_id'] = result['Id']
            for product in products:
                if 'metadata' not in product:
                    product['metadata'] = {'reviews': []}
                product_review = review.copy()
                product_review['url'] = product['url']
                product_review['sku'] = product.get('sku', '')
                product['metadata']['reviews'].append(product_review)

        limit = int(data['BatchedResults']['q0']['Limit'])
        offset = int(data['BatchedResults']['q0']['Offset'])
        total = int(data['BatchedResults']['q0']['TotalResults'])

        if (offset + limit) < total:
            reviews_url = response.url
            reviews_url = add_or_replace_parameter(reviews_url, 'offset.q0', str(offset + limit))
            yield Request(reviews_url, meta={'products': products}, callback=self.parse_reviews)
        else:
            for product in products:
                yield product

    def _encode_price(self, price):
        price = price.replace(',', '.').encode("ascii", "ignore")
        if len(re.findall(r'\.', price)) > 1:
            price = price.replace('.', '', 1)
        return price

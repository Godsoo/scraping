
# -*- coding: utf-8 -*-
import datetime
import urlparse
import re, os, csv
import json
import time

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.utils import extract_price_eu, extract_price
from product_spiders.items import Product, ProductLoaderWithNameStripEU as ProductLoader
from sonaeitems import SonaeMeta
from product_spiders.config import DATA_DIR
HERE = os.path.abspath(os.path.dirname(__file__))

class FnacSpider(BaseSpider):
    name = "sonae-fnac.pt-direct"
    allowed_domains = ["fnac.pt"]
    #start_urls = ["http://www.fnac.pt"]
    search_url = 'http://pesquisa.fnac.pt/SearchResult/ResultList.aspx?ItemPerPage=20&SDM=list&Search=%7C&SFilt=1!206&sft=1&sl=0.77000964&ssi=1&sso=1&PageIndex={page}'
    products = {}
    metadata_ = {}
    deduplicate_identifiers = True
    seen = set()

    def __init__(self, *args, **kwargs):
        super(FnacSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def spider_idle(self):
        self.log('Spider idle.')
        for identifier in self.products:
            if identifier in self.seen:
                continue
            url = self.products[identifier]['url']
            exclusive_online = self.metadata_.get(identifier, {}).get('exclusive_online', '')
            if exclusive_online.lower() == 'yes':
                exclusive_online = True
            request = Request(url, callback=self.parse_product, meta={'exclusive_online': exclusive_online})

            self._crawler.engine.crawl(request, self)

    def start_requests(self):
        if hasattr(self, 'prev_crawl_id'):
            filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
        else:
            filename = os.path.join(HERE, 'fnac_products.csv')


        with open(filename) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.products[row['identifier']] = {'brand':row['brand'],
                                                    'sku':row['sku'],
                                                    'url': row['url'],
                                                    'category': row['category'].decode('utf8'),
                                                    'image_url':row['image_url'],
                                                    'name': row['name'].decode('utf8')}

        if hasattr(self, 'prev_crawl_id'):
            meta_filename = os.path.join(DATA_DIR, 'meta/%s_meta.json-lines' % self.prev_crawl_id)
            if os.path.exists(meta_filename):
                with open(meta_filename) as f:
                    for line in f:
                        p = json.loads(line)
                        self.metadata_[p['identifier']] = {'promo_start': p['metadata'].get('promo_start'),
                                                           'promo_end': p['metadata'].get('promo_end')}

        yield Request(self.search_url.format(page=1), callback=self.parse_number_pages)

    def parse_number_pages(self, response):
        pages = response.xpath('//*[@class="sliderTotal"]/text()').extract()[0]
        pages = int(re.search('(\d+)', pages, re.MULTILINE).groups()[0])
        pages = (pages / 20) + 10
        self.log('{} pages found'.format(pages))

        for i in range(1, pages + 1):
            yield Request(self.search_url.format(page=i), callback=self.parse_search_results,
                          dont_filter=True)

    def extract_product_info(self, product):
        prod_url = product.xpath('.//a/@href').extract()[0]
        price_section = product.xpath('./../../following-sibling::div')
        marketplace = len(price_section.xpath('.//*[@class="seller"]')) > 0
        price = price_section.xpath('.//*[@class="floatl"]//*[@class="userPrice"]/text()').extract()
        if price:
            price = price[0].replace(u'\xa0', '')
            price = extract_price_eu(price)

        promotion_price = price_section.xpath('.//*[@class="floatl"]//*[@class="oldPrice"]/text()').extract()
        if promotion_price:
            promotion_price = promotion_price[0].replace(u'\xa0', '')
            promotion_price = extract_price_eu(promotion_price)

        out_stock = len(product.xpath('./..//*[@class="Nodispo"]').extract()) > 0
        dispo = product.xpath('./../..').css('.sellerInfos > li')
        if dispo:
            dispo = ' '.join(dispo.css('.Dispo-txt').xpath("text()").extract())
        else:
            dispo = ''

        exclusive_online = u'exclusivo internet' in dispo.lower()

        shipping = product.xpath('./..//*[@class="Delivery-price"]//text()')
        if shipping:
            shipping = ''.join(shipping.extract())
            shipping = extract_price(shipping)
        else:
            shipping = ''

        identifier =  re.search('/mp(\d+)/', prod_url)
        if not identifier:
            identifier = re.search('/a(\d+)$', prod_url)
        if identifier:
            identifier = 'fcom' + identifier.groups()[0]
        else:
            self.log('Identifier not found {}'.format(prod_url))

        result = {'url': prod_url, 'marketplace': marketplace, 'price': price,
                  'promotion_price': promotion_price, 'out_stock': out_stock,
                  'exclusive_online': exclusive_online, 'shipping': shipping,
                  'identifier': identifier}
        

        return result

    def get_product_from_cache(self, response, product_data):
        identifier = product_data['identifier']
        values = self.products[identifier]
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', identifier)
        loader.add_value('brand', values['brand'].decode('utf-8'))
        loader.add_value('sku', values['sku'].decode('utf-8'))
        loader.add_value('image_url', values['image_url'])
        loader.add_value('name', values['name'])
        category = self.products[identifier]['category'].split(' > ')

        loader.add_value('category', category)
        loader.add_value('dealer', 'Fnac')
        if product_data['shipping']:
            loader.add_value('shipping_cost', product_data['shipping'])

        loader.add_value('url', product_data['url'])
        loader.add_value('price', str(product_data['price']).replace('.', ','))

        product = Product(loader.load_item())

        product['metadata'] = SonaeMeta()
        product['metadata']['delivery_24_48'] = 'Yes'

        if product_data['exclusive_online']:
            product['metadata']['exclusive_online'] = 'Yes'

        promotion_price = product_data['promotion_price']
        if promotion_price:
            product['metadata']['promotion_price'] = str(promotion_price).replace(',', '.')

        if identifier in self.metadata_:
            prev_meta = self.metadata_[identifier]
        else:
            prev_meta = {}

        promo = promotion_price
        promo_start = prev_meta.get('promo_start')
        promo_end = prev_meta.get('promo_end')
        today = datetime.datetime.now().strftime('%Y-%m-%d')

        product['metadata']['extraction_timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        if promo:
            product['metadata']['promo_start'] = promo_start if promo_start and not promo_end else today
            product['metadata']['promo_end'] = ''
        else:
            if promo_start:
                product['metadata']['promo_start'] = promo_start
                product['metadata']['promo_end'] = today if not promo_end else promo_end

        return product

    def parse_search_results(self, response):
        products = response.xpath('//*[@class="Article-desc"]')
        products = [p for p in products if p.xpath('.//a')]
        self.log('products found {}'.format(len(products)))

        for prod in products:
            result = self.extract_product_info(prod)
            identifier = result['identifier']
            if identifier in self.products and not result['marketplace']:
                self.log('Loading product from cache')
                self.seen.add(identifier)
                yield self.get_product_from_cache(response, result)
                continue

            meta = response.meta.copy()
            if result['exclusive_online']:
                meta['exclusive_online'] = True

            yield Request(result['url'], meta=meta, callback=self.parse_product)

    def parse_product(self, response):
        self.log("[[TEST]] parse_product")
        description_field = response.xpath("//script[contains(text(), 'tc_vars')]/text()").extract_first()
        if not description_field:
            raise ValueError("Could not find description field: {}".format(response.url))

        m = re.findall(r'tc_vars\["product_id"\]\s*=\s*"([^"]*)"', description_field)
        identifier = m[0]
        if not identifier:
            raise ValueError("Identifier not found: {}".format(response.url))
        identifier = 'fcom' + identifier

        name = response.css('.ProductSummary-title').xpath("//*[@itemprop='name']/text()").extract_first().strip()
        if not name:
            raise ValueError("Name not found: {}".format(response.url))
        subname = response.css('.ProductSummary-subTitle').xpath("span[a]/preceding-sibling::span/text()").extract_first()
        if subname:
            name = ' '.join([name, subname])

        m = re.findall(r'tc_vars\["product_EAN"\]\s*=\s*"(\d*)"', description_field)
        sku = m[0] if m else ''

        price = response.xpath('//*[@class="ProductSellers-tabControlText" and contains(text(), "Fnac")]//text()')
        if price:
            price = ' '.join(price.extract()).replace(u'\xa0', '')
            price = re.search('([\d,]+)', price, re.MULTILINE|re.DOTALL)
            if price:
                price = price.groups()[0]
            self.log(price)

        if not price and not identifier in self.products:
            self.log('Price not found {}'.format(response.url))
            return

        stock = 1 if price else 0

        category_01 = response.css('.Breadcrumb-list').css('.Breadcrumb-item').css('[itemprop=title]')[1].xpath('text()').extract_first()
        try:
            category_02 = response.css('.Breadcrumb-list').css('.Breadcrumb-item').css('[itemprop=title]')[2].xpath('text()').extract_first()
        except IndexError:
            category_02 = ''

        m = re.findall(r'tc_vars\["product_trademark"\]\s*=\s*"([^"]*)"', description_field)
        brand = m[0] if m else ''

        shipping = response.css('.Delivery').xpath('.//text()').extract()
        if shipping:
            shipping = ''.join(shipping).strip()
            shipping = re.search('([\d,]+)', shipping)
            if shipping:
                shipping = shipping.groups()[0]
                shipping = extract_price_eu(shipping)
        else:
            shipping = ''

        m = re.findall(r'tc_vars\["product_picture_url"\]\s*=\s*"([^"]*)"', description_field)
        image_url = m[0]

        l = ProductLoader(item=Product(), response=response)
        self.seen.add(identifier)
        l.add_value('identifier', identifier)
        l.add_value('name', name)
        l.add_value('url', response.url)
        l.add_value('sku', sku)
        l.add_value('price', price)
        if not stock:
            l.add_value('stock', stock)
        l.add_value('category', category_01)
        l.add_value('category', category_02)
        l.add_value('brand', brand)
        l.add_value('shipping_cost', shipping)
        l.add_value('image_url', image_url)
        l.add_value('dealer', 'Fnac')

        product = l.load_item()

        product['metadata'] = SonaeMeta()
        product['metadata']['delivery_24_48'] = 'Yes'
        if response.meta.get('exclusive_online'):
            product['metadata']['exclusive_online'] = 'Yes'

        promotion_price = response.css('.ProductPriceBox').css('.oldPrice').xpath("text()").extract_first()
        if promotion_price:
            promotion_price = promotion_price.strip().replace(u'\xa0', '').replace(u'\u20ac', '').replace(' ', '')
            product['metadata']['promotion_price'] = str(extract_price_eu(promotion_price))

        if identifier in self.metadata_:
            prev_meta = self.metadata_[identifier]
        else:
            prev_meta = {}
        promo = promotion_price
        promo_start = prev_meta.get('promo_start')
        promo_end = prev_meta.get('promo_end')
        today = datetime.datetime.now().strftime('%Y-%m-%d')

        product['metadata']['extraction_timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        if promo:
            product['metadata']['promo_start'] = promo_start if promo_start and not promo_end else today
            product['metadata']['promo_end'] = ''
        else:
            if promo_start:
                product['metadata']['promo_start'] = promo_start
                product['metadata']['promo_end'] = today if not promo_end else promo_end

        yield product